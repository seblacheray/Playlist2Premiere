from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import zipfile
import pytest

SCRIPTS = Path(__file__).parents[1] / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qt = load('collect_qt_legal')
sources = load('prepare_corresponding_source')


def test_inventory_mapping_uses_frozen_dlls():
    modules = qt.qt_modules("(0, 'PySide6/Qt6Widgets.dll')\n(0, 'Qt6Core.dll')\nQt6Gui.dll\nQt6Svg.dll")
    assert modules == ['Core', 'Gui', 'Svg', 'Widgets']
    assert qt.repositories_for_modules(modules) == ['qtbase', 'qtsvg']
    assert qt.qt_modules('PySide6_Addons installed, no DLL present') == []
    assert qt.repositories_for_modules(['Core', 'Gui', 'Widgets', 'Qml', 'Quick']) == ['qtbase', 'qtdeclarative']


@pytest.mark.parametrize('module', ['Pdf', 'VirtualKeyboard', 'Unknown'])
def test_unexpected_qt_modules_block_packaging(module):
    with pytest.raises(ValueError):
        qt.repositories_for_modules(['Core', 'Gui', 'Widgets', module])


def test_plugin_hook_filters_only_unused_plugins(monkeypatch):
    collector = types.ModuleType('PyInstaller.utils.hooks.qt')
    plugins = [('qpdf.dll', 'imageformats'), ('qvirtualkeyboard.dll', 'platforminputcontexts'),
               ('qwindows.dll', 'platforms'), ('qoffscreen.dll', 'platforms'), ('qsvg.dll', 'imageformats'),
               ('Qt6Gui.dll', '.'), ('qjpeg.dll', 'imageformats')]
    collector.add_qt6_dependencies = lambda path: ([], plugins, [('data', '.')])
    monkeypatch.setitem(sys.modules, 'PyInstaller.utils.hooks.qt', collector)
    spec = importlib.util.spec_from_file_location('qtgui_hook', SCRIPTS / 'pyinstaller_hooks/hook-PySide6.QtGui.py')
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    assert hook.binaries == plugins[2:]
    assert hook.datas == [('data', '.')]


def manifest_fixture(tmp_path):
    file = tmp_path / 'build.txt'
    file.write_text('Fixture build instructions, NOT real corresponding sources')
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    components = []
    for name in sorted(sources.REQUIRED | {'libexample'}):
        components.append({'id': name, 'version': '1', 'revision': 'a' * 40,
                           'license': 'GPL-3.0-only', 'source_origin': 'https://example.invalid/source',
                           'modified': False, 'build_instructions': 'build.txt',
                           'files': [{'path': 'build.txt', 'sha256': digest}]})
    next(c for c in components if c['id'] == 'ffmpeg')['statically_linked_components'] = ['libexample']
    return {'schema_version': 1, 'components': components}


def test_assembly_is_reproducible_and_contains_manifest(tmp_path):
    manifest = tmp_path / 'SOURCE-MANIFEST.json'
    manifest.write_text(json.dumps(manifest_fixture(tmp_path)))
    first, second = tmp_path / 'one.zip', tmp_path / 'two.zip'
    assert sources.assemble(manifest, first) == sources.assemble(manifest, second)
    with zipfile.ZipFile(first) as archive:
        assert set(archive.namelist()) == {'SOURCE-MANIFEST.json', 'build.txt'}
    with pytest.raises(FileExistsError):
        sources.assemble(manifest, first)


@pytest.mark.parametrize('change', ['checksum', 'missing_component', 'traversal', 'missing_static_libraries', 'missing_build_recipe'])
def test_incomplete_or_unsafe_sources_rejected(tmp_path, change):
    manifest = manifest_fixture(tmp_path)
    if change == 'checksum':
        manifest['components'][0]['files'][0]['sha256'] = '0' * 64
    elif change == 'missing_component':
        manifest['components'] = [c for c in manifest['components'] if c['id'] != 'qt']
    elif change == 'traversal':
        manifest['components'][0]['files'][0]['path'] = '../outside'
    elif change == 'missing_static_libraries':
        next(c for c in manifest['components'] if c['id'] == 'ffmpeg')['statically_linked_components'] = []
    else:
        manifest['components'][0]['build_instructions'] = 'not-included.txt'
    path = tmp_path / 'SOURCE-MANIFEST.json'
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        sources.assemble(path, tmp_path / 'out.zip')


def test_source_version_and_revision_verification(tmp_path, monkeypatch):
    manifest = manifest_fixture(tmp_path)
    by_id = {record['id']: record for record in manifest['components']}
    by_id['ffmpeg']['version'] = 'N-1-gaaaaaaaaaa-20261012'
    by_id['qt']['module_revisions'] = {'qtbase': 'b' * 40}
    by_id['pyside']['module_revisions'] = {'pyside-setup': 'c' * 40}
    (tmp_path / 'SOURCE-MANIFEST.json').write_text(json.dumps(manifest))
    archive = tmp_path / 'source.zip'
    sources.assemble(tmp_path / 'SOURCE-MANIFEST.json', archive)
    (tmp_path / 'qt-license-provenance.json').write_text(json.dumps({'qt_version': '1', 'pyside_version': '1', 'sources': [{'component': 'qtbase', 'revision': 'b' * 40}, {'component': 'pyside-setup', 'revision': 'c' * 40}]}))
    (tmp_path / 'installed-packages.json').write_text(json.dumps([{'name': 'pyinstaller', 'version': '1'}]))
    (tmp_path / 'build-provenance.json').write_text(json.dumps({'python_version': '1'}))
    (tmp_path / 'ffprobe-configuration.txt').write_text('ffprobe version N-1-gaaaaaaaaaa-20261012\nconfiguration: --enable-gpl --enable-version3')
    pinned = tmp_path / 'ffprobe-pinned'
    pinned.mkdir()
    lock = {'ffmpeg_revision': 'a' * 40, 'btbn_release_tag_revision': 'a' * 40,
            'ffprobe_sha256': 'd' * 64, 'source_correspondence_verified': True, 'source_archives': []}
    by_id['ffmpeg']['binary_sha256'] = 'd' * 64
    (tmp_path / 'SOURCE-MANIFEST.json').write_text(json.dumps(manifest))
    archive.unlink()
    sources.assemble(tmp_path / 'SOURCE-MANIFEST.json', archive)
    (pinned / 'ffprobe-lock.json').write_text(json.dumps(lock))
    monkeypatch.setattr(sources, 'FFPROBE_LOCK_PATH', pinned / 'ffprobe-lock.json')
    sources.verify(archive, tmp_path)
    lock['source_correspondence_verified'] = False
    (pinned / 'ffprobe-lock.json').write_text(json.dumps(lock))
    with pytest.raises(ValueError, match='distribution blocked'):
        sources.verify(archive, tmp_path)
    assert (tmp_path / 'source-verification.json').is_file()
    (tmp_path / 'ffprobe-configuration.txt').write_text('ffprobe version N-1-gbbbbbbbbbb-20261012')
    with pytest.raises(ValueError, match='version mismatch'):
        sources.verify(archive, tmp_path)


@pytest.mark.parametrize('gpl_available', [True, False])
def test_qt_collector_requires_open_source_texts(tmp_path, monkeypatch, gpl_available):
    import io
    (tmp_path / 'frozen-inventory.txt').write_text('Qt6Core.dll Qt6Gui.dll Qt6Widgets.dll')
    monkeypatch.setattr(qt, 'resolve_tag', lambda repo, version: 'a' * 40)
    def download(url, timeout):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('source/LICENSES/LicenseRef-Qt-Commercial.txt', 'Unused commercial alternative')
            if gpl_available:
                archive.writestr('source/LICENSES/GPL-3.0-only.txt', 'GPL fixture text')
                archive.writestr('source/src/3rdparty/qt_attribution.json', '{"copyright": "Upstream authors"}')
                archive.writestr('source/src/3rdparty/LICENSE', 'Upstream terms')
        data.seek(0)
        return data
    monkeypatch.setattr(qt.urllib.request, 'urlopen', download)
    if not gpl_available:
        with pytest.raises(ValueError, match='GPL text missing'):
            qt.collect(tmp_path)
    else:
        qt.collect(tmp_path)
        report = json.loads((tmp_path / 'qt-license-provenance.json').read_text())
        assert report['selected_pyside_license'] == 'GPL-3.0-only'
        assert all(any('GPL-3.0-only.txt' in path for path in entry['notices']) for entry in report['sources'])
        assert any('qt_attribution.json' in path for path in report['sources'][0]['notices'])
        assert (tmp_path / 'QT-LICENSING.txt').is_file()


def test_ffprobe_lock_is_pinned_and_still_blocks_distribution():
    lock = json.loads((SCRIPTS.parent / '.github/ffprobe-lock.json').read_text())
    assert '/latest/' not in lock['archive_url']
    assert lock['release_tag'] in lock['archive_url']
    assert len(lock['archive_sha256']) == len(lock['ffprobe_sha256']) == 64
    assert len(lock['ffmpeg_revision']) == len(lock['btbn_release_tag_revision']) == 40
    assert '--enable-gpl' in lock['ffprobe_configuration']
    assert '--enable-version3' in lock['ffprobe_configuration']
    assert '--enable-nonfree' not in lock['ffprobe_configuration']
    assert hashlib.sha256(lock['ffprobe_configuration'].encode()).hexdigest() == lock['ffprobe_configuration_sha256']
    assert lock['source_correspondence_verified'] is False
    assert len(lock['distribution_blockers']) > 0


def test_locked_download_rejects_substitution(tmp_path, monkeypatch):
    import io
    fetcher = load('fetch_ffprobe')
    monkeypatch.setattr(fetcher.urllib.request, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'actual bytes'))
    target = tmp_path / 'data.zip'
    with pytest.raises(ValueError, match='checksum mismatch'):
        fetcher.download_checked('https://example.invalid/pinned.zip', '0' * 64, target)
    with pytest.raises(ValueError, match='never latest'):
        fetcher.download_checked('https://example.invalid/latest/data.zip', '0' * 64, target)
    target.unlink()
    fetcher.download_checked('https://example.invalid/pinned.zip', hashlib.sha256(b'actual bytes').hexdigest(), target)
    assert target.read_bytes() == b'actual bytes'


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'C:/drive', 'dir\\escape'])
def test_locked_archive_paths_cannot_escape(name):
    with pytest.raises(ValueError):
        load('fetch_ffprobe').safe_member(name)


def test_final_executable_must_embed_exact_locked_ffprobe(tmp_path, monkeypatch):
    import PyInstaller.archive.readers
    legal = load('package_legal')
    payload = b'Fixture bytes, not a real binary'
    path = tmp_path / 'lock.json'
    path.write_text(json.dumps({'ffprobe_sha256': hashlib.sha256(payload).hexdigest(), 'ffprobe_version': 'fixture'}))
    monkeypatch.setattr(legal, 'FFPROBE_LOCK_PATH', path)
    class Reader:
        toc = {'ffprobe.exe': None}
        def __init__(self, name):
            pass
        def extract(self, name):
            return payload
    monkeypatch.setattr(PyInstaller.archive.readers, 'CArchiveReader', Reader)
    legal.verify_embedded_ffprobe('fake.exe', tmp_path)
    assert json.loads((tmp_path / 'embedded-ffprobe-verification.json').read_text())['sha256'] == hashlib.sha256(payload).hexdigest()
    path.write_text(json.dumps({'ffprobe_sha256': '0' * 64, 'ffprobe_version': 'fixture'}))
    with pytest.raises(RuntimeError, match='differs from pinned'):
        legal.verify_embedded_ffprobe('fake.exe', tmp_path)
