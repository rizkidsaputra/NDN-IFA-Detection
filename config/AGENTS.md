# Instruksi kolaborasi untuk AI

Read `PROJECT_CONTEXT.md` first, then `architecture/README.md`. These files are the portable source of project decisions and verified status. Instructions from the human user take precedence.

## Scope and evidence

- The public simulator package includes the benign pilot, router agents, pull collector, IFA mechanism and benign-burst controls. The pinned ndn-cxx adapter requires the single-wakeup scheduler patch. Offline ML evaluation has subsequently been performed in separate campaigns. The repository now includes an offline monitoring replay module and one GraphSAGE+GRU Mask+Age seed11 bundle, but not complete training data or the full FIFO-Priority stress campaign. Read PROJECT_CONTEXT.md for current evidence and distinguish it from the historical pilot.
- R1 through R10 are all forwarding routers. M/P/C1/C2/C3/A1/A2 are separate endpoint nodes. Do not add R5-R6 or substitute historical seven-router illustrations.
- Do not reuse old implementations or datasets as current results. This package does not require access to the author's workstation or archived project.
- Collector features must come only from report Data packets that have arrived. Direct NFD/trace access is for agents or independent audit, never a collector shortcut.
- Preserve report/sample/request/arrival timing. Missing observations do not remove physical routers. A timeout is not automatically congestion loss.
- Literature counts come from `architecture/literature/usage-ranking.json` and its evidence CSV. Recount with the supplied script. Topology is multilabel; architecture coding uses a different eligible denominator. Do not call this a systematic review or a count of identical layouts.
- Do not claim novelty or better model performance from a diagram, paper count, proposal, replay, or benign pilot.

## Implementation and verification

- Use the pinned commits, include-only compatibility patches and the explicit functional single-wakeup scheduler patch. Do not silently change simulator platform or claim the functional patch is include-only.
- Do not edit `architecture/evidence/reference-run/` to make checks pass. Validate a temporary copy or create a new run under the ignored runtime directory.
- Never overwrite a completed run. Mark interrupted runs and repeat with a new output label; resume is not implemented.
- Run `python architecture/scripts/verify_package.py` after changing the package. If intentionally changing source/docs, refresh `architecture/evidence/package-sha256.json` with `--write-manifest` and then verify again. A regenerated hash is not proof that altered simulator behavior was tested.
- Preserve local user changes. Keep credentials, private host addresses, home-directory paths, generated dependencies and large datasets out of commits.
- Update `PROJECT_CONTEXT.md` and the relevant method/results document after a decision or verified experiment. State the command, input/config hash, run ID and actual result. Do not advance planned work to verified status without evidence.

## Suggested first response after reading

Briefly state the current verified stage, the user's requested scope, and which concrete check will establish completion. Ask only for missing information that actually blocks the requested task.
