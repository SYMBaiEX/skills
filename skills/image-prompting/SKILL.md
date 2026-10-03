---
name: image-prompting
description: Write and refine image-generation and image-editing prompts, with model-specific guidance for GPT Image 2.5. Use when a user wants a new image, a targeted edit, or a clear prompt they can paste into an image tool.
---

# Image prompting

Translate the user's idea into a prompt that describes the desired image and protects the details they care about. This is a prompt-writing skill for Codex, Claude Code, and other compatible agents. It does not assume a particular image-generation provider or start image generation by itself.

For GPT Image 2.5, read [references/gpt-image-2-5.md](references/gpt-image-2-5.md). For another specified image model, preserve the useful creative brief but adapt syntax and settings only to that model's documented controls.

## Draft with intent

Identify whether the user wants to create an image or edit one. For an edit, distinguish:

- What should change.
- What must stay the same, such as identity, product shape, layout, camera angle, or palette.
- Which reference image controls each attribute.

Capture the few decisions that materially affect the result: intended use, subject, composition, aspect ratio or crop, visual style, exact text, and any preservation constraints. Ask only for missing essentials. If the request is clear enough, state reasonable assumptions and draft.

Describe the image in priority order:

1. Main subject and intended use.
2. Composition, framing, viewpoint, placement, and negative space.
3. Important visible details, materials, expression, pose, and environment.
4. Lighting, color, medium, and finish.
5. Exact text, if required.
6. Constraints and exclusions that prevent likely mistakes.

Prefer specific visual outcomes to adjective piles. Say what should appear in the image rather than describing an abstract prompt recipe. For precise copy, quote the exact wording and explicitly exclude extra text. Recommend a separate editable text overlay when exact typography or small copy is critical.

For an edit, use a narrow instruction such as “Change only X; preserve Y.” Make a consequential edit one step at a time and inspect the result before continuing. For transparent cutouts, use an actual transparent-background control if the selected tool has one; a checkerboard drawn into an image is not transparency.

## Return the prompt

Provide one paste-ready prompt, plus a compact reference map or settings notes only when helpful. Keep model parameters separate from prompt prose. Do not invent negative-prompt syntax, aspect-ratio flags, or model settings. If the user requests generation and a suitable authorized tool is available, generate only within that request; otherwise provide the prompt for the user's chosen tool.
