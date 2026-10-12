# Issue #3: Fix Windows XML pathurl for Premiere and Resolve

Source issue: https://github.com/seblacheray/Playlist2Premiere/issues/3

## Context
Playlist2Premiere exports Final Cut Pro 7 XML (xmeml). On Windows, test media comprised three 1080p 25fps MP4 files (no audio), lengths 124, 123, 71 frames, 318 frames total (12s18f). Original XML import into Premiere Pro 2026 displays second Part2 timeline clip as black/hatched, although same source plays in source monitor and manual timeline placement works.

## Isolated experiment
Three otherwise identical XML variants tested in fresh Premiere projects:
- A: remove video `<sourcetrack>` only, retain original `pathurl` => FAIL (Part2 black)
- B: change `pathurl` to Premiere-exported style only, retain `<sourcetrack>` => PASS
- C: both changes => PASS

Variant B also imported successfully into DaVinci Resolve 21.1.1. Three clips in correct order, no gap or overlap, all images visible, total 318 frames at 25fps.

## Required change
- Implement ONLY variant B in XML export code: format Windows file URI paths as Premiere's reference XML `file://localhost/D%3a/_Le%20crash/...` rather than original `file:///D:/_Le%20crash/...`.
- Ensure URI encoding is correct for Windows drive letters, spaces, accents, special and reserved characters. Avoid double encoding.
- Keep existing video `<sourcetrack>` elements and all clip start/end, in/out, durations, FPS, duplication/order, media linking, and audio logic unchanged.
- Add/update regression tests for Windows paths including accents, spaces, reserved characters and XML validity.
- Run tests and open a focused pull request; DO NOT merge automatically.
- Do NOT rename Playlist2Premiere yet (Playlist2XML rename is future separate work).

## Post-fix acceptance
Build a new Windows executable with GitHub Actions. Export the same 3-media test playlist and reimport generated XML into Premiere Pro 2026 and DaVinci Resolve 21.1.1. Previous checks validated *experimental XML*, not the resulting app binary.

This brief mirrors GitHub issue #3 because the Codex environment was unable to fetch the issue API endpoint (Forbidden/404), while Git access works.
