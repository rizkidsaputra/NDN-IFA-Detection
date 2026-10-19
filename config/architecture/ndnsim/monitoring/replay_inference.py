import csv
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import torch

from graph_detector import GraphSAGEGRU, GraphDetector


HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
OUT = HERE / "outputs"

ROUTERS = [f"R{i}" for i in range(1, 11)]
FEATURE_COUNT = 11
WINDOW_SIZE = 5


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_artifacts():
    metadata = read_json(ART / "metadata.json")
    complete = read_json(ART / "COMPLETE.json")
    graph = read_json(ART / "graph.json")

    assert metadata["spec"] == {
        "kind": "graph",
        "variant": "Mask+Age",
        "seed": 11,
    }
    assert metadata["run_identity"] == complete["run_identity"]
    assert metadata["test_evaluated"] is False

    for filename in ("model.pt", "preprocessor.joblib", "metadata.json"):
        digest = hashlib.sha256(
            (ART / filename).read_bytes()
        ).hexdigest()

        expected = complete["sha256"][filename]
        if digest != expected:
            raise ValueError(f"SHA256 mismatch: {filename}")

    assert graph["router_order"] == ROUTERS
    return metadata, graph


def check_topology(run, graph):
    with (run / "links.csv").open(newline="") as f:
        links = list(csv.DictReader(f))

    actual = {
        frozenset((row["a"], row["b"]))
        for row in links
        if row["a"] in ROUTERS and row["b"] in ROUTERS
    }

    adjacency = np.asarray(graph["adjacency_binary"])
    expected = {
        frozenset((ROUTERS[i], ROUTERS[j]))
        for i in range(10)
        for j in range(i + 1, 10)
        if adjacency[i, j] != 0
    }

    if actual != expected:
        raise ValueError(
            f"Graph topology mismatch: "
            f"missing={expected - actual}, extra={actual - expected}"
        )


def load_windows(run):
    # Agent digunakan hanya sebagai sumber jadwal window,
    # bukan sumber measurement bagi ML.
    windows = {}

    with (run / "agent-R1.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            if row["event"] != "sample":
                continue

            fields = row["detail"].split(";")
            if len(fields) != 16:
                raise ValueError("Invalid agent sample payload")

            seq = int(fields[1])
            end = float(fields[3])

            if seq in windows:
                raise ValueError("Duplicate sampling window")
            windows[seq] = end

    ids = sorted(windows)
    if not ids or ids != list(range(1, len(ids) + 1)):
        raise ValueError("Sampling windows are not consecutive")

    return windows


def load_received(run, run_id):
    reports = {router: [] for router in ROUTERS}
    seen_names = set()

    with (run / "collector-received.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            parts = row["payload"].split(";")
            if len(parts) != 16:
                raise ValueError("Invalid Collector payload")

            router = parts[0]
            seq = int(parts[1])

            if router not in ROUTERS:
                raise ValueError(f"Unknown router: {router}")

            name = f"/report/{run_id}/{router}/{seq}"
            if row["name"] != name or name in seen_names:
                raise ValueError(f"Invalid/duplicate report: {name}")

            seen_names.add(name)

            values = np.asarray(
                [float(v) for v in parts[5:16]],
                dtype=np.float32,
            )
            if not np.isfinite(values).all():
                raise ValueError("Nonfinite telemetry")

            reports[router].append({
                "seq": seq,
                "end": float(parts[3]),
                "ready": float(parts[4]),
                "arrival": float(row["arrival"]),
                "values": values,
            })

    return reports


def build_frames(windows, reports, deadline_offset):
    frames = []

    for seq, end in sorted(windows.items()):
        cutoff = end + deadline_offset

        raw = np.zeros((10, FEATURE_COUNT), dtype=np.float32)
        mask = np.zeros((10, 1), dtype=np.float32)
        age = np.zeros((10, 1), dtype=np.float32)
        history = np.zeros((10, 1), dtype=np.float32)

        for i, router in enumerate(ROUTERS):
            eligible = [
                report
                for report in reports[router]
                if report["seq"] <= seq
                and report["ready"] <= cutoff + 1e-9
                and report["arrival"] <= cutoff + 1e-9
                and report["end"] <= cutoff + 1e-9
            ]

            if not eligible:
                continue

            # Gunakan sample terbaru yang sudah diterima.
            latest = max(
                eligible,
                key=lambda r: (r["seq"], r["arrival"]),
            )

            raw[i] = latest["values"]
            mask[i, 0] = float(latest["seq"] == seq)
            age[i, 0] = cutoff - latest["end"]
            history[i, 0] = 1.0

        frames.append({
            "window": seq,
            "decision_at_s": cutoff,
            "raw": raw,
            "mask": mask,
            "age": age,
            "history": history,
        })

    return frames


def build_batch(frames):
    groups = [
        frames[i:i + WINDOW_SIZE]
        for i in range(len(frames) - WINDOW_SIZE + 1)
    ]

    if not groups:
        raise ValueError("Fewer than five monitoring frames")

    return {
        key: np.asarray([
            [frame[key] for frame in group]
            for group in groups
        ], dtype=np.float32)
        for key in ("raw", "mask", "age", "history")
    }, groups


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python replay_inference.py runs/RUN_ID"
        )

    run = Path(sys.argv[1]).resolve()
    config = read_json(run / "config.json")

    metadata, graph = check_artifacts()
    check_topology(run, graph)

    if config["routers"] != ROUTERS:
        raise ValueError("Run router order mismatch")

    preprocessor = joblib.load(ART / "preprocessor.joblib")

    model = GraphSAGEGRU(channels=13)
    state = torch.load(
        ART / "model.pt",
        map_location="cpu",
        weights_only=True,
    )
    model.load_state_dict(state, strict=True)

    detector = GraphDetector(
        model=model,
        variant="Mask+Age",
        preprocessor=preprocessor,
        graph=graph,
        threshold=metadata["threshold"],
    )

    windows = load_windows(run)
    reports = load_received(run, config["runId"])

    frames = build_frames(
        windows,
        reports,
        float(config["report_deadline_s"]),
    )

    batch, groups = build_batch(frames)

    # Memakai checkpoint terlatih, tanpa fitting ulang.
    result = detector.predict(
        batch,
        router_order=graph["router_order"],
    )

    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / f"{config['runId']}-predictions.jsonl"

    with destination.open("w", encoding="utf-8") as f:
        for i, group in enumerate(groups):
            last = group[-1]
            row = {
                "run_id": config["runId"],
                "window": last["window"],
                "decision_at_s": last["decision_at_s"],
                "score": float(result["score"][i]),
                "prediction": int(result["pred"][i]),
                "threshold": float(result["threshold"]),
                "fresh_reports": int(last["mask"].sum()),
                "stale_reports": int(
                    ((last["history"] == 1) &
                     (last["mask"] == 0)).sum()
                ),
            }
            f.write(json.dumps(row) + "\n")

    print("Run:", config["runId"])
    print("Frames:", len(frames))
    print("Sequences:", len(groups))
    print("Output:", destination)
    print("Threshold:", metadata["threshold"])


if __name__ == "__main__":
    main()