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

**Sample-directed command sandbox redesign**

- Source visual truth: `docs/resource-command-sandbox/reference-sample.png`, copied unchanged from the user-provided reference image (1487 × 1058).
- Implementation evidence: `docs/resource-command-sandbox/implementation-sample-redesign.png`, captured from the running app in the Codex in-app browser. The browser display capture is 2560 × 1440; the responsive page was checked with the desktop viewport override and the full comparison was normalized to a common 720px height in `docs/resource-command-sandbox/sample-comparison.png`.
- Tested state: baseline date `2026-09-08`, with the visibly labeled latest real-data snapshot from `2026-08-31`; no demo records are present.

**Full-view and focused comparison evidence**

The reference and implementation were placed side by side in the same comparison image. The implementation follows the reference hierarchy: dark navigation rail with an expanded resource-sandbox group, compact search/date/actions bar, six KPI cells, map controls, a pale tabletop deployment board, perimeter project objectives, linked personnel and task nodes, legend, and a fixed right-side personnel inspector.

The first browser pass retained the earlier scenic relief background, which was a P1 mismatch against the reference's quiet planning-board surface. It was replaced with a pale low-contrast grid asset and rechecked in the final comparison. Real project names and staffing totals make the production board naturally sparser than the illustrative reference; the hierarchy, interaction targets, and information density remain intact.

**Required fidelity surfaces**

- Typography: strong navy page title, compact operational labels, emphasized KPI values, and restrained secondary metadata match the reference hierarchy.
- Layout: sidebar, toolbar, metric strip, central board, and inspector preserve the reference's desktop proportions and grouping.
- Color and depth: dark navy navigation, teal actions and connections, amber project accents, white raised cards, soft shadows, and the pale grid board reproduce the reference's visual system.
- Content: live people, projects, assignments, allocation, periods, tags, and notes come from the existing application data; the fallback uses the latest real snapshot and states its date.
- Assets: existing local staff portraits are reused, and the board texture contains no baked-in labels, nodes, or UI text.

**Primary interactions tested**

1. Selected `He,Crystal YY` on the board and confirmed the inspector heading and assignment content updated.
2. Activated `聚焦`, then `重置`, and confirmed the board returned to its default deployment state.
3. Confirmed all expected project, person, task, legend, and inspector controls are present in the accessibility tree.
4. Confirmed browser console errors: none.
5. Confirmed `npm run build`, `node --test tests/command-sandbox.test.mjs`, `git diff --check`, and CodeGraph freshness checks pass.

No actionable P0, P1, or P2 differences remain after the background correction.

final result: passed

**Experimental command sandbox iteration**

- Selected visual direction: personnel-first military-style deployment board, reference at `docs/resource-command-sandbox/reference.png`.
- Implementation: `实验性沙盘` at `http://127.0.0.1:8000/`, verified in the Codex in-app browser on 2026-09-08 with the Chinese interface.
- Visual surfaces checked: generated relief-board background, project objectives, personnel roster, selected-person command core, normal and blocked routes, task cards, and right-side deployment inspector.
- Interactions checked: opening the new sidebar entry, selecting a task card, viewing assignment details, and switching from `倾视` to `顶视`.
- Data behavior: live assignments are scoped to the global baseline date. When none are current, the page visibly announces and uses a labeled demo posture; choosing a date with active assignments replaces it with the live people, projects, tasks, and risk states.
- Data update: demo records were removed. When the baseline date has no active work, the sandbox now renders the latest available snapshot from the user's own assignments and labels that snapshot date.
- Build and logic validation: `npm run build`, `node --test tests/command-sandbox.test.mjs`, and `git diff --check` all pass.
- Console/runtime errors observed: none.

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

**Command sandbox cartoon-avatar correction**

- Replaced the rotating photographic portraits with the existing eight-character cartoon sprite sheet.
- Avatar selection is stable by member ID and split into explicit female and male avatar pools. Existing `gender` or `sex` data takes precedence; the current imported roster uses a reviewed first-name mapping for female members and a male fallback.
- Verified the high-density board with `Wang, Reo HH`, `He,Crystal YY`, `Chen, Jett WJ`, `Huang, Zinnia ZY`, `Lin, Linda YY`, and `Xu, Alan JL` visible together. Male and female presentation matched the roster mapping.
- Selected `He,Crystal YY` and confirmed the same cartoon identity appears in the board node and right-side inspector.
- Browser console errors: none. Production build, command-sandbox tests, and diff check pass.

final result: passed

**Command sandbox full-project visibility**

- Removed the command board's fixed six-project medium-density and eight-project high-density truncation.
- Project cards now use a generated perimeter layout and render every project in the current real-data snapshot; density continues to control the number of people shown.
- Verified `13` project cards from the August 31 snapshot. This is one selected project plus the 12 surrounding projects seen in the relationship constellation.
- Added the rendered project count beside `编组部署图` so the board's scope is explicit.
- Desktop visual check confirmed all cards are reachable around the board perimeter. Browser console errors: none.
- Production build, command-sandbox tests, diff check, and CodeGraph freshness check pass.

final result: passed

**Zoned deployment redesign — selected direction 1**

- Source visual target: `docs/resource-command-sandbox/zoned-layout/reference.png` (1354 × 1161), the first displayed Product Design Ideate result selected by the user.
- Rendered implementation: `docs/resource-command-sandbox/zoned-layout/implementation.png` at a 1488 × 1058 desktop viewport; the board region is saved as `implementation-board.png` (826 × 684).
- Comparison evidence: `docs/resource-command-sandbox/zoned-layout/comparison-board.png`, with the source and implementation board normalized to a common 720px height in one side-by-side image.
- State: medium density, latest real-data snapshot dated `2026-08-31`, `Wang, Reo HH` selected, 13 project cards visible.

**Findings and fixes**

No actionable P0, P1, or P2 differences remain. The previous perimeter layout's card collisions, bottom clipping, and line crossings were removed by grouping projects inside bounded zones and replacing project-to-person spokes with bundled zone routes.

- [P3] The production board is narrower than the standalone generated target because the existing 330px person inspector remains visible. Project text and zone headings are correspondingly more compact, while all labels stay readable and all 13 projects remain visible.
- [P3] Real task names are longer than the illustrative target, so the two center task nodes retain the existing ellipsis behavior.

**Required fidelity surfaces**

- Fonts and typography: the source hierarchy is retained with colored zone headings, bold project names, orange load values, teal person load, and muted hour metadata.
- Spacing and layout rhythm: five collision-free project zones surround a generous central personnel area; the legend has a dedicated footer strip and no longer overlaps project cards.
- Colors and visual tokens: blue, green, violet, teal, and orange zone tints use the existing navy/teal/orange product system over the pale planning-board texture.
- Image quality and asset fidelity: the existing cartoon avatar asset is reused at native crop proportions with stable person mapping; no visual placeholder is present.
- Copy and content: the selected direction's five zone names, all 13 real project names, four default personnel nodes, load, hours, snapshot date, task nodes, and legend semantics are present.

**Primary interactions tested**

1. Selected `Commercial Fixed`; the board filtered from 13 project cards to the selected project.
2. Used `重置`; all 13 project cards returned in their zones.
3. Selected `He,Crystal YY`; the right inspector updated to the matching person and assignment.
4. Switched map density to `较高`; six compact personnel nodes rendered without project-card collision.
5. Browser console errors: none. Production build, three command-sandbox tests, diff check, and CodeGraph freshness check pass.

final result: passed

**Compact personnel nodes and high-density default**

- Source evidence: user-provided crop showing oversized central personnel cards and the map-density selector.
- Implementation changes: reduced normal personnel cards from 112px to 96px wide, high-density cards to 82px wide, reduced avatars and type proportionally, widened the six-person formation, and moved task nodes outward.
- Default behavior: map density now initializes to `较高`; `重置` also restores `较高`.
- Static validation: production build, three command-sandbox tests, and diff check pass.
- Browser visual verification: blocked because the Mac locked before the refreshed implementation could be captured. The in-app browser retry could not unlock the Mac.

final result: blocked

**Command sandbox direct layout editing**

- Source visual target: /Users/james/.codex/generated_images/01a07cc7-da75-7f12-b111-179ccf7ce8bb/exec-bcc4cd67-29cc-4013-a923-f79a0fe628b9.png, the selected inline-edit and direct-drag direction.
- Implementation: Experimental Command Sandbox at http://127.0.0.1:8000/, checked in the Codex in-app browser on 2026-09-09.
- State: latest real-data snapshot dated 2026-08-31, high density, default five-zone layout, 13 real project cards and six personnel nodes.

**Comparison and findings**

The implementation preserves the selected source hierarchy: five lightly tinted operational zones, small drag handles at zone and project level, inline zone-name editing, a pale tactical board, compact cartoon personnel nodes, route lines, and restrained save feedback. The implementation adds the requested project cross-zone move state with a floating project preview and a highlighted target zone.

No actionable P0, P1, or P2 differences remain. At the in-app browser's available narrow desktop surface, the board retained a measured 881 by 625 canvas: all five zones were contained within the board and all 13 project cards remained represented. The app shell's existing narrow-width navigation occupies the top of the visible browser panel; this is outside the command-sandbox component and does not change the desktop target layout.

**Primary interactions tested**

1. Edited the core infrastructure zone inline, confirmed the name, then used undo to restore it.
2. Dragged Commercial Fixed by its dedicated handle into the overseas and finance zone; the zone counts changed from 3/2 to 2/3 and the success message named the project and destination.
3. Undid the project move and confirmed the original zone counts returned.
4. Dragged the complete core zone to a new position and confirmed the dirty state appeared.
5. Saved the changed layout, restored defaults, and saved the default state for handoff.
6. Confirmed all five zones remain inside the board bounds and all 13 project cards are rendered.
7. Browser console errors: none. Production build, three command-sandbox tests, diff check, and CodeGraph freshness check pass.

final result: passed
