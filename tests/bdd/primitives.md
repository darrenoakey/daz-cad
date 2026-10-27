# BDD primitives — daz-cad

The Gherkin scenarios in `tests/bdd/features/` are fulfilled by co-located
pytest + Playwright suites (for example `src/file_browser_test.py` fulfills
`tests/bdd/features/file_browser.feature`). The step phrasings below are the
shared vocabulary those suites implement; they are plain helper functions in
each `*_test.py`, not a separate runner.

## Reachability primitives

| Step phrase | Implementation |
| --- | --- |
| `the CAD application is running` | session `server` fixture (uvicorn on an OS-assigned port) |
| `I browse to "/"` | `page.goto(f"{server}/")` |
| `the CAD editor is visible` | wait for `#status-text === 'Ready'` and `window.Workplane` |
| `the file browser panel is visible` | click `#file-selector-btn`, await its list response and populated cards, expect `#file-dropdown` visible |

## File browser primitives (`src/file_browser_test.py`)

| Step phrase | Implementation |
| --- | --- |
| `I click the file selector button` / `I open the file browser` | `_open_panel(page)` |
| `I create a new model "name"` | fill `#new-file-input`, click `#create-file-btn`, expect `#filename-display` |
| `the editor loads "name"` | `#filename-display` contains the name, editor reaches Ready |
| `I change the source from a box to a cylinder` | `_type_source(page, CYLINDER_SOURCE)` via the Monaco surface |
| `the model finishes rendering` | wait for the `PUT /api/models/{name}/thumbnail?revision=…` response |
| `exactly one new thumbnail is cached` | recorder list holds two distinct sha256 revisions for the model |
| `I enter an invalid source` | replace the script with `INVALID_SOURCE` (unbalanced call) |
| `the editor reports a render error` | `#status-text` becomes `Error`, `#error-overlay` is visible |
| `the card still shows its cached thumbnail` | card's `img.file-preview` completes with `naturalWidth > 0` |
| `I sort the file browser by "X"` | `select_option` on `#file-sort` (`recent`, `name`, `name-desc`) |
| `I search the file browser for "X"` | fill `#file-search`, read grid order via `data-filename` |
| `the file count matches the visible cards` | `#file-count` text `N of M models` agrees with card count |
| `I press Escape` / `I click the editor outside the panel` | keyboard `Escape`, or click the viewport's lower-right corner outside the panel |
| `the file selector button has focus` | `expect(#file-selector-btn).to_be_focused()` |
| `I record network requests` | `_attach_recorders(page)` tracks request lifecycle and writes |
| `no render or thumbnail save requests were made` | `_await_quiet` then assert the writes list is empty |

## Gridfinity generator primitives (`src/gridfinity_generator_test.py`)

| Step phrase | Implementation |
| --- | --- |
| `the editor toolbar contains "Generators"` | visible `#generator-btn` |
| `I click "Generators" in the toolbar` | click `#generator-btn` |
| `the Generators panel is visible` | expect `#generator-panel` visible |
| `the generator menu offers "Segmented Gridfinity baseplate"` | selected option text in `#generator-kind` |
| `I set the Gridfinity width to "N" units` / `depth` | fill `#generator-x` / `#generator-y` |
| `I set the printer build area to "N" mm` | fill `#generator-bed-area` |
| `the panel reports four balanced segments with remainder units distributed evenly` | inspect `#generator-summary` for balanced axis partitions |
| `the panel shows a positive-integer validation error` | fill `#generator-x` with zero; assert summary error state |
| `I click "Generate baseplate"` | click `#generator-create`; assert editable Monaco source and rendered preview |
| `I click the "3MF" export button` | click `#download-3mf-btn` while recording a browser download |
| `one 3MF download contains both baseplate segments and their snap connectors` | inspect the downloaded real 3MF package's mesh objects and names |

The module maps these four scenarios to its Playwright test and records per-run durations in `tests/bdd/perf.json`. New generator modules register through `static/generator-registry.js`; the registry-backed UI test in `src/startup_path_test.py` proves late registration adds a selectable form and source generator without changing the menu controller.

## Long-running geometry checks

`src/gridfinity_generator_test.py::test_generator_ui_creates_segmented_model_and_one_complete_3mf` runs real OpenCascade segmentation, snap booleans, mouse-ear unions, and 3MF export; a cold run has exceeded five minutes. Always launch this test detached with a logfile and durable exit-code file, then use the AgentD3 `sleep` tool to resume and inspect that exact job's verdict/log. Never run it inline, poll it, or concurrently with another OpenCascade browser test. A failed result must be diagnosed before another run.
## Printability primitives (`src/file_browser_test.py`)

| Step phrase | Implementation |
| --- | --- |
| `the Printability panel is visible` | click the **Print for FDM** toolbar button and expect `#printability-panel` visible |
| `I preserve mating edges "selector"` | fill `#printability-preserve` with a CAD edge selector |
| `I click "Apply Printability"` | click `#printability-apply`; the worker validates source and generated solid before Monaco changes |
| `the editor script contains "optimizeForPrinting"` | inspect Monaco's visible generated source |
| `the Worker Console reports the printability changes` | expect named `base-chamfer` and `vertical-fillet` audit entries |
| `the editor script remains unchanged` | compare Monaco text after rejected settings |

## Recording primitives

- `_attach_recorders(page)` tracks the actual in-flight requests in
  `_fb_pending`, model writes (`_fb_writes`) and thumbnail PUT revisions
  (`_fb_thumbnails`). Tests wait with `_await_quiet(page)` before asserting
  that something never happened, so stragglers from earlier renders are never
  misattributed.
- `record_duration` + `write_perf` fixtures attribute each test's wall time to
  its scenarios in `tests/bdd/perf.json` (ten-run history).

## Data rules

Every test creates its own `test-fb-{uuid}…js` models through the UI; the
session server isolates `DAZCAD_MODELS_DIR` to a temp root, so cleanup is the
fixture's page close and nothing shared is ever touched. Later read-only tests
may select models created earlier in the same module run. All assertions read
only this run's namespace — never global counts or order across other models.
