"""Fetch hash-locked FFprobe and source evidence; no fallback to latest."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import urllib.request
import zipfile

LOCK_PATH = Path(__file__).resolve().parents[1] / '.github/ffprobe-lock.json'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def download_checked(url, expected, path):
    if not url.startswith('https://') or '/latest/' in url:
        raise ValueError('Exact HTTPS artifact URL required, never latest')
    if not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('Pinned SHA-256 required')
    path = Path(path)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response, path.open('xb') as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
    if sha256(path) != expected:
        raise ValueError(f'Pinned checksum mismatch: {path.name}')


def safe_member(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or re.match(r'^[A-Za-z]:', name):
        raise ValueError('Unsafe ZIP entry')
    return path


def fetch(destination, lock_path=LOCK_PATH):
    lock = json.loads(Path(lock_path).read_text())
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'ffmpeg.zip'
    download_checked(lock['archive_url'], lock['archive_sha256'], archive)
    root = destination / 'tools'
    root.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            path = safe_member(member.filename)
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Symlink in tool archive')
            target = root.joinpath(*path.parts)
            if not target.resolve().is_relative_to(root.resolve()):
                raise ValueError('Extracted path escapes tool directory')
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as reader, target.open('wb') as writer:
                    shutil.copyfileobj(reader, writer, length=1024 * 1024)
    probes = list(root.rglob('ffprobe.exe'))
    encoders = list(root.rglob('ffmpeg.exe'))
    if len(probes) != 1 or len(encoders) != 1 or not all(p.stat().st_size for p in probes + encoders):
        raise ValueError('Exactly one nonempty FFprobe and FFmpeg executable required')
    if sha256(probes[0]) != lock['ffprobe_sha256']:
        raise ValueError('Pinned FFprobe executable checksum mismatch')
    evidence = destination / 'evidence'
    evidence.mkdir(exist_ok=True)
    shutil.copy2(lock_path, evidence / 'ffprobe-lock.json')
    records = []
    for record in lock['source_archives']:
        path = destination / f'{record["component"]}-source.zip'
        download_checked(record['url'], record['sha256'], path)
        target = evidence / path.name
        shutil.copy2(path, target)
        notices = []
        with zipfile.ZipFile(path) as source:
            for member in source.infolist():
                relative = safe_member(member.filename)
                if member.is_dir() or relative.name not in ('LICENSE', 'LICENSE.md', 'COPYING.GPLv3', 'COPYING.GPLv2', 'COPYING.LGPLv3', 'COPYING.LGPLv2.1'):
                    continue
                target = evidence / 'source-notices' / record['component'] / Path(*relative.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(member))
                notices.append(str(target.relative_to(evidence)))
        records.append({**record, 'archive': path.name, 'collected_notices': notices})
    report = {'ffprobe_path': str(probes[0].resolve()), 'ffmpeg_path': str(encoders[0].resolve()),
              'evidence': str(evidence.resolve()), 'binary_sha256_verified': lock['ffprobe_sha256'],
              'source_archives': records, 'source_correspondence_verified': lock['source_correspondence_verified'],
              'unresolved': lock['distribution_blockers']}
    (destination / 'fetch-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (evidence / 'fetch-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    import sys
    fetch(sys.argv[1])
