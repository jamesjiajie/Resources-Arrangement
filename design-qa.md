**Comparison target**

- Source visual truth: `/Users/james/.codex/generated_images/019ff09c-4e1d-7ba3-a54e-173d3517ec23/exec-7ca53f93-a11b-4136-a5a1-64fc1263881c.png`
- Implementation: browser-rendered Resource Sandbox at `http://127.0.0.1:8000/`, captured in the Codex in-app browser during this QA run.
- Viewport: 1280 × 720 CSS pixels, desktop, Chinese UI, project constellation view. The source is a 1488 × 1058 desktop composition; comparison is normalized to the same desktop information architecture rather than a 1:1 crop.
- State: source has one project expanded and all other projects collapsed; implementation was checked in the equivalent selected-project state, first `Commercial Fixed`, then `AI Hub` after selection.

**Full-view comparison evidence**

The browser capture visibly shows all 13 project nodes, a centered selected project, radial project links, small pixel-avatar member orbit, minimap, density controls, summary counts, and a right-hand selected-project inspector. The source mock uses the same hierarchy and interaction model. Focused inspection covered the selected center card, project-node labels, the member orbit, and the inspector member rows.

**Required fidelity surfaces**

- Fonts and typography: existing app font stack and title hierarchy are retained. Project labels use compact, readable weights; long project names truncate rather than overflow.
- Spacing and layout rhythm: desktop canvas, inspector, toolbar, controls, and project nodes preserve the design's compact working-area rhythm. The 13-node layout remains inside the canvas at the verified desktop viewport.
- Colors and visual tokens: existing navy shell and teal primary token remain in use; teal marks normal relationships, amber marks risk links, and status colors match the existing product language.
- Image quality and asset fidelity: generated pixel-art avatars are used as raster assets, cropped from an 8-avatar sheet into 26–27px tiles. The final browser capture confirms the avatars render crisply in both orbit and inspector rows.
- Copy and content: Chinese labels identify project count, people, assignments, cross-project people, selected-project details, density, reset, and risk notes. Live project and member names come from the existing overview payload.

**Findings**

No actionable P0, P1, or P2 differences were found for the selected desktop constellation state.

- [P3] Capacity figures can be zero when the global baseline date falls outside the imported allocation month.
  Location: selected-project node and inspector.
  Evidence: the verified page uses baseline date 2026-09-01 while the imported August allocations are no longer current, so live `member_load` is 0%.
  Impact: this is correct date-scoped data behavior, but it is visually less representative than the stress-test mock.
  Follow-up: consider preserving the last imported resource month as the default baseline date after import.

**Primary interactions tested**

1. Opened the Resource Sandbox navigation entry.
2. Confirmed all 13 projects, 45 people, and 47 assignments are represented.
3. Selected `AI Hub` from the constellation and confirmed the inspector and expanded member orbit update.
4. Confirmed console errors and warnings: none.
5. Confirmed production build: `npm run build` passes.

**Implementation checklist**

- [x] Replace person-to-task rows with project constellation semantic zoom.
- [x] Keep one selected project expanded and the remaining projects compact.
- [x] Add raster pixel-avatar asset and display it in selected-project relationships.
- [x] Add filtering, text search, density control, reset, minimap, project inspector, and responsive fallback.
- [x] Verify build, browser rendering, interaction, and console output.

**Follow-up polish**

- Optional: preserve the latest imported resource period in the date control after an Excel import.

**Accordion detail iteration**

- Source interaction design: the approved right-inspector member accordion, with task, stage, allocation, period, status, source notes, and a single expanded member at a time.
- Browser evidence: 1280 × 720 desktop capture on the Resource Sandbox. `Chen, Jett WJ` was expanded after `Cai, Wayne WC`; exactly one `.member-details` region remained open. The expanded assignment showed `Implementation`, `100%`, `2026-08-01 — 2026-08-31`, source notes, and the "不在当前基准日期内" state.
- Date semantics: risk cards are now calculated from assignments active on the baseline date only. With baseline date `2026-09-01` and August-only source assignments, zero risk cards were rendered; the task retains its historical detail instead of incorrectly reporting a current high-load warning.
- Task focus: selecting a detail task produced one highlighted center project and one highlighted matching orbit avatar, connecting inspector selection back to the constellation without changing layout.
- Console errors and warnings: none in a fresh browser tab.
- Build: `npm run build` passed after the iteration.

No actionable P0, P1, or P2 differences were found in the expanded-member state. The nested detail card remains within the inspector scroll region and does not alter constellation layout.

final result: passed

**Work-detail simplification iteration**

- Source visual truth: `/Users/james/.codex/generated_images/019ff09c-4e1d-7ba3-a54e-173d3517ec23/exec-061f3d05-7b6f-4ec2-b353-b46988bdca3b.png` (selected first work-detail direction).
- Implementation: browser-rendered Resource Sandbox at `http://127.0.0.1:8000/`, captured in the Codex in-app browser during this QA run.
- Viewport: 1280 × 720 CSS pixels, desktop, Chinese UI; source is an image-generation mock at 1212 × 1296 pixels, so the comparison is normalized to the expanded-member detail region rather than full-screen scale.
- State: `Commercial Fixed` selected; `Cai, Wayne WC` expanded; the first assignment selected.

**Full-view and focused comparison evidence**

The reference and the browser-rendered implementation were viewed together in the QA pass. The implementation uses the source's label-and-value hierarchy within the actual 290px inspector: work content is first and uses the full available row width; status, allocation, and period follow as light, divider-separated rows; the out-of-baseline warning uses amber. The existing pixel avatar and member header remain intact.

**Findings**

No actionable P0, P1, or P2 differences were found.

- [P3] The production inspector is materially narrower than the generated mock, so the supplied long English task title wraps to two lines. This preserves the intended work-first hierarchy and avoids truncating the task.

**Required fidelity surfaces**

- Fonts and typography: existing product type scale is retained; the task title is the strongest detail text, with 10–11px metadata labels and status values.
- Spacing and layout rhythm: the nested rounded card was removed. Rows use lightweight dividers and a compact vertical rhythm compatible with multiple assignments.
- Colors and visual tokens: existing navy text, teal status/allocation values, muted label text, and amber period warning are preserved.
- Image quality and asset fidelity: the existing pixel avatar remains unchanged and renders crisply in the expanded member header.
- Copy and content: the detail only shows work content, status, allocation, time range, and the date-context warning. `Implementation`, PM, Stage, Source, and HKPM are absent.

**Primary interactions tested**

1. Opened Resource Sandbox and expanded `Cai, Wayne WC`.
2. Selected the assignment and confirmed exactly one task is selected.
3. Checked rendered detail text: no `Implementation`, PM, Stage, Source, or HKPM content is present.
4. Confirmed browser console errors and warnings: none.
5. Confirmed production build and Python test suite pass.

final result: passed

**Constellation hierarchy fidelity iteration**

- Rechecked against the same approved source at a 1280 × 720 desktop viewport after replacing the uniform rectangular spoke layout.
- The selected project is now a compact teal pill inside a pale dashed project domain. Its member avatars are independently named nodes within that domain, with lighter internal relationship lines.
- The other 12 projects are circular, color-coded outer nodes. Each node shows people, assignments, and the imported plan total while keeping the date-scoped current load in the inspector.
- Outer links now begin at the project-domain boundary instead of crossing the center, use lower visual weight, and keep risk coloring as a secondary signal.
- Verified project semantic zoom by switching from `Commercial Fixed` to `Now-TV`: exactly one selected project remained, the canvas member count changed from 8 to 1, and the inspector member count matched.
- Verified member accordion after project switching: exactly one task-detail region opened.
- Console errors and warnings: none.
- Production build: `npm run build` passed.

No actionable P0, P1, or P2 fidelity or interaction issues were found in the revised hierarchy.

final result: passed
