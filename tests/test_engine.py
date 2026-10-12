from fractions import Fraction as F
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from playlist2premiere.playlist import read_playlist, parse_pls, parse_mpcpl
from playlist2premiere.paths import MediaResolver
from playlist2premiere.probe import Media, Audio, parse_probe
from playlist2premiere.timeline import build_timeline, Settings, frames
from playlist2premiere.xml_export import export_bytes, write_xml, premiere_pathurl


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
    assert root.findtext('.//file/pathurl') == premiere_pathurl(first.path)
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


@pytest.mark.parametrize('source,expected', [
    (r'D:\Videos\Part2.mp4', 'file://localhost/D%3a/Videos/Part2.mp4'),
    (r'C:\Mes vidéos\été & #1 + 100%.mp4', 'file://localhost/C%3a/Mes%20vid%C3%A9os/%C3%A9t%C3%A9%20%26%20%231%20%2B%20100%25.mp4'),
    (r'd:\dossier\déjà%20.mp4', 'file://localhost/d%3a/dossier/d%C3%A9j%C3%A0%2520.mp4'),
])
def test_premiere_windows_pathurl(source, expected):
    from pathlib import PureWindowsPath
    assert premiere_pathurl(PureWindowsPath(source)) == expected


def test_unc_and_posix_urls_unchanged():
    from pathlib import PureWindowsPath, PurePosixPath
    for path in [PureWindowsPath(r'\\serveur\partage\été & #1.mp4'), PurePosixPath('/tmp/été & #1.mp4')]:
        assert premiere_pathurl(path) == path.as_uri()


def test_export_changes_only_windows_pathurl(monkeypatch):
    from pathlib import PureWindowsPath
    from playlist2premiere import xml_export
    sources = [Media(PureWindowsPath(f'D:/Mes vidéos/Part{i}.mp4'), F(n, 25), F(25), 1920, 1080, 0, F(0), (Audio(1, 2, 48000, F(n, 25), F(0)),)) for i, n in enumerate([124, 123, 71], 1)]
    timeline = build_timeline(sources)
    corrected = export_bytes(timeline)
    monkeypatch.setattr(xml_export, 'premiere_pathurl', lambda path: path.as_uri())
    original = export_bytes(timeline)
    expected = original
    for source in sources:
        expected = expected.replace(source.path.as_uri().encode(), premiere_pathurl(source.path).encode())
    assert corrected == expected  # Includes audio, sourcetrack, IDs, rates and all timings.
    root = ET.fromstring(corrected)
    assert root.findtext('./sequence/duration') == '318'
    assert [(c.findtext('start'), c.findtext('end')) for c in root.findall('./sequence/media/video/track/clipitem')] == [('0', '124'), ('124', '247'), ('247', '318')]
    assert len(root.findall('./sequence/media/video/track/clipitem/sourcetrack')) == 3


def test_windows_reserved_characters_produce_valid_xml():
    from pathlib import PureWindowsPath
    from urllib.parse import unquote, urlsplit
    # These characters are legal in Windows filenames, but reserved in URI/XML syntax.
    path = PureWindowsPath("D:/L'été & montage/[prise] #1 + 100% ;,@=.mp4")
    source = Media(path, F(123, 25), F(25), 1920, 1080, 0, F(0), ())
    payload = export_bytes(build_timeline([source]))
    root = ET.fromstring(payload)
    uri = root.findtext('.//file/pathurl')
    assert uri == "file://localhost/D%3a/L%27%C3%A9t%C3%A9%20%26%20montage/%5Bprise%5D%20%231%20%2B%20100%25%20%3B%2C%40%3D.mp4"
    parsed = urlsplit(uri)
    assert parsed.netloc == 'localhost'
    assert parsed.query == parsed.fragment == ''
    assert unquote(parsed.path) == '/' + path.as_posix()
    assert root.findtext('.//clipitem/name') == path.name
