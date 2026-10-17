<!-- >>> greenline >>> -->
## Greenline gate — how merges work here

This repo is gated by **greenline**. Read `docs/greenline.md` and `docs/DOCTRINE.md`
before writing code or tests.

**Invariants (never violate):**
- `master` == what prod runs == green, always.
- The canonical checkout is pristine — never edit it by hand.
- All work happens in worktrees branched from last-green.
- Every merge goes through the serialized gate: change-impact `check` + real `deploy`.

**Your workflow:**
1. `greenline worktree <name>` — get a worktree at `/Volumes/Gumby/worktrees/greenline/daz-cad/<name>` on branch `gl/<name>`.
2. Do your work there. Co-design tests + code per docs/DOCTRINE.md (parallel-safe, namespaced, no global-state assertions, OS-assigned ports, probe the exact host:port instead of machine-wide `lsof`/`netstat`/`ss`/`fuser` scans; never mock other services — make real calls fast with a content-addressed record/replay cache).
3. Commit in your worktree. Then `greenline submit` (from that worktree).
4. The gate squash-merges, runs `./run check`, fast-forwards `master`, runs `./run deploy`, and publishes. It rolls back prod automatically if deploy fails.
5. On success: `greenline done` to remove your worktree + branch.

**Never** commit or push on `master` — hooks hard-lock it (reference-transaction
cannot be bypassed with `--no-verify`; pre-commit/pre-push refuse too). Never edit the
canonical checkout. If the gate reports a conflict, rebase your worktree on
`master` and resubmit. If commits somehow reached `master` outside the
gate (legacy workflow, hotfix), run `greenline adopt` to gate them in place —
greenline never discards commits on `master`.

Diagnose with `greenline status` and `greenline doctor` (`--fix` to reconcile).
<!-- <<< greenline <<< -->

## Model browser and preview cache

- `static/file-browser.css` styles the searchable model grid. Its URL in `static/editor.html` contains the CSS SHA-256 prefix; `src/startup_path_test.py` enforces the match and standalone packaging.
- Successful renders save an exact filename/source snapshot, then create a 192px transparent PNG during browser idle time. `CADViewer.captureThumbnail()` uses an isolated mesh-only render target, sRGB output and linear-space alpha correction without changing the viewport.
- `src/model_preview.py` stores immutable source-SHA256 PNGs in `local/model-previews/`, outside the models git repository. Unchanged saves retain source mtime and cached previews; stale uploads return 409. Existing files acquire previews when next successfully rendered.
- Browser scenarios live in `tests/bdd/features/file_browser.feature` and run through `src/file_browser_test.py`; real color/scheduling/save-race integrations live in `src/preview_race_test.py`. The test server uses the test-harness-only `DAZCAD_MODELS_DIR` and file-backed logs under `output/testing/`. Never capture an active uvicorn server in unread PIPE streams, which can block request handling when logs fill the pipe.
- Local release selection includes committed, dirty and untracked paths, so `./run check` covers edits before the first commit. Every check retains the browser, preview, worker/export and affected geometry coverage.
