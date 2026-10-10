from fractions import Fraction as F
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from playlist2premiere.playlist import read_playlist, parse_pls, parse_mpcpl
from playlist2premiere.paths import MediaResolver
from playlist2premiere.probe import Media, Audio, parse_probe
from playlist2premiere.timeline import build_timeline, Settings, frames
from playlist2premiere.xml_export import export_bytes, write_xml


def media(path, fps=F(25), duration=F(1), audio=True):
    return Media(path.resolve(), duration, fps, 1920, 1080, 0, F(0), (Audio(1, 2, 48000, duration, F(0)),) if audio else ())


def test_pls_order_duplicates_and_equals():
    entries = parse_pls('[playlist]\nFile2=a=b.mp4\nFile1=a=b.mp4\nTitle1=été\nLength1=-1\n')
    assert [e.index for e in entries] == [1, 2]
    assert [e.path for e in entries] == ['a=b.mp4'] * 2
    assert entries[0].title == 'été'


def test_mpcpl_type_order_and_commas():
    entries = parse_mpcpl('MPCPLAYLIST\n2,type,0\n2,filename,é,té.mp4\n1,type,0\n1,filename,é,té.mp4')
    assert [e.index for e in entries] == [2, 1]
    assert [e.path for e in entries] == ['é,té.mp4'] * 2


@pytest.mark.parametrize('text', ['MPCPLAYLIST\n1,filename,a', 'MPCPLAYLIST\n1,type,1\n1,filename,a', 'MPCPLAYLIST\n1,type,0\n1,filename,a\n1,filename,b'])
def test_mpcpl_unsupported(text):
    with pytest.raises(ValueError):
        parse_mpcpl(text)


@pytest.mark.parametrize('encoding', ['utf-8-sig', 'utf-16', 'cp1252'])
def test_encoding(tmp_path, encoding):
    path = tmp_path / 'liste.pls'
    path.write_bytes('[playlist]\nFile1=été.mp4'.encode(encoding))
    assert read_playlist(path)[0].path == 'été.mp4'


def test_paths(tmp_path):
    sub = tmp_path / 'dossier'
    sub.mkdir()
    file = sub / 'été & #1.mp4'
    file.touch()
    resolver = MediaResolver(tmp_path, tmp_path)
    for value in [str(file), 'dossier\\été & #1.mp4', file.as_uri(), 'C:\\ancien\\été & #1.mp4', '\\\\serveur\\partage\\été & #1.mp4']:
        assert resolver.resolve(value) == file
    with pytest.raises(FileNotFoundError):
        resolver.resolve('absent.mp4')
    other = tmp_path / 'autre'
    other.mkdir()
    (other / file.name).touch()
    with pytest.raises(ValueError, match='ambigu'):
        MediaResolver(tmp_path, tmp_path).resolve('D:\\ancien\\' + file.name)


def test_probe_exact_duration_and_audio(tmp_path):
    data = {'streams': [dict(codec_type='video', index=0, width=1920, height=1080, avg_frame_rate='30000/1001', r_frame_rate='30000/1001', duration_ts=60060, time_base='1/30000', start_time='0'), dict(codec_type='audio', index=1, channels=2, sample_rate='48000', duration_ts=96096, time_base='1/48000', start_time='0')]}
    result = parse_probe(tmp_path / 'a.mp4', data)
    assert result.duration == F(1001, 500)
    assert result.fps == F(30000, 1001)
    assert result.audio[0].duration == result.duration
    del data['streams'][0]['duration_ts']
    with pytest.raises(ValueError, match='absente'):
        parse_probe(tmp_path / 'a.mp4', data)


def test_no_cumulative_drift_and_mixed_rates(tmp_path):
    sources = [media(tmp_path / 'a.mp4', F(24000, 1001), F(1001, 24000))] * 1000
    sequence = build_timeline(sources, Settings(1280, 720, F(30000, 1001)))
    assert sequence.duration == 1250
    assert all(a.end == b.start for a, b in zip(sequence.clips, sequence.clips[1:]))
    mixed = build_timeline([media(tmp_path / 'a', F(24), F(5, 4)), media(tmp_path / 'b', F(30000, 1001), F(1001, 1000))])
    assert mixed.clips[1].source_end == 30
    assert mixed.duration == frames(F(5, 4) + F(1001, 1000), F(24))


def test_xml_duplicates_audio_rates_and_escaping(tmp_path):
    first = media(tmp_path / 'été & #1.mp4', F(24000, 1001), F(1001, 1000))
    second = media(tmp_path / 'b.mp4', F(30000, 1001), F(1001, 1000), False)
    sequence = build_timeline([first, second, first])
    root = ET.fromstring(export_bytes(sequence))
    assert root.findtext('.//sequence/rate/timebase') == '24'
    assert root.findtext('.//sequence/rate/ntsc') == 'TRUE'
    clips = root.findall('.//sequence/media/video/track/clipitem')
    assert len(clips) == 3
    assert [(c.findtext('start'), c.findtext('end')) for c in clips] == [('0', '24'), ('24', '48'), ('48', '72')]
    assert len(root.findall('.//sequence/media/audio/track')) == 2
    assert len(root.findall('.//sequence/media/audio/track/clipitem')) == 4
    assert len(root.findall('.//file/pathurl')) == 2
    assert root.findtext('.//file/pathurl') == first.path.as_uri()
    assert root.find('.//timecode') is None
    for link in root.findall('.//link'):
        ref = link.findtext('linkclipref')
        assert root.find(f'.//clipitem[@id="{ref}"]') is not None


def test_audio_offset_and_multi_stream(tmp_path):
    item = media(tmp_path / 'a.mp4', duration=F(2))
    item = Media(item.path, item.duration, item.fps, item.width, item.height, 0, F(0), (Audio(1, 2, 48000, F(1), F(1, 2)), Audio(2, 1, 44100, F(2), F(0))))
    root = ET.fromstring(export_bytes(build_timeline([item])))
    clips = root.findall('.//sequence/media/audio/track/clipitem')
    assert len(clips) == 3
    assert clips[0].findtext('start') == '13'
    assert clips[0].findtext('end') == '38'
    assert clips[0].findtext('in') == '0'
    assert clips[2].findtext('sourcetrack/trackindex') == '3'


def test_write_protects_source(tmp_path):
    source = tmp_path / 'source.xml'
    source.write_text('original')
    with pytest.raises(ValueError):
        write_xml(build_timeline([media(source)]), source)
    assert source.read_text() == 'original'


def test_invalid_sequence_rate(tmp_path):
    with pytest.raises(ValueError, match='représentable'):
        build_timeline([media(tmp_path / 'a')], Settings(1920, 1080, F('29.97')))


@pytest.mark.parametrize('change', ['missing_start', 'variable_rate', 'missing_audio_duration'])
def test_probe_rejects_uncertain_metadata(tmp_path, change):
    video = dict(codec_type='video', index=0, width=640, height=360, avg_frame_rate='25', r_frame_rate='25', duration='2', start_time='0')
    audio = dict(codec_type='audio', index=1, channels=2, sample_rate='48000', duration='2', start_time='0')
    if change == 'missing_start':
        del video['start_time']
    elif change == 'variable_rate':
        video['avg_frame_rate'] = '249/10'
    else:
        del audio['duration']
    with pytest.raises(ValueError):
        parse_probe(tmp_path / 'a.mp4', {'streams': [video, audio], 'format': {'duration': '999'}})
