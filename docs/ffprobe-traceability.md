# Pinned FFprobe evidence and unresolved corresponding sources

## Independently verified choice for new builds

Release: `autobuild-2026-10-12-13-12` (BtbN/FFmpeg-Builds).

Archive URL:
https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-12-13-12/ffmpeg-N-127388-g615b07170e-win64-gpl.zip

- Archive SHA-256: `b79906cf805b8a43e7bc061715acddb4a48ac6534a9e30768217e546104b8bee`
- FFprobe executable SHA-256: `4139072494710643369eb06a41e43df3113e7c921182d69a261ec48fac0d98be`
- Embedded version string: `N-127388-g615b07170e-20261012`
- Full FFmpeg revision resolved from upstream commit: `615b07170e30d79ad5906418ea49f81c3cbd8457`
- BtbN release-tag target, fetched through Git: `63ac3265b0789ea16c7b1f8351cd2ad195a28722`
- FFmpeg source archive SHA-256: `bd699597c7403864b689dc703a63f595f02b0061c53ab3249f0f7a31dbbe2f43`
- BtbN recipe source archive SHA-256: `4af54438fa804f6122f46738e525f086b700897e553baa765be8a2abe07199b4`

The dated archive and both immutable-commit source archives were actually downloaded and hashed. The archive digest also matched the release's checksums.sha256. FFprobe bytes were extracted from the ZIP and hashed; embedded printable version/configuration strings were inspected, not executed on Linux. Configuration includes --enable-gpl, --enable-version3, --pkg-config-flags=--static and lacks --enable-nonfree. Full configuration and hashes are in `.github/ffprobe-lock.json`. Windows CI additionally executes that binary and compares its reported version/configuration.

This dated ZIP is NOT claimed identical to the historical `latest` ZIP with SHA-256 `4480b1abcae8bb46146e271fe603efaa90f29671ff9013bb0aed2d64d12951c8`. Version-name equality is insufficient to establish identity. No historical artifact was substituted.

A dated GitHub release can be removed or replaced by its publisher. A pinned hash prevents accepting replacement bytes; there is no fallback. BtbN documents 14-day retention of ordinary daily releases, versus two-year retention of the last build of a month. This October 12 asset is therefore not guaranteed to remain available indefinitely. Preserve the verified archive and evidence in owner-controlled storage before expiry, keeping the hash and reviewing licensing before redistribution; alternatively audit/pin an available retained monthly asset in a separate update. No Release was published here.

## What the BtbN recipe establishes — and what it does not

The exact tag target contains build.sh, makeimage.sh, images, scripts.d, patches, variants and addins. Its GPL variant selects COPYING.GPLv3. BtbN's recipe itself is MIT licensed; its original copyright/license is preserved in downloaded source notices. The FFmpeg source provides LICENSE.md and GPL/LGPL texts, plus original source-header attributions. This evidence supports GPL v3 for the aggregate FFprobe build, not GPL relicensing of every component.

`docs/ffprobe-recipe-candidates.json` records 81 recipe files, their exact SHA-256 and SCRIPT_REPO/SCRIPT_COMMIT declarations where present. Example: x264 recipe declares revision `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`. This is a recipe declaration, NOT proof that this exact revision was linked into FFprobe. The recipe set is a superset, includes disabled components and non-source stages, and is not a static link map.

Configuration advertises external libraries including dav1d, aom, x264/x265, vorbis, opus, libxml2, zlib, iconv, libass, libbluray, libjxl, libssh, libcurl, freetype, harfbuzz, gmp, lzma and many others. Configuration switches establish enabled features, not an exhaustive list of objects actually linked into FFprobe. Transitive dependencies (including Rust crates, font/graphics libraries and MinGW/libgcc/libstdc++ runtimes where linked) require their own investigation. Some runtime integrations can be dynamic rather than static; do not label every advertised feature a statically distributed library.

Missing evidence:

1. Actual FFprobe link command/map, component version inventory and all transitive native dependency inputs.
2. Digest/provenance of the exact BtbN Docker build images and cache entries used by the release build. The source tag is not proof of image contents; build.sh uses image-derived dependencies and clones a branch for FFmpeg.
3. Exact revisions/tarball hashes, submodules, applied patches and Cargo inputs for each library actually linked.
4. Full applicable licenses/attributions and sources for those exact inputs, not merely generic project license labels.

No unavailable revision, license choice, tarball digest or static-library membership is invented. These gaps mean corresponding-source completeness is NOT established. The checked-in lock has `source_correspondence_verified: false`; portable distribution is blocked even when a source ZIP and owner-review flag are supplied. Remove that blocker only in a reviewed change with actual provenance evidence, never just to make CI pass.

## Reproducible collection and next actions

`python scripts/fetch_ffprobe.py <new-output-directory>` downloads only the hash-locked archive and the two hash-locked source archives. It checks safe extraction, exactly one nonempty FFprobe/FFmpeg, binary identity and license/source evidence. It refuses latest or checksum substitutions. It retains sources and original copyright/license files under evidence. These are INPUTS, not a complete corresponding-source bundle.

The workflow checks native version/configuration, then verifies the bytes of ffprobe.exe extracted from the FINAL PyInstaller executable against the pinned SHA-256. This links the locked binary to the shipped container; it does not prove that sources reproduce that binary. Review source extraction, compilation and linkage separately.

Follow corresponding-sources.md after acquiring the missing inputs. The ffmpeg manifest record must declare `binary_sha256`, exact version/full revision and every relevant static library component; the btbn-build revision must match the reviewed release tag. Both pinned source archives must be included verbatim with their measured hashes. A source manifest differing from the build's checked-in lock is rejected.

Preferred resolution: request the release's exact build/cache provenance, source inputs and link map from the supplier. If unobtainable, do not claim this prebuilt binary compliant. Prepare a separately reviewed minimal FFprobe build from pinned FFmpeg sources, with --disable-autodetect, no unnecessary external libraries, explicit codec/demuxer requirements, immutable toolchain inputs and captured configuration/link maps/source bundle. Validate media coverage before switching builds; no such functionality change is made in this PR.
