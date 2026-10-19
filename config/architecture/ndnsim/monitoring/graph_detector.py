from collections.abc import Mapping

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


MEASUREMENTS = [
    "in_interests",
    "out_interests",
    "in_data",
    "out_data",
    "in_nacks",
    "out_nacks",
    "satisfied_pit_events",
    "unsatisfied_pit_events",
    "cs_hits",
    "cs_misses",
    "pit_entries",
]

VARIANT_CHANNELS = {
    "Mask": 12,
    "Mask+Age": 13,
}

DEFAULT_MODEL_CONFIG = {
    "graph_hidden": 32,
    "gru_hidden": 64,
    "dropout": 0.15,
}


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


class MeanSAGELayer(nn.Module):
    def __init__(self, input_channels, output_channels):
        super().__init__()

        self.self_linear = nn.Linear(
            input_channels, output_channels
        )

        self.neighbor_linear = nn.Linear(
            input_channels,
            output_channels,
            bias=False,
        )

    def forward(self, x, adjacency):
        neighbors = torch.einsum(
            "ij,btjf->btif",
            adjacency,
            x,
        )

        return (
            self.self_linear(x)
            + self.neighbor_linear(neighbors)
        )


class GraphSAGEGRU(nn.Module):
    def __init__(self, channels, config=None):
        super().__init__()

        require(
            channels in (12, 13),
            "Full-feature Mask=12, Mask+Age=13.",
        )

        config = (
            DEFAULT_MODEL_CONFIG
            if config is None
            else config
        )

        spatial = config["graph_hidden"]
        temporal = config["gru_hidden"]

        self.sage1 = MeanSAGELayer(
            channels, spatial
        )
        self.norm1 = nn.LayerNorm(spatial)

        self.sage2 = MeanSAGELayer(
            spatial, spatial
        )
        self.norm2 = nn.LayerNorm(spatial)

        self.dropout = nn.Dropout(
            config["dropout"]
        )

        self.gru = nn.GRU(
            spatial,
            temporal,
            batch_first=True,
        )

        self.classifier = nn.Sequential(
            nn.LayerNorm(temporal),
            nn.Linear(temporal, 32),
            nn.ReLU(),
            nn.Dropout(config["dropout"]),
            nn.Linear(32, 1),
        )

    def forward(self, x, adjacency):
        spatial = self.dropout(
            F.relu(
                self.norm1(
                    self.sage1(x, adjacency)
                )
            )
        )

        spatial = self.dropout(
            F.relu(
                self.norm2(
                    self.sage2(spatial, adjacency)
                )
            )
        )

        network_sequence = spatial.mean(dim=2)

        temporal, _ = self.gru(
            network_sequence
        )

        return self.classifier(
            temporal[:, -1]
        ).squeeze(-1)


def transform_inputs(
    preprocessor,
    variant,
    batch,
    *,
    router_order,
):
    require(
        variant in VARIANT_CHANNELS,
        "Pilih Mask atau Mask+Age.",
    )

    require(
        list(preprocessor["measurement_features"])
        == MEASUREMENTS,
        "Measurement order berbeda dari training.",
    )

    require(
        list(preprocessor["router_order"])
        == list(router_order),
        "Router order berbeda dari scaler training.",
    )

    require(
        len(router_order) > 0
        and len(set(router_order)) == len(router_order),
        "Router order kosong atau duplikat.",
    )

    raw_input = np.asarray(batch["raw"])
    mask = np.asarray(batch["mask"])
    age_input = np.asarray(batch["age"])
    history_input = np.asarray(batch["history"])

    require(
        raw_input.ndim == 4,
        "raw harus [B,5,N,11].",
    )

    expected = (
        raw_input.shape[0],
        5,
        len(router_order),
        11,
    )

    require(
        raw_input.shape == expected
        and expected[0] > 0,
        f"raw shape harus {expected}.",
    )

    slot_shape = expected[:-1] + (1,)

    require(
        all(
            value.shape == slot_shape
            for value in (
                mask,
                age_input,
                history_input,
            )
        ),
        "Shape Mask, Age, atau History tidak sesuai.",
    )

    require(
        np.isin(history_input, [0, 1]).all(),
        "History harus biner.",
    )

    require(
        np.isin(mask, [0, 1]).all(),
        "Mask harus biner.",
    )

    history = history_input.astype(bool)

    require(
        not ((mask == 1) & ~history).any(),
        "Report tersedia tetapi tidak punya history.",
    )

    mean = np.asarray(
        preprocessor["mean"]
    )
    std = np.asarray(
        preprocessor["std"]
    )

    require(
        mean.shape == std.shape == (11,),
        "Scaler harus memiliki 11 fitur.",
    )

    require(
        np.isfinite(mean).all()
        and np.isfinite(std).all()
        and (std > 0).all(),
        "Scaler measurement tidak valid.",
    )

    raw = np.where(
        history,
        raw_input,
        0.0,
    )

    require(
        np.isfinite(raw).all()
        and (raw >= 0).all(),
        "Measurement harus finite dan nonnegatif.",
    )

    values = (
        np.log1p(raw) - mean
    ) / std

    values = np.where(
        history,
        values,
        0.0,
    ).astype(np.float32)

    channels = [
        values,
        mask.astype(np.float32),
    ]

    if variant == "Mask+Age":
        age_mean = float(
            preprocessor["age_mean"]
        )
        age_std = float(
            preprocessor["age_std"]
        )

        require(
            np.isfinite(age_mean)
            and np.isfinite(age_std)
            and age_std > 0,
            "Scaler Age tidak valid.",
        )

        age = np.where(
            history,
            age_input,
            0.0,
        )

        require(
            np.isfinite(age).all()
            and (age >= 0).all(),
            "Age harus finite dan nonnegatif.",
        )

        age = (
            np.log1p(age) - age_mean
        ) / age_std

        channels.append(
            np.where(
                history,
                age,
                0.0,
            ).astype(np.float32)
        )

    result = np.concatenate(
        channels,
        axis=-1,
    ).astype(np.float32)

    require(
        result.shape[-1]
        == VARIANT_CHANNELS[variant],
        "Jumlah channel tidak sesuai.",
    )

    require(
        np.isfinite(result).all(),
        "Input transform mengandung nilai nonfinite.",
    )

    return result


class GraphDetector:
    def __init__(
        self,
        model,
        variant,
        preprocessor,
        graph,
        threshold,
        device="cpu",
        batch_size=128,
    ):
        require(
            variant in VARIANT_CHANNELS,
            "Pilih Mask atau Mask+Age.",
        )

        require(
            isinstance(preprocessor, Mapping),
            "Preprocessor harus dictionary.",
        )

        self.router_order = list(
            graph["router_order"]
        )

        require(
            self.router_order
            == list(preprocessor["router_order"]),
            "Router order graph dan scaler berbeda.",
        )

        adjacency = np.asarray(
            graph["adjacency_mean"],
            dtype=np.float32,
        )

        nodes = len(self.router_order)

        require(
            adjacency.shape == (nodes, nodes),
            "Ukuran adjacency berbeda.",
        )

        require(
            np.isfinite(adjacency).all()
            and (adjacency >= 0).all(),
            "Adjacency tidak valid.",
        )

        require(
            np.allclose(
                adjacency.sum(axis=1),
                1.0,
            ),
            "Gunakan adjacency MEAN training.",
        )

        require(
            np.allclose(
                np.diag(adjacency),
                0.0,
            ),
            "Graph tidak menggunakan self-loop.",
        )

        require(
            model.sage1.self_linear.in_features
            == VARIANT_CHANNELS[variant],
            "Channel checkpoint dan varian berbeda.",
        )

        require(
            np.isfinite(threshold),
            "Threshold tidak valid.",
        )

        require(
            isinstance(batch_size, int)
            and batch_size > 0,
            "Batch size harus positif.",
        )

        self.variant = variant
        self.preprocessor = preprocessor
        self.threshold = float(threshold)
        self.device = torch.device(device)
        self.batch_size = batch_size

        self.model = model.to(
            self.device
        ).eval()

        self.adjacency = torch.as_tensor(
            adjacency,
            device=self.device,
        )

    def predict(
        self,
        batch,
        *,
        router_order,
    ):
        require(
            list(router_order) == self.router_order,
            "Router order input berbeda dari training.",
        )

        x = transform_inputs(
            self.preprocessor,
            self.variant,
            batch,
            router_order=router_order,
        )

        parts = []
        self.model.eval()

        with torch.no_grad():
            for start in range(
                0,
                len(x),
                self.batch_size,
            ):
                xb = torch.from_numpy(
                    x[start:start + self.batch_size]
                ).to(self.device)

                score = torch.sigmoid(
                    self.model(
                        xb,
                        self.adjacency,
                    )
                )

                parts.append(
                    score.cpu().numpy()
                )

        scores = np.concatenate(
            parts
        ).astype(float)

        require(
            np.isfinite(scores).all(),
            "Skor ML tidak valid.",
        )

        return {
            "score": scores,
            "pred": (
                scores >= self.threshold
            ).astype(np.int64),
            "threshold": self.threshold,
            "variant": self.variant,
        }