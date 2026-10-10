"""Local playlist readers. Playlist duration hints are never authoritative."""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Entry:
    index: int
    path: str
    title: str = ""


def read_playlist(path: Path, encoding: str | None = None) -> list[Entry]:
    data = path.read_bytes()
    if encoding:
        text = data.decode(encoding)
    elif data.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = data.decode('utf-16')
    else:
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = data.decode('cp1252')
    if path.suffix.lower() == '.pls':
        entries = parse_pls(text)
    elif path.suffix.lower() == '.mpcpl':
        entries = parse_mpcpl(text)
    else:
        raise ValueError('Format attendu : .pls ou .mpcpl')
    if not entries:
        raise ValueError('La playlist ne contient aucun média.')
    return entries


def parse_pls(text: str) -> list[Entry]:
    records: dict[int, dict[str, str]] = {}
    section = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith((';', '#')):
            continue
        if line.startswith('['):
            section = line.lower() == '[playlist]'
            continue
        if not section:
            continue
        key, sep, value = line.partition('=')
        match = re.fullmatch(r'(File|Title|Length)([1-9]\d*)', key.strip(), re.I)
        if sep and match:
            record = records.setdefault(int(match[2]), {})
            field = match[1].lower()
            if field in record:
                raise ValueError(f'Clé PLS répétée : {key}')
            record[field] = value.strip()
    result = []
    for index, record in sorted(records.items()):
        if not record.get('file'):
            raise ValueError(f'Entrée PLS {index} sans fichier')
        result.append(Entry(index, record['file'], record.get('title', '')))
    return result


def parse_mpcpl(text: str) -> list[Entry]:
    lines = text.lstrip('\ufeff').splitlines()
    if not lines or lines[0].strip() != 'MPCPLAYLIST':
        raise ValueError('En-tête MPCPLAYLIST absent')
    records: dict[int, dict[str, str]] = {}
    order = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(',', 2)
        if len(parts) != 3 or not parts[0].isdigit() or int(parts[0]) < 1:
            raise ValueError(f'Ligne MPCPL invalide : {line}')
        index, field, value = int(parts[0]), parts[1].strip().lower(), parts[2].strip()
        record = records.setdefault(index, {})
        if field in ('filename', 'type', 'video', 'audio') and field in record:
            raise ValueError(f'Entrée {index} : médias externes multiples non pris en charge')
        record[field] = value
        if field == 'type':
            order.append(index)
    if set(order) != set(records):
        raise ValueError('Entrée MPCPL sans type')
    result = []
    for index in order:
        record = records[index]
        if record['type'] != '0' or 'audio' in record or 'video' in record:
            raise ValueError(f'Entrée {index} : périphérique ou doublage externe non pris en charge')
        if not record.get('filename'):
            raise ValueError(f'Entrée MPCPL {index} sans fichier')
        result.append(Entry(index, record['filename'], record.get('label', '')))
    return result
