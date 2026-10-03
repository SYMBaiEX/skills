---
name: video-prompting
description: Draft, adapt, and troubleshoot paste-ready prompts for AI video generation. Use for Alibaba Wan 3.0 or ByteDance Seedance 2.0/2.5, routing through each model's own shot, reference, motion, and audio conventions. Return prompts; submit generations only when the user asks.
---

# Video prompting

Turn the user's idea into a clear, model-native video prompt. This skill is for prompt writing and prompt revision across Codex, Claude Code, and other compatible agents. It has no preferred generation platform and does not depend on Higgsfield.

## Route by model and task

Identify the exact model and task before drafting:

- For Wan 3.0, read [references/wan-3.md](references/wan-3.md).
- For Seedance 2.0, read [references/seedance-2.md](references/seedance-2.md).
- For Seedance 2.5, read [references/seedance-2-5.md](references/seedance-2-5.md).

Do not transfer reference tokens, shot formatting, parameter names, or assumed limits between these models. If the user says only “Wan” or “Seedance,” use the version they name or ask which one they have selected. If they do not know, state a reasonable version assumption and still give them a useful draft.

Determine only the choices that materially change the prompt: text-to-video, image-to-video, reference-to-video, editing, or extension; target duration and aspect ratio; the role of each supplied reference; action and camera movement; and whether dialogue, sound effects, or music are wanted. Ask about missing essentials briefly. Otherwise make minimal assumptions and label them.

## Write the prompt

1. Preserve the user's idea, cast, and visual intent. Clarify a vague idea into one visible action with a clear beginning, development, and end.
2. Map every supplied asset to its actual label in the target interface. State what each reference contributes, such as subject identity, composition, location, motion, sound, or style. Never invent a reference or token.
3. Direct the subject's movement and the camera separately. Make the action physically legible, and avoid contradictory instructions such as “one continuous take” alongside unmarked cuts.
4. For multiple shots, give each shot its own time range, subject action, framing or camera behavior, and transition where it matters. Keep the number of beats within the requested duration.
5. Put spoken words in quotation marks and identify the speaker. Describe desired ambience, sound effects, or music only when sound is in scope. Do not add dialogue, lyrics, or music the user did not ask for.
6. Separate prompt prose from UI/API controls such as duration, resolution, aspect ratio, generation mode, and negative-prompt fields. Mention a control only when the chosen interface supports it. Do not turn a negative list into prompt prose if the interface has a separate negative-prompt field.
7. Keep only details that help control the result. A concise prompt is fine for a simple shot; do not pad it with camera jargon or every category in a formula.

## Return a useful handoff

Give the user:

- A one-line interpretation of the scene and any consequential assumption.
- A reference map when assets were supplied.
- One paste-ready prompt in the target model's expected format.
- Optional settings notes kept separate from the prompt, and one focused alternative only when it resolves a real creative tradeoff.

When revising, preserve what the user approved and change the smallest part that addresses their feedback. Do not claim that a prompt is proven unless an output was actually generated and reviewed. Do not start a paid generation, upload assets, or submit a job unless the user explicitly asked for generation and the necessary tool is available.
