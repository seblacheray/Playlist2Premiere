#!/usr/bin/env bash
# Experimental only. Native demuxers/decoders/parsers remain enabled.
set -euo pipefail
source_dir=$(cygpath -u "$1")
build_dir=$(cygpath -u "$2")
report_dir=$(cygpath -u "$3")
mkdir -p "$build_dir" "$report_dir"
source_dir=$(cd "$source_dir" && pwd)
build_dir=$(cd "$build_dir" && pwd)
report_dir=$(cd "$report_dir" && pwd)
trap 'status=$?; printf "build_exit_code=%s\n" "$status" > "$report_dir/build-status.txt"; for f in config.h config_components.h ffbuild/config.log ffbuild/config.mak ffprobe-link.map; do if [[ -f "$build_dir/$f" ]]; then cp "$build_dir/$f" "$report_dir/$(basename "$f")"; fi; done' EXIT
{
    uname -a
    gcc --version
    ld --version
    make --version
    pacman -Q
} > "$report_dir/toolchain-versions.txt"
find /var/cache/pacman/pkg -maxdepth 1 -type f -name '*.pkg.tar.*' -print0 | sort -z | xargs -0 -r sha256sum > "$report_dir/toolchain-package-hashes.txt"
cp "$0" "$report_dir/build-recipe.txt"
# ZIP extraction on Windows may not preserve Unix executable bits.
find "$source_dir/ffbuild" -type f -name '*.sh' -exec chmod +x {} +
cd "$build_dir"
flags=(
    --arch=x86_64 --target-os=mingw32
    --disable-autodetect --disable-iconv
    --disable-doc --disable-debug
    --disable-programs --enable-ffprobe
    --disable-avdevice --disable-avfilter
    --disable-encoders --disable-muxers
    --disable-network --disable-hwaccels
    --disable-pthreads --enable-w32threads
    --enable-static --disable-shared
    --enable-gpl --enable-version3
    --enable-zlib --pkg-config-flags=--static
    --disable-x86asm
    --extra-version=playlist2premiere-615b07170e
    '--extra-ldflags=-static -static-libgcc -static-libstdc++ -Wl,-Map=ffprobe-link.map'
)
printf '%q ' "$source_dir/configure" "${flags[@]}" > "$report_dir/configure-command.txt"
printf '\n' >> "$report_dir/configure-command.txt"
bash "$source_dir/configure" "${flags[@]}" 2>&1 | tee "$report_dir/configure.log"
make -j2 V=1 ffprobe.exe 2>&1 | tee "$report_dir/build.log"
sha256sum ffprobe.exe > "$report_dir/candidate-unstripped-sha256.txt"
cp ffprobe.exe ffprobe-candidate.exe
strip --strip-unneeded ffprobe-candidate.exe
sha256sum ffprobe-candidate.exe > "$report_dir/candidate-sha256.txt"
wc -c ffprobe-candidate.exe > "$report_dir/candidate-size.txt"
grep '^LOAD ' ffprobe-link.map > "$report_dir/linked-archives.txt" || true
objdump -p ffprobe-candidate.exe > "$report_dir/pe-imports.txt"
nm -g ffprobe.exe > "$report_dir/link-symbols.txt"
./ffprobe-candidate.exe -version > "$report_dir/candidate-version.txt" 2>&1
./ffprobe-candidate.exe -buildconf > "$report_dir/candidate-buildconf.txt" 2>&1
./ffprobe-candidate.exe -L > "$report_dir/candidate-license.txt" 2>&1
./ffprobe-candidate.exe -decoders > "$report_dir/candidate-decoders.txt" 2>&1
./ffprobe-candidate.exe -demuxers > "$report_dir/candidate-demuxers.txt" 2>&1
./ffprobe-candidate.exe -protocols > "$report_dir/candidate-protocols.txt" 2>&1
