# Resource Sandbox Design QA

- Source visual truth: `/Users/james/.codex/generated_images/019ff09c-4e1d-7ba3-a54e-173d3517ec23/exec-d619f985-2844-46f7-9167-f580b785c082.png`
- Implementation screenshot: `/Users/james/Document/Projects/Resources-Arrangement/sandbox-implementation-final.png`
- Combined comparison: `/Users/james/Document/Projects/Resources-Arrangement/sandbox-design-comparison.png`
- Browser viewport: 1440 x 1024 CSS px
- Source pixels: 1487 x 1058
- Implementation pixels: 1440 x 1024
- Density normalization: both images were normalized to 720 x 512 inside a 1440 x 548 side-by-side comparison; no browser chrome was included.
- State: Chinese desktop view, `资源沙盘` selected, graph mode, all projects, no search term, `陈安` selected. The local database was empty, so the implementation visibly uses its labeled sample-data state.

## Full-view comparison evidence

The implementation preserves the target's major composition: 260 px dark navigation rail, light workspace, title and date controls, people column, allocation connections, task/project column, and a right-side detail inspector. The selected person, overload colors, blocked states, capacity ring, related-work list, and risk panel all retain the intended hierarchy.

The implementation intentionally uses straight allocation lines instead of the mock's decorative curves so line weight remains stable with live data and responsive layout. The empty-database notice adds one row above the sandbox; it disappears automatically when real assignments are available.

## Focused comparison evidence

- Header and navigation: entry order, active treatment, typography, dark sidebar, amber RA mark, teal actions, and compact radii match the existing product and source direction.
- Relationship stage: person portraits are sharp 256 px generated assets with consistent studio treatment; allocation lines use teal, orange, and red semantic tokens; task cards retain the source's project, status, task, and date hierarchy.
- Detail inspector: selected identity, capacity visualization, available-hours summary, related work, and risk warning match the target structure without clipped text at 1440 x 1024.

## Required fidelity surfaces

- Fonts and typography: system UI stack matches the existing application; title, section, body, metadata, and status weights are coherent and remain readable at the target viewport. No truncation or broken wrapping was observed.
- Spacing and layout rhythm: the main three-column relationship structure and right inspector fit the viewport. The first pass stacked every assignment as a separate card and created excessive height; the final pass groups each person around one primary task card while preserving every connection and all related work in the inspector.
- Colors and visual tokens: the implementation reuses the repository's navy, teal, amber, red, muted text, border, background, and shadow tokens. Semantic overload, blocked, planned, and normal states are consistent.
- Image quality and asset fidelity: four generated employee portraits were resized to 256 px and load crisply in circular crops. No placeholder glyphs, broken images, or compression artifacts were observed.
- Copy and content: Chinese labels are coherent and match the selected concept. The sample-data notice clearly distinguishes demo content from live data.
- Icons: the implementation uses the project's existing icon family with consistent stroke weight and alignment.
- Accessibility: semantic buttons, inputs, select controls, image alt text, active navigation state, and visible focus styles are present. Color is supplemented by percentages and text labels.

## Interaction and runtime checks

- Navigation to `资源沙盘`: passed.
- Person selection and inspector update (`陈安` to `李敏`): passed.
- Search for `回归` reducing the stage to one matching row: passed.
- Project filter: passed.
- Graph/list toggle and active state: passed.
- Default-state restoration: passed after reload.
- Browser console warnings/errors: none.
- Production build: passed with Vite.

## Comparison history

1. Pass 1 finding — P2: every assignment rendered as a full task card, causing the graph to run below the target viewport and weakening the one-person/one-primary-task rhythm.
   - Fix: retained all allocation lines and inspector items, but reduced each person row to one primary task card.
   - Post-fix evidence: `sandbox-implementation-pass2.png` and the final screenshot show all four people, legend, and detail panel within 1440 x 1024.
2. Pass 2 result — no actionable P0/P1/P2 differences remained. Browser interactions and console checks passed.

## Follow-up polish

- P3: replace straight allocation lines with measured curves only if future live-data testing confirms that curves remain readable with many concurrent assignments.
- P3: with live data, the sample-data notice disappears and the content begins closer to the source's vertical position.

final result: passed
