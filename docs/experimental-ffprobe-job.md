# Experimental native Windows FFprobe job

## Isolation and status

Workflow **Experimental Windows FFprobe**, job `candidate`, uses windows-2022 plus MSYS2 UCRT64/MinGW-w64. It runs on relevant PR changes or manual dispatch when the workflow is available. It does not feed the portable build job, modify find_ffprobe, change the pinned BtbN binary, enable distribution, merge or create a Release.

The scripts and workflow were checked locally. Native Windows compilation/result and candidate size are pending GitHub Actions: run/status/artifact API requests return Forbidden here. No successful Windows compile or measured candidate size is claimed. Inspect the artifact before concluding success.

## Build inputs and conservative profile

`fetch_ffprobe.py` downloads the existing hash-locked baseline and the exact FFmpeg source ZIP for revision 615b07170e30d79ad5906418ea49f81c3cbd8457. No unverified source upgrade is introduced. The source ZIP has no Git metadata; the candidate's extra-version identifies the pinned source revision without inventing an upstream Git-describe version.

`build_ffprobe.sh` retains native demuxers, decoders, parsers and bitstream filters, and builds only ffprobe. It removes encoding/muxing/devices/filters/network protocols/hardware accelerators and disables optional autodetection. It explicitly includes static zlib to preserve compressed MOV/Matroska probing where applicable, and uses Win32 threads. No format whitelist and no disable-everything. It keeps swscale/swresample as needed. NASM is omitted in this first experiment via disable-x86asm; performance must be checked before replacement.

MSYS2 GCC, binutils, pkgconf and zlib packages are installed with package-signature verification left intact. The exact installed versions and hashes of cached package archives are recorded, but MSYS2 package updates and setup action tags are not yet immutable. This job is an experimental input-traceability step, NOT a bit-for-bit reproducible toolchain or complete corresponding-source package. MinGW/GCC runtime and zlib source/notices still need exact collection and review. No source-correspondence flag is changed.

Two compile processes are used to bound memory use; make V=1 exposes commands. Linker maps and symbol/import listings document what is actually linked. The candidate is stripped separately while the unstripped build is retained only within the runner for symbol evidence. Both hashes and the stripped byte size are reported. A failing configure/build/native run leaves a status file and logs; EXIT cleanup preserves generated config and link evidence.

## Corpus and comparison semantics

The pinned baseline FFmpeg generates five small real-media fixtures in a directory and filenames containing accents, spaces, &, #, + and %:

- MP4 H.264/AAC at 25 fps.
- MP4 H.264/AAC at 30000/1001.
- MP4 HEVC/AAC at 25 fps.
- MKV H.264/AAC at 25 fps.
- MP4 H.264 with two separate AAC audio streams at different sample rates.

Both probes use exactly `-v error -show_streams -show_format -of json <absolute path>`, matching the application, with its 120-second timeout. The comparison records per-probe commands, stderr, exit code, timing, raw JSON and field-by-field differences. It separately compares parsed Media records and XML bytes when the application accepts both, checks two audio streams for the multi-track fixture and verifies fixture hashes remain unchanged.

Identical application rejections are reported as baseline limitations, not usable media support. In particular, MKV can omit per-stream duration; both probes may succeed while the current application rejects both. The summary explicitly lists accepted_by_application and baseline_limitations. A probe crash/error, a candidate-only rejection, altered application metadata, changed XML or missing audio fails the comparison. Raw JSON differences outside consumed fields remain visible and need review even if the application comparison passes.

The 35 original tests are then run with the exact stripped candidate renamed ffprobe.exe at the start of PATH; baseline FFmpeg is retained solely for fixture generation. These tests do not certify all formats. No AV1, compressed-header fixture, UNC, long-path or UHD case is covered in this initial corpus; these remain required before switching defaults.

## Read the artifact

Artifact: **Experimental-FFprobe-Windows-evidence**. Upload is restricted to textual report extensions; neither executable, DLL, library archives nor media fixtures are uploaded.

| Evidence | Interpretation |
| --- | --- |
| build-status.txt, configure.log, build.log | Build exit code and failing command diagnostics |
| candidate-size.txt, candidate-sha256.txt | Actual stripped byte size and identity; never estimates |
| candidate-version/buildconf/license.txt | Native executable-reported configuration and licensing |
| toolchain-versions.txt, toolchain-package-hashes.txt | Installed toolchain record, not source completeness |
| ffprobe-link.map, linked-archives.txt, link-symbols.txt | Actual native linker/library evidence |
| pe-imports.txt | Check for non-system runtime DLL dependencies before expecting portability |
| config.h, config_components.h, config.mak, config.log | Actual enabled components and configure tests |
| baseline-source-lock.json, fetch-report.json | Verified baseline/source provenance |
| comparison-summary.json | Per-fixture acceptance/equivalence, raw differences and measured candidate size |
| numbered baseline/candidate/differences/generation JSON | Full diagnostic comparisons and fixture generation failures |
| candidate-original-tests.xml | Existing test runner results on the candidate |

Only conclude a real Windows build after build-status=0 and native version/license/PE outputs exist. Only conclude this corpus passes after comparison_passed=true and original tests pass. Report accepted fixtures separately from identical rejections. No successful build or corpus result alone proves complete licensing or replacement readiness.

## Local checks performed

60 automated tests passed (35 original plus packaging and harness checks). Bash syntax and both workflow YAML files parsed. The harness generated the five media fixtures and compared the SAME system Linux probe against itself: four application-accepted fixtures, and matching MKV duration rejection, no raw differences. This is a harness self-test only, not baseline-vs-candidate validation and not Windows evidence.

## Failure follow-up

If compilation fails, inspect config.log/build.log and retained link map, keep the existing binary and fix the diagnosed prerequisite/flag/source issue on this branch. Missing runtime DLLs in PE imports require resolving static linkage or providing reviewed runtime files; do not hide them with PATH. Corpus regressions require retaining the relevant native support or a justified source-locked dependency; do not weaken application checks. API access is needed here to inspect actual job output; otherwise the owner can supply the textual evidence artifact for diagnosis. Distribution remains blocked throughout.
