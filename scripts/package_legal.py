"""Collect legal review evidence. Does not certify license compliance."""
from importlib import metadata
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys


FFPROBE_LOCK_PATH = Path(__file__).resolve().parents[1] / '.github/ffprobe-lock.json'


def verify_embedded_ffprobe(executable, destination):
    from PyInstaller.archive.readers import CArchiveReader
    lock = json.loads(FFPROBE_LOCK_PATH.read_text())
    archive = CArchiveReader(str(executable))
    names = [name for name in archive.toc if Path(name.replace('\\', '/')).name.lower() == 'ffprobe.exe']
    if len(names) != 1:
        raise RuntimeError('Exactly one embedded FFprobe executable required')
    digest = hashlib.sha256(archive.extract(names[0])).hexdigest()
    if digest != lock['ffprobe_sha256']:
        raise RuntimeError('Embedded FFprobe differs from pinned binary')
    (Path(destination) / 'embedded-ffprobe-verification.json').write_text(json.dumps({
        'entry': names[0], 'sha256': digest, 'version_locked': lock['ffprobe_version'],
        'method': 'Extract bytes from final PyInstaller CArchive and compare SHA-256'}, indent=2), encoding='utf-8')


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('LICENSE', 'THIRD-PARTY.md', 'docs/license-compliance.md'):
        shutil.copy2(name, destination / Path(name).name)
    shutil.copytree('licenses', destination / 'project-third-party-license-texts', dirs_exist_ok=True)
    python_license = next((path for path in (Path(sys.base_prefix) / 'LICENSE.txt', Path(sys.base_prefix) / 'LICENSE') if path.is_file()), None)
    if python_license is None:
        raise RuntimeError('CPython license text missing from installation; provide it before packaging')
    shutil.copy2(python_license, destination / 'CPython-LICENSE.txt')
    packages = []
    for distribution in metadata.distributions():
        name = distribution.metadata['Name']
        record = {'name': name, 'version': distribution.version,
                  'license': distribution.metadata.get('License-Expression') or distribution.metadata.get('License'),
                  'collected_notices': []}
        for entry in distribution.files or []:
            path = Path(str(entry))
            if any(word in path.name.lower() for word in ('license', 'copying', 'copyright', 'notice')):
                source = distribution.locate_file(entry)
                if not source.is_file():
                    continue
                # Avoid wheel-relative traversal and preserve distinct vendor texts.
                safe = [part for part in path.parts if part not in ('.', '..', '/', '\\')]
                target = destination / 'vendor-licenses' / name / Path(*safe)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                record['collected_notices'].append(str(target.relative_to(destination)))
        packages.append(record)
    (destination / 'installed-packages.json').write_text(json.dumps(packages, indent=2), encoding='utf-8')
    with (destination / 'frozen-inventory.txt').open('w', encoding='utf-8') as handle:
        subprocess.run([sys.executable, '-m', 'PyInstaller.utils.cliutils.archive_viewer', '-l', '-r', 'dist/Playlist2Premiere.exe'], stdout=handle, stderr=subprocess.STDOUT, check=True)
    verify_embedded_ffprobe('dist/Playlist2Premiere.exe', destination)
    from collect_qt_legal import collect
    collect(destination)
    subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(destination / 'project-source.zip'), 'HEAD'], check=True)
    exe = Path('dist/Playlist2Premiere.exe')
    (destination / 'build-provenance.json').write_text(json.dumps({
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version, 'python_version': '.'.join(map(str, sys.version_info[:3])), 'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
        'inventory_scope': 'Installed packages are a superset; inspect frozen-inventory.txt for shipped contents',
        'compliance_status': 'Requires owner verification of notices and corresponding sources'}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
