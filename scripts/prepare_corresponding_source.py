"""Assemble and check a reviewed source bundle; never infer missing sources.

Hashes establish integrity, version checks establish declared correspondence,
not legal completeness or reproducibility of vendor binaries.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import zipfile

def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


REQUIRED = {'qt', 'pyside', 'ffmpeg', 'btbn-build', 'python', 'pyinstaller'}


def safe_path(value):
    if not isinstance(value, str) or '\\' in value or re.match(r'^[A-Za-z]:', value):
        raise ValueError('Archive paths must be relative POSIX paths')
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts or value == '.':
        raise ValueError('Unsafe or empty archive path')
    return path


def validate_manifest(manifest):
    if manifest.get('schema_version') != 1:
        raise ValueError('Expected SOURCE-MANIFEST schema_version 1')
    records = manifest.get('components')
    if not isinstance(records, list) or not records:
        raise ValueError('Component list required')
    ids = [record.get('id') for record in records]
    if len(ids) != len(set(ids)) or not REQUIRED.issubset(ids):
        raise ValueError('Unique component IDs and all required components needed')
    for record in records:
        for key in ('version', 'revision', 'license', 'source_origin', 'build_instructions'):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f'{record.get("id")}: {key} required')
        if record.get('modified') not in (True, False):
            raise ValueError('Explicit modification status required')
        files = record.get('files')
        if not isinstance(files, list) or not files:
            raise ValueError('Source/build file list required for every component')
        for entry in files:
            safe_path(entry.get('path'))
            if not re.fullmatch(r'[a-fA-F0-9]{64}', entry.get('sha256', '')):
                raise ValueError('Every source/build file needs a SHA-256')
        safe_path(record['build_instructions'])
        if record['build_instructions'] not in [entry['path'] for entry in files]:
            raise ValueError('Build instructions must be included and hashed')
    ffmpeg = next(r for r in records if r['id'] == 'ffmpeg')
    linked = ffmpeg.get('statically_linked_components')
    if not isinstance(linked, list) or not linked or not set(linked).issubset(ids):
        raise ValueError('FFprobe static libraries must be individually declared as components')
    recipe = next(r for r in records if r['id'] == 'btbn-build')
    if not re.fullmatch(r'[a-f0-9]{40}', recipe['revision']):
        raise ValueError('Full exact BtbN build-recipe revision required')
    if not re.fullmatch(r'[a-f0-9]{40}', ffmpeg['revision']):
        raise ValueError('Full exact FFmpeg Git revision required')
    return records


def assemble(manifest_path, destination):
    manifest_path, destination = Path(manifest_path), Path(destination)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    records = validate_manifest(manifest)
    root = manifest_path.parent.resolve()
    entries = {}
    for record in records:
        for entry in record['files']:
            name = entry['path']
            if name == 'SOURCE-MANIFEST.json':
                raise ValueError('Reserved manifest path')
            path = (root / Path(*safe_path(name).parts)).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f'Missing or escaping source file: {name}')
            if file_sha256(path) != entry['sha256'].lower():
                raise ValueError(f'Source file checksum mismatch: {name}')
            if name in entries and entries[name] != path:
                raise ValueError('Conflicting source path')
            entries[name] = path
    if destination.resolve() in entries.values():
        raise ValueError('Output would overwrite source')
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        # Fixed metadata and ordering give repeatable ZIPs for the same inputs.
        def write(name, data):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
        write('SOURCE-MANIFEST.json', json.dumps(manifest, sort_keys=True, indent=2).encode('utf-8'))
        for name, path in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with path.open('rb') as source, archive.open(info, 'w', force_zip64=True) as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
    return file_sha256(destination)


def verify(archive_path, evidence):
    evidence = Path(evidence)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate entries in source ZIP')
        for name in names:
            safe_path(name.rstrip('/'))
        manifest = json.loads(archive.read('SOURCE-MANIFEST.json'))
        records = validate_manifest(manifest)
        for record in records:
            for entry in record['files']:
                digest = hashlib.sha256()
                with archive.open(entry['path']) as source:
                    while block := source.read(1024 * 1024):
                        digest.update(block)
                if digest.hexdigest() != entry['sha256'].lower():
                    raise ValueError(f'Source ZIP checksum mismatch: {entry["path"]}')
    by_id = {record['id']: record for record in records}
    qt = json.loads((evidence / 'qt-license-provenance.json').read_text(encoding='utf-8'))
    for component, expected in [('qt', qt['qt_version']), ('pyside', qt['pyside_version'])]:
        if by_id[component]['version'] != expected:
            raise ValueError(f'{component} source version differs from built version')
    packages = {p['name'].lower(): p['version'] for p in json.loads((evidence / 'installed-packages.json').read_text(encoding='utf-8'))}
    if by_id['pyinstaller']['version'] != packages['pyinstaller']:
        raise ValueError('PyInstaller source version mismatch')
    provenance = json.loads((evidence / 'build-provenance.json').read_text(encoding='utf-8'))
    if by_id['python']['version'] != provenance['python_version']:
        raise ValueError('CPython source version mismatch')
    config = (evidence / 'ffprobe-configuration.txt').read_text(encoding='utf-8-sig')
    match = re.search(r'ffprobe version\s+(\S+)', config)
    if not match or by_id['ffmpeg']['version'] != match[1]:
        raise ValueError('FFprobe source version mismatch')
    revision = re.search(r'-g([a-f0-9]+)(?:-|\s|$)', match[1])
    if revision and not by_id['ffmpeg']['revision'].startswith(revision[1]):
        raise ValueError('FFmpeg source revision differs from FFprobe build')
    if '--enable-nonfree' in config:
        raise ValueError('Nonfree FFprobe redistribution unresolved')
    for source in qt['sources']:
        component = by_id['pyside' if source['component'] == 'pyside-setup' else 'qt']
        commits = component.get('module_revisions', {})
        if commits.get(source['component']) != source['revision']:
            raise ValueError('Qt/PySide module revision differs from source evidence')
    report = {'verified': 'Declared versions, source-file hashes and module revisions',
              'component_ids': sorted(by_id),
              'unverified': ['Static library list completeness', 'Vendor patches and toolchain equivalence',
                             'Actual binary/source reproducibility', 'Legal completeness of notices and sources']}
    (evidence / 'source-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    create = sub.add_parser('assemble')
    create.add_argument('manifest', type=Path)
    create.add_argument('output', type=Path)
    check = sub.add_parser('verify')
    check.add_argument('archive', type=Path)
    check.add_argument('evidence', type=Path)
    args = parser.parse_args()
    if args.mode == 'assemble':
        print(assemble(args.manifest, args.output))
    else:
        verify(args.archive, args.evidence)
