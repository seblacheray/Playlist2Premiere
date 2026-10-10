from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import json
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class Audio:
    index: int
    channels: int
    sample_rate: int
    duration: Fraction
    start: Fraction


@dataclass(frozen=True)
class Media:
    path: Path
    duration: Fraction
    fps: Fraction
    width: int
    height: int
    video_index: int
    start: Fraction
    audio: tuple[Audio, ...]
    warnings: tuple[str, ...] = ()


def rational(value) -> Fraction:
    if value in (None, '', 'N/A', '0/0'):
        raise ValueError('Information temporelle absente')
    return Fraction(str(value))


def stream_duration(stream: dict) -> Fraction:
    if stream.get('duration_ts') is not None and stream.get('time_base'):
        result = rational(stream['duration_ts']) * rational(stream['time_base'])
    else:
        result = rational(stream.get('duration'))
    if result <= 0:
        raise ValueError('Durée absente ou non positive')
    return result


def parse_probe(path: Path, data: dict) -> Media:
    streams = data.get('streams', [])
    videos = [s for s in streams if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')]
    if not videos:
        raise ValueError('Aucune piste vidéo exploitable')
    if len(videos) != 1:
        raise ValueError('Plusieurs pistes vidéo : sélection non prise en charge')
    video = videos[0]
    fps = rational(video.get('avg_frame_rate'))
    nominal = rational(video.get('r_frame_rate'))
    if fps <= 0 or nominal <= 0:
        raise ValueError('Cadence absente ou invalide')
    if fps != nominal:
        raise ValueError('Cadence variable ou contradictoire : transcoder en cadence constante avant export')
    duration = stream_duration(video)
    width, height = int(video.get('width', 0)), int(video.get('height', 0))
    if width <= 0 or height <= 0:
        raise ValueError('Résolution absente')
    # Missing timestamps are not replaced with synthetic timecodes or zero offsets.
    start = rational(video.get('start_time'))
    if video.get('sample_aspect_ratio', '1:1') not in ('1:1', '0:1', 'N/A'):
        raise ValueError('Pixels non carrés non pris en charge')
    if video.get('field_order', 'progressive') not in ('progressive', 'unknown'):
        raise ValueError('Vidéo entrelacée non prise en charge')
    if any(int(s.get('rotation', 0)) % 360 for s in video.get('side_data_list', [])):
        raise ValueError('Rotation vidéo : normaliser le média avant export')
    audio = []
    for stream in streams:
        if stream.get('codec_type') != 'audio':
            continue
        channels, sample_rate = int(stream.get('channels', 0)), int(stream.get('sample_rate', 0))
        if channels <= 0 or sample_rate <= 0:
            raise ValueError('Métadonnées audio absentes')
        track = Audio(int(stream['index']), channels, sample_rate, stream_duration(stream), rational(stream.get('start_time')))
        audio.append(track)
    warnings = ()
    if any(a.start != start or a.duration != duration for a in audio):
        warnings = ('Audio : décalages et durées propres conservés dans les limites du clip vidéo.',)
    return Media(path.resolve(), duration, fps, width, height, int(video['index']), start, tuple(audio), warnings)


def find_ffprobe() -> str:
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'ffprobe.exe'
    if bundled.is_file():
        return str(bundled)
    executable = shutil.which('ffprobe')
    if not executable:
        raise ValueError('FFprobe introuvable : installer FFmpeg et ajouter son dossier bin au PATH')
    return executable


def probe(path: Path, executable: str | None = None) -> Media:
    process = subprocess.run([executable or find_ffprobe(), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if process.returncode:
        raise ValueError(f'FFprobe : {process.stderr.strip()}')
    return parse_probe(path, json.loads(process.stdout))
