# Alibaba Wan 3.0

Use this reference for Alibaba Cloud Model Studio's Wan 3.0 video-generation workflow. Product surfaces can expose different tasks, controls, and limits, so check the selected interface before recommending settings.

## Prompt shape

Alibaba's Wan 3.0 guide describes a full prompt as an overall description, reference citations, timed shots with subject/scene/motion/aesthetic direction, dialogue, sound effects or music, style/mood, and optional negative prompts. Use only the parts the brief needs. A one-sentence prompt is valid for a simple clip.

For several shots, use explicit time spans and direct each beat:

~~~text
Overall: A grounded, intimate scene in a quiet greenhouse.
References: Image 1 supplies the lead character's appearance. Video 1 supplies camera movement only.
Shot 1 [0–3 s]: The lead kneels beside a seedling; medium shot, camera slowly pushes in.
Shot 2 [3–7 s]: Close-up as the lead brushes soil from one leaf and smiles; hold on the final expression.
Dialogue: The lead says, "There you are."
Sound: Soft greenhouse ambience; no music.
Style: Natural morning light, muted green palette, realistic detail.
Avoid: Extra people, text, logos. [Use a separate negative-prompt field if the interface provides one.]
~~~

These are prompt sections, not required keywords or API syntax. Replace each reference label with the exact item and order shown by the interface.

## Choose the right mode

- Text-to-video: describe the subject, setting, action, and desired camera behavior.
- First-frame or first-and-last-frame image-to-video: treat those images as boundary frames; describe the motion that connects them and preserve the details the user wants held constant.
- Reference-to-video: distinguish inspiration references from strict start/end frames. Explicitly name each reference's role.
- Editing or extension: identify the source clip, the exact change or continuation, and what must remain unchanged.

Describe motion over time rather than restating every static detail already visible in a reference. For motion, make the sequence observable: starting state, main action, and ending state. Keep the number of actions and transitions appropriate to the requested clip length.

## Reference labels and current documentation

Model Studio's examples identify references in prompt text as “Image 1,” “Video 1,” and “Audio 1,” matching their order in the submitted media. Follow the actual interface's labels; do not assume a UI and an API enumerate media identically.

Research checkpoint: 2026-10-03. Recheck current task support, input limits, and prompt behavior before giving version-specific settings.

- [Wan 3.0 video generation prompt guide](https://help.aliyun.com/en/model-studio/wan3-video-generation-prompt-guide)
- [Wan video generation guide and task modes](https://help.aliyun.com/en/model-studio/wan3-video-generation-guide)
- [Alibaba Cloud video-generation prompt guide](https://www.alibabacloud.com/help/en/model-studio/text-to-video-prompt)
