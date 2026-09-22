# GPT-5.6 rollout compatibility

GPT-5.6 Sol, Terra, and Luna are retained here as historical and rollout-parent compatibility
references. If a user has already selected a GPT-5.6 parent, preserve it; this skill does not
switch the active chat model. GPT-5.6 is not a current GPT Engineer child route. Any delegation
from a GPT-5.6 parent must be an explicit mixed-model route to GPT-6 Sol or GPT-6 Luna. Astra
remains parent-only under every route.

Use only runtime-supported selectors and the upstream model catalog. The old unsupported Luna
V1-to-V2 catalog creation path has been removed. Never patch a catalog to make a model available or
claim execution from configuration alone. Existing old catalog state is outside this routing
policy; diagnose it with the existing read-only check and do not mutate it without a separate,
explicit recovery request.
