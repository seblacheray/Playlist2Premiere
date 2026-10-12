from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit, unquote


class MediaResolver:
    """Prefer exact paths; never silently pick one of several basename matches."""
    def __init__(self, playlist_dir: Path, media_dir: Path):
        self.playlist_dir = playlist_dir
        self.media_dir = media_dir
        self._index = None

    def resolve(self, value: str) -> Path:
        if value.lower().startswith('file:'):
            url = urlsplit(value)
            value = unquote(url.path)
            if url.netloc:
                value = '//' + url.netloc + value
            elif len(value) > 2 and value[0] == '/' and value[2] == ':':
                value = value[1:]
        elif '://' in value:
            raise ValueError('Les URL distantes ne sont pas prises en charge')
        windows = PureWindowsPath(value)
        local = Path(value.replace('\\', '/'))
        candidates = [local] if local.is_absolute() or windows.is_absolute() else [self.playlist_dir / local, self.media_dir / local]
        for candidate in candidates:
            try:
                exists = candidate.is_file()
            except OSError:
                # An unavailable network path may raise instead of returning False.
                # Only this existence check falls back; other errors remain visible.
                continue
            if exists:
                return candidate.resolve()
        if self._index is None:
            index = {}
            for path in self.media_dir.rglob('*'):
                if path.is_file():
                    index.setdefault(path.name.casefold(), []).append(path)
            # Publish only a complete index; a failed scan must not hide ambiguity.
            self._index = index
        matches = self._index.get(windows.name.casefold(), [])
        if len(matches) > 1:
            raise ValueError(f'Chemin ambigu ({len(matches)} fichiers) : {value}')
        if not matches:
            raise FileNotFoundError(f'Média introuvable : {value}')
        return matches[0].resolve()
