# GPT-5.6 routing and old catalog recovery

Sol, Terra and Luna are current supported parents, alongside Astra. See
[model routing](model-routing.md); they are not restricted to an Astra-led economy fleet.

Use supported runtime selectors and the upstream catalog. The old unsupported Luna V1-to-V2 catalog
creation path has been removed. Never patch a catalog to make a model available or claim execution
from configuration alone.

`scripts/configure_luna_v2.py --check` diagnoses the known managed override.
With explicit setup/recovery authorization, `--disable` backs up configuration privately and removes
only that exact setting while preserving all other parsed values. It leaves any catalog file intact
because it may have been customized. Restart Codex after recovery. Custom overrides and symlinks
are preserved or rejected for review, never silently replaced. No apply/refresh/Fast enable path remains.
