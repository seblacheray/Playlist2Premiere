# Windows Actions failure: UNC media path handling

## Evidence
GitHub Actions run: https://github.com/seblacheray/Playlist2Premiere/actions/runs/38306565372
Job build, step "Run all tests including media integration" failed: **25 passed, 1 failed** (test_paths in tests/test_engine.py). The subsequent PyInstaller build and artifact upload were skipped.

Trace: src/playlist2premiere/paths.py, MediaResolver.resolve(), candidate.is_file() -> pathlib.Path.stat() -> OSError [WinError 64] "The specified network name is no longer available" for a deliberately nonexistent UNC path `\\\\serveur\\partage\\été & #1.mp4`.

## Requested fix
- Make MediaResolver robust to inaccessible UNC/network paths on Windows: handle relevant OSError during candidate existence checks, then fall back to existing unique basename search under media_dir.
- Preserve behavior for valid local/UNC paths, ambiguity detection, missing media, and other playlist path types. Avoid silently swallowing unrelated programming errors; use narrowly scoped exception handling.
- Add or adjust Windows regression tests for unavailable UNC paths and fallback. Make tests independent of a real network share; use mocking where appropriate. Consider behavior of `rglob` / `is_file` on inaccessible entries if applicable.
- Keep the XML pathurl variant B fix from PR #4 unchanged. Do not rename Playlist2Premiere.
- Run tests on Windows if possible. Open a focused PR into main, no auto-merge. If API access prevents PR creation, push branch and report branch name and commit.
- After merging, verify Actions passes all tests, PyInstaller builds portable EXE and uploads artifact; then manual XML import into Premiere Pro 2026 and Resolve 21.1.1.

This task is distinct from issue #3. Do not edit this docs-only branch or merge it.
