# ByteDance Seedance 2.5

Use for Seedance 2.5 specifically. Its longer storytelling and expanded reference handling make shot planning more important; they do not make every task better as one long prompt.

## Prompt pattern

Seedance 2.5 supports longer audio-video clips, multi-round extensions, and expanded image, video, and audio referencing. ByteDance's examples use clear prose, labels such as “@Image 1” and “@Video 1,” and timed shot plans. Use the exact reference labels available in the selected interface and verify its current input limits.

For a clip with several beats, plan a timeline and keep it internally consistent:

~~~text
Create a 20-second cinematic scene. Keep the same subject, wardrobe, location, and lighting throughout.
@Image 1 defines the lead's appearance. @Image 2 defines the room. @Video 1 supplies camera movement only.
0–5 s: Wide shot. The lead enters from frame left and stops by the window; slow dolly in.
5–11 s: Medium close-up. The lead opens the envelope and reads the first line; camera holds steady.
11–16 s: Close-up. Their expression shifts from uncertainty to relief; a small exhale.
16–20 s: Pull back to the original wide composition as they set the letter down. End in a still frame.
Audio: Quiet room tone and paper movement; no music or extra dialogue.
~~~

For editing, name the source clip, the exact attribute to alter, and everything to preserve. For extension, describe how the new segment continues the final state of the reference: subject position, action, sound, and camera movement. Avoid adding a new plot beat unless the user requested one.

## Directing choices

- Use a continuous take only when the action and camera can plausibly stay continuous. If the story needs cuts, mark the shots and transitions.
- Give each time range one primary action and one camera plan. Do not stack multiple incompatible moves into every beat.
- For several subjects, identify each by the reference label or a stable visual description, then state their spatial relation and action.
- For intended on-screen words, provide exact copy and placement; recommend a post-production overlay when exact typography is essential.
- Keep requested audio clear: dialogue, ambience, effects, and music should not conflict. If no music is wanted, say so.

ByteDance's launch material describes physical-plausibility and multi-subject consistency as areas that still need improvement. Keep complicated interactions simple enough to evaluate, and treat each extension as a new result to review.

Research checkpoint: 2026-10-03.

- [Seedance 2.5 official model page](https://seed.bytedance.com/en/seedance2_5)
- [Seedance 2.5 official launch and prompt examples](https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5)
