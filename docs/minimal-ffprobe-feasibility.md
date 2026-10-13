# Own Windows x64 FFprobe: feasibility before replacement

## Decision for this change

Technically feasible, but NOT sufficiently validated to replace the current embedded binary. Only documentation changes are made. The pinned BtbN binary, its SHA-256 checks, packaging and distribution block remain unchanged. No new executable or native Windows inventory is claimed. No Release is published.

## Actual application needs

`src/playlist2premiere/probe.py` invokes exactly:

```
ffprobe -v error -show_streams -show_format -of json <absolute-local-file>
```

It uses a 120-second timeout, no shell, and reads stream types/indexes, duration_ts/time_base (or stream duration), start_time, avg_frame_rate/r_frame_rate, width/height, audio channels/sample_rate, disposition, sample aspect ratio, field order and rotation side data. It requires usable video timing and checks audio timing, not just container duration. It neither transcodes, renders filters nor requests show_frames/count_frames. Nevertheless FFprobe uses avformat_find_stream_info and can open decoders to determine stream characteristics; removing every decoder is unsafe.

Playlist extensions PLS/MPCPL do not constrain media container/codec extensions. The resolver accepts existing local files, including Windows drive paths, accents and UNC shares. Network FFmpeg protocols are not needed for those file paths; disabling network protocols must not be confused with disabling Windows filesystem access to SMB shares. Explicit remote URLs are already rejected by the resolver.

Confirmed media tests are H.264 MP4 with and without AAC audio, integer/fractional rates and mixed resolutions. The existing automated real-media integration is mainly H.264/AAC MP4. It does not establish support for all common codecs/containers. Existing application restrictions (CFR, required stream durations, square pixels, no rotation/interlacing) must remain unchanged; missing metadata that the old binary also cannot provide is an existing limitation, not necessarily a new build regression.

## Candidate strategy: minimize tasks, not a guessed format whitelist

Keep all available native demuxers, parsers, decoders and bitstream filters. Do NOT use --disable-everything or limit demuxers/decoders to MOV/H.264. Remove command-line ffmpeg/ffplay, encoding/muxing, input/output devices, filters and hardware accelerators not needed by probing. Keep avformat/avcodec/avutil and conservatively keep swscale/swresample if required by native components. Prefer Win32 threads on Windows to avoid a winpthreads dependency, subject to build verification.

A no-external-library feasibility profile, exercised at configure time on Linux, is:

```sh
./configure \
  --disable-autodetect --disable-iconv \
  --disable-doc --disable-debug \
  --disable-programs --enable-ffprobe \
  --disable-avdevice --disable-avfilter \
  --disable-encoders --disable-muxers \
  --disable-network --disable-hwaccels \
  --enable-static --disable-shared \
  --enable-gpl --enable-version3 \
  --disable-x86asm
```

This is a CONFIGURE-ONLY diagnostic profile, not a Windows build recipe or a validated replacement. --disable-x86asm avoids requiring NASM for the local diagnostic; a production choice must benchmark probing time, especially UHD media, against the 120-second timeout. Explicit --disable-iconv matters: the initial configure check still found libc-provided iconv despite --disable-autodetect. Autodetect control alone does not prove zero external/system dependencies.

Source revision used: 615b07170e30d79ad5906418ea49f81c3cbd8457, matching the pinned FFprobe FFmpeg revision. The verified source archive hash is bd699597c7403864b689dc703a63f595f02b0061c53ab3249f0f7a31dbbe2f43. This avoids mixing a source upgrade with the build change.

## Coverage risks requiring decisions backed by tests

| Need | Native conservative profile | Additional validation / possible dependency |
| --- | --- | --- |
| MP4/MOV, H.264, HEVC, AAC/PCM | Native components remain enabled | Compare exact stream metadata, fractional rates, multitrack audio and durations against pinned baseline |
| AVI/MXF/MPEG-TS/MPEG-PS, ProRes, DNxHD/DNxHR, MPEG-2/4, MJPEG | Keep native demuxers/decoders | Genuine or generated representative fixtures; metadata equivalence rather than assumed support |
| MKV/WebM, VP8/VP9, Vorbis/Opus | Native components remain enabled | Matroska compression variants and stream-duration limitations |
| Compressed MOV headers / Matroska content encodings | zlib/bzip2 omitted in diagnostic profile | A small pinned zlib/bzip2 source set may be necessary to preserve baseline support |
| Compressed image/intraframe formats | Some native decoders require zlib/lzma | Screen codecs, PNG/EXR/TIFF and production media must be assessed before any exclusion |
| AV1 | Native AV1 path exists, but source reports hardware-assisted decoding requirements | Test the actual probing command on AV1 MP4/MKV/elementary media; a pinned dav1d may be needed for reliable software probing |
| JPEG XL and specialized codecs | External-library-backed support may disappear | Identify actual needs; retain a source-locked dependency or record an explicitly reviewed limitation, never silently drop support |
| Accented/long paths and UNC | Windows file API support is distinct from iconv/network protocols | Real native Windows tests; Linux cannot confirm Windows path handling |

The zero-external profile is therefore not automatically acceptable. The recommended production direction is a native-codec profile plus a *small, justified and source-locked* dependency set, not deletion of every external library. At least zlib and possibly bzip2/lzma/dav1d require investigation. No revision, license, hash or necessity for these candidate dependencies is invented here.

## GitHub Actions Windows feasibility and reproducibility

FFmpeg's pinned platform documentation supports native MinGW-w64/MSYS2 and MSVC builds. A windows-2022 job can compile FFprobe with MSYS2 UCRT64 or a tested MSVC environment. The exact toolchain, package archives, hashes, headers, binutils and build utilities must be locked before claiming reproducibility; installing MSYS2's current packages is not sufficient. Native Win32 threading can avoid pthread DLLs, but actual PE imports must verify it.

A candidate job should be SEPARATE from the existing validated package job and upload only review evidence. Capture configure flags, config.h/config_components.h, config.log, full make V=1 output, compiler versions, link commands/maps, PE import list, unstripped/stripped hashes, build manifest and corresponding-source inputs. Keep old FFprobe available for the same media corpus. Supply the candidate through probe(path, executable=...) in a test harness; do not alter find_ffprobe or normal packaging until comparison succeeds.

Source reproducibility and byte-for-byte reproducibility are different. Pin inputs and dependency sources; control timestamps/SOURCE_DATE_EPOCH and archive ordering; build twice with the same inputs and compare hashes. Windows PE timestamps, toolchain paths and archives can still require normalization. Never disable signature/checksum/TLS validation. No successful Windows compile, executable run, link-map inspection or double-build comparison was possible here: MinGW cross compiler, native Windows/MSYS2/MSVC, Wine and PowerShell are unavailable in this Linux environment.

Current pinned FFprobe is 168719872 bytes (about 161 MiB, measured). A build removing large external libraries should be substantially smaller; tens of MiB is a planning estimate, NOT a measured size or guarantee. Native decoder breadth, optimization, assembly and retained dependencies determine size. The final onefile application's size also includes Python/Qt and must be measured separately.

## Validation required before replacement

1. Produce a candidate Windows executable without changing the embedded default; verify its version, configuration, codecs/demuxers, PE imports and FFmpeg revision.
2. Run the 35 original tests with the candidate on PATH, retaining FFmpeg solely for fixture generation. Existing tests alone are insufficient.
3. Run both binaries with the application's exact command on a corpus covering the table above, multistream audio, 25/24000/1001/30000/1001 rates, UHD media, Unicode/special/long Windows paths and UNC. Compare parsed Media records and expected errors; separately investigate differences rather than weaken assertions.
4. Identify compressed-header and external-codec coverage with real fixtures. Ensure deliberate unsupported formats do not silently produce fabricated metadata.
5. Compile twice, compare hashes, verify source lock/link map completeness, then build a separate candidate portable exe and exercise both Windows/offscreen GUI/dialogs, embedded probe and XML exports. Real Premiere/Resolve import remains a user acceptance check.
6. Only after these pass, prepare an explicit change to replace the locked FFprobe. Keep a rollback baseline; do not switch automatically on compilation success.

## License and corresponding sources

A source-locked own GPL build avoids the unknown BtbN cache/static-input set but not licensing obligations. Include the exact FFmpeg source/license/copyrights, local patches and build scripts; every required static dependency's exact source/license/notices; and toolchain/runtime licensing records. FFmpeg's configured license depends on selected components: the native configure check reports GPL version 3 or later with the shown GPL flags. Verify the actual Windows result. Do not confuse MSYS shell licensing with linking MSYS runtime into a Windows executable. MinGW CRT/runtime/GCC support libraries require their actual licenses/exceptions and appropriate source-obligation analysis; system libraries must not be assumed to cover arbitrary shipped runtime DLLs. CPython/Qt obligations remain independent.

Do not set source_correspondence_verified to true until actual candidate evidence establishes source linkage, transitives and notices. The existing BtbN lock and distribution gate remain false/blocked. The viable solution is to obtain a pinned Windows toolchain and test corpus, then build and inspect a separate candidate. This change intentionally stops at feasibility because replacement reliability and coverage cannot currently be demonstrated.
