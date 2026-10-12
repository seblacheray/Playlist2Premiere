from pathlib import Path
import errno
import pytest
from playlist2premiere.paths import MediaResolver

UNC = r'\\serveur\partage\été & #1.mp4'


def mock_unc(monkeypatch, result=False, error=None):
    original = Path.is_file
    calls = []
    candidate = Path(UNC.replace('\\', '/'))

    def is_file(path):
        if path == candidate:
            calls.append(path)
            if error is not None:
                raise error
            return result
        return original(path)

    monkeypatch.setattr(Path, 'is_file', is_file)
    return calls


@pytest.mark.parametrize('code', [64, 53, 5])
def test_unavailable_unc_falls_back_to_unique_local_file(tmp_path, monkeypatch, code):
    source = tmp_path / 'été & #1.mp4'
    source.touch()
    error = OSError(errno.EIO, 'Simulated inaccessible share')
    error.winerror = code
    calls = mock_unc(monkeypatch, error=error)
    assert MediaResolver(tmp_path, tmp_path).resolve(UNC) == source.resolve()
    assert len(calls) == 1


@pytest.mark.parametrize('count', [0, 2])
def test_unavailable_unc_preserves_missing_and_ambiguity(tmp_path, monkeypatch, count):
    for i in range(count):
        directory = tmp_path / str(i)
        directory.mkdir()
        (directory / 'été & #1.mp4').touch()
    mock_unc(monkeypatch, error=OSError(errno.EIO, 'Unavailable share'))
    with pytest.raises(FileNotFoundError if count == 0 else ValueError):
        MediaResolver(tmp_path, tmp_path).resolve(UNC)


def test_available_unc_keeps_exact_path_priority(tmp_path, monkeypatch):
    mock_unc(monkeypatch, result=True)
    candidate = Path(UNC.replace('\\', '/'))
    original = Path.resolve
    monkeypatch.setattr(Path, 'resolve', lambda path: candidate if path == candidate else original(path))
    monkeypatch.setattr(Path, 'rglob', lambda *args: pytest.fail('Exact UNC must not scan local files'))
    assert MediaResolver(tmp_path, tmp_path).resolve(UNC) == candidate


def test_programming_error_not_swallowed(tmp_path, monkeypatch):
    mock_unc(monkeypatch, error=RuntimeError('Unexpected implementation error'))
    with pytest.raises(RuntimeError):
        MediaResolver(tmp_path, tmp_path).resolve(UNC)


@pytest.mark.parametrize('failure', ['rglob', 'is_file'])
def test_failed_scan_does_not_cache_partial_index(tmp_path, monkeypatch, failure):
    resolver = MediaResolver(tmp_path, tmp_path)
    def entries(*args):
        yield tmp_path / 'one.mp4'
        if failure == 'rglob':
            raise OSError(errno.EACCES, 'Incomplete directory scan')
        yield tmp_path / 'two.mp4'
    def is_file(path):
        if path.name == 'one.mp4':
            return True
        if path.name == 'two.mp4':
            raise OSError(errno.EACCES, 'Inaccessible entry')
        return False
    monkeypatch.setattr(Path, 'rglob', entries)
    monkeypatch.setattr(Path, 'is_file', is_file)
    with pytest.raises(OSError):
        resolver.resolve('missing.mp4')
    assert resolver._index is None
