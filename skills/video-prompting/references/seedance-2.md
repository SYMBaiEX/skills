# ByteDance Seedance 2.0

Use for Seedance 2.0 specifically. Do not silently apply Seedance 2.5 duration or reference assumptions to this version.

## What to direct

ByteDance documents Seedance 2.0 as a multimodal audio-video model that accepts text, image, audio, and video references. It supports reference-driven generation, editing, extension, multi-shot video, and synchronized audio. Published limits can vary by the access surface; check the current UI or API instead of hardcoding limits into a prompt.

Seedance examples use ordinary natural-language direction and reference labels such as “@Image 1” and “@Video 1.” Use the exact labels shown by the user's interface. Explain each reference's role so the model does not have to guess which material supplies appearance, setting, motion, or sound.

## Prompt pattern

Start with the desired clip and its visual through-line. Add only the relevant subject, action, camera, environment, style, reference roles, and sound. For a multi-shot sequence, describe the sequence as separate beats, each with one main action and a readable camera choice.

~~~text
Create a 12-second warm, observational short in a neighborhood bakery.
@Image 1 is the baker's appearance. @Image 2 is the bakery interior. Use @Video 1 for hand movement only.
Shot 1, 0–4 s: Medium side view. The baker kneads dough on the wooden counter; the camera tracks slowly from left to right.
Shot 2, 4–8 s: Close-up of the baker dusting the dough with flour, then setting it into a metal tray.
Shot 3, 8–12 s: The baker slides the tray toward the oven and looks back with a small smile. End on a steady medium shot.
Audio: Light room tone and soft dough handling sounds; no dialogue or music.
Keep the same baker, clothing, and bakery across all shots.
~~~

If an uploaded reference clip is meant to provide only one attribute, say so explicitly. If audio is supplied, say whether to preserve it, use it as timing or style guidance, or replace it; do not imply that a generated soundtrack is an exact copy of an input track.

## Strengths and limits to account for

ByteDance describes stronger motion and audio-video instruction following than earlier Seedance versions, while acknowledging remaining issues with multi-subject consistency, exact text rendering, and complex edits. For a crowded scene, reduce simultaneous actions and specify who does what. Put critical on-screen copy in a later editable overlay unless the user specifically wants it generated in-frame. Review generated audio and text rather than promising exact fidelity.

Research checkpoint: 2026-10-03.

- [Seedance 2.0 official model page](https://seed.bytedance.com/en/seedance2_0)
- [Seedance 2.0 official launch and examples](https://seed.bytedance.com/en/blog/official-launch-of-seedance-2-0/)
