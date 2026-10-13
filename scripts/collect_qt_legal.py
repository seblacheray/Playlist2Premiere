"""Fetch version-matched Qt/PySide source archives and preserve legal material.

Sources and license labels are evidence, not proof of binary/source equivalence.
Immutable Git commits are resolved from version tags before downloading.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.request
import zipfile
from importlib import metadata

QTBASE_MODULES = {'Core', 'Gui', 'Widgets', 'Network', 'OpenGL', 'OpenGLWidgets',
                  'PrintSupport', 'DBus', 'Sql', 'Concurrent', 'Xml', 'Test'}
FORBIDDEN_MODULES = {'Pdf', 'PdfWidgets', 'VirtualKeyboard'}


def qt_modules(inventory):
    return sorted(set(re.findall(r'Qt6([A-Za-z0-9]+)\.dll\b', inventory, re.I)))


def repositories_for_modules(modules):
    repos = {'qtbase'}
    for module in modules:
        if module in FORBIDDEN_MODULES:
            raise ValueError(f'Unexpected unused Qt module still bundled: {module}')
        if module in QTBASE_MODULES:
            continue
        # Binding DLLs can retain QML/Quick as link-time dependencies even when
        # no corresponding Python API is imported. Do not delete required DLLs.
        if module.startswith(('Qml', 'Quick')):
            repos.add('qtdeclarative')
        elif module in ('Svg', 'SvgWidgets'):
            repos.add('qtsvg')
        else:
            raise ValueError(f'Qt module {module} requires an explicit source/license mapping')
    return sorted(repos)


def resolve_tag(repo, version):
    tag = f'refs/tags/v{version}'
    output = subprocess.check_output(['git', 'ls-remote', f'https://github.com/{repo}.git', tag, tag + '^{}'], text=True)
    refs = dict(line.split()[::-1] for line in output.splitlines())
    revision = refs.get(tag + '^{}', refs.get(tag))
    if not revision or not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError(f'Cannot resolve exact source tag {repo} v{version}')
    return revision


def legal_member(name):
    path = PurePosixPath(name)
    base = path.name.lower()
    return ('LICENSES' in path.parts or base == 'qt_attribution.json' or
            any(word in base for word in ('license', 'copying', 'copyright', 'notice', 'authors')))


def collect(destination):
    from PySide6.QtCore import qVersion
    destination = Path(destination)
    inventory = (destination / 'frozen-inventory.txt').read_text(encoding='utf-8')
    modules = qt_modules(inventory)
    if not {'Core', 'Gui', 'Widgets'}.issubset(modules):
        raise ValueError('Windows frozen inventory must contain Qt Core/Gui/Widgets')
    qt_version = qVersion()
    pyside_version = metadata.version('PySide6')
    if metadata.version('shiboken6') != pyside_version:
        raise ValueError('PySide6 and Shiboken versions must match for this source mapping')
    licenses = metadata.metadata('PySide6').get('License', '')
    if 'GPL-3.0-only' not in licenses:
        raise ValueError('GPL v3 option not confirmed by installed PySide6 metadata')
    sources = [(f'qt/{repo}', qt_version) for repo in repositories_for_modules(modules)]
    sources.append(('pyside/pyside-setup', pyside_version))
    records = []
    for repo, version in sources:
        revision = resolve_tag(repo, version)
        url = f'https://codeload.github.com/{repo}/zip/{revision}'
        name = repo.split('/')[-1]
        archive = destination / 'qt-source-evidence' / f'{name}-{revision}.zip'
        archive.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with urllib.request.urlopen(url, timeout=120) as response, archive.open('wb') as target:
            while block := response.read(1024 * 1024):
                digest.update(block)
                target.write(block)
        notices = []
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                path = PurePosixPath(member.filename)
                if member.is_dir() or not legal_member(member.filename):
                    continue
                if path.is_absolute() or '..' in path.parts or '\\' in member.filename:
                    raise ValueError('Unsafe source archive path')
                target = destination / 'qt-open-source-notices' / name / Path(*path.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(member))
                notices.append(str(target.relative_to(destination)))
        required = destination / 'qt-open-source-notices' / name / 'LICENSES' / 'GPL-3.0-only.txt'
        if not required.is_file():
            raise ValueError(f'Open-source GPL text missing for {repo}')
        records.append({'component': name, 'version': version, 'revision': revision,
                        'source_url': url, 'archive': str(archive.relative_to(destination)),
                        'sha256': digest.hexdigest(), 'notices': notices})
    report = {'qt_version': qt_version, 'pyside_version': pyside_version,
              'shiboken_version': metadata.version('shiboken6'), 'frozen_qt_modules': modules,
              'retained_qml_quick_dependencies': [m for m in modules if m.startswith(('Qml', 'Quick'))],
              'selected_pyside_license': 'GPL-3.0-only', 'sources': records,
              'limits': ['Tag-matched source is not proof of vendor wheel build equivalence.',
                         'Vendor patches, wheel toolchains and native third-party libraries need review.',
                         'All license alternatives are retained; commercial text is not the selected license.',
                         'Qt attribution JSON and source license notices require human review.',
                         'Repository archives do not include Git submodule contents.']}
    (destination / 'qt-license-provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (destination / 'QT-LICENSING.txt').write_text(
        'PySide6/Shiboken: GPL-3.0-only option selected. Qt: open-source GPL-compatible route; '
        'retain all module-specific terms and third-party notices. LicenseRef-Qt-Commercial '
        'is an unused alternative and is NOT proof of GPL compliance. See qt-license-provenance.json '
        'and qt-open-source-notices. Correspondence of sources to vendor wheels remains subject '
        'to review. Source headers and full attributions are preserved in qt-source-evidence archives.\n', encoding='utf-8')


if __name__ == '__main__':
    import sys
    collect(sys.argv[1])
