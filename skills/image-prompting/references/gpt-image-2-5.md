# GPT Image 2.5

Use for image creation and editing with GPT Image 2.5. This is an image model, not a video-generation model.

## Select the model for the task

OpenAI's current documentation distinguishes two GPT Image 2.5 choices:

- GPT Image 2.5 Flare is optimized for speed and iterative everyday work.
- GPT Image 2.5 Sunburst is optimized for higher quality and demanding detail or editing precision.

These are model-selection choices, not words to insert into the prompt. If the user's ChatGPT surface selects the model automatically, focus on writing the request rather than trying to override its routing. Check the current product or API for live model IDs and controls.

## Write a clear image brief

Lead with what the image is for and what must be visible. Describe subject, composition, style, light, materials, and constraints as needed. Include exact aspect ratio, crop, or size in the tool's settings when available instead of assuming those words in the prompt force a technical output size.

For reference-based creation or edits, assign each image a clear role: subject identity, object details, pose, composition, palette, or style. State what should be borrowed and what should not. To preserve an existing image, name the invariants and limit the edit:

~~~text
Change only the jacket to a dark green wool coat.
Preserve the person's identity, face, hair, expression, pose, body shape, camera angle, and background.
Match the original lighting and shadows so the new garment fits naturally.
Do not add text, logos, accessories, or other changes.
~~~

For a new image, a useful structure is:

~~~text
Create a [use] showing [subject and action].
Composition: [framing, viewpoint, subject placement, and space reserved for copy].
Details: [important objects, materials, expression, environment].
Visual direction: [medium or photographic treatment, lighting, palette, texture].
Constraints: [exact text, preservation needs, and unwanted additions].
~~~

Do not mechanically fill every field. Use the few controls that matter for this image.

## Iterate and inspect

Refine one material change at a time. Check the result for subject or product preservation, composition, text accuracy, unwanted changes, and transparency when requested. When producing an edit series, restate the most important preservation constraints in later turns rather than assuming every detail will persist.

For transparent output, choose a transparent-background option in the interface or API and use a format that retains alpha. Do not ask the model to draw a checkerboard as a substitute. If exact logo geometry, small print, or brand text must be perfect, generate a clean art direction with space for editable text or apply a verified source asset afterward.

The official guide includes separate prompting patterns for text, diagrams, reference images, product edits, and style transfer. Check it for the current behavior and controls before advising on an API workflow.

Research checkpoint: 2026-10-03.

- [OpenAI GPT Image 2.5 prompting guide](https://developers.openai.com/api/docs/guides/image-prompting)
- [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- [GPT Image 2.5 Sunburst model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst)
