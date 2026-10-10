import shutil
import subprocess
from pathlib import Path
from fractions import Fraction
import xml.etree.ElementTree as ET
import pytest
from playlist2premiere.probe import probe
from playlist2premiere.timeline import build_timeline
from playlist2premiere.xml_export import export_bytes


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg et FFprobe requis')
def test_real_ffprobe_to_xml(tmp_path):
    paths = []
    for i, rate in enumerate(['24000/1001', '30000/1001', '25']):
        path = tmp_path / f'vidéo & {i}.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', f'color=s=160x90:r={rate}', '-f', 'lavfi', '-i', 'sine=sample_rate=48000', '-t', '0.5', '-c:v', 'libx264', '-c:a', 'aac', '-ac', '2', '-shortest', str(path)], check=True)
        paths.append(path)
    original = [p.read_bytes() for p in paths]
    sources = [probe(p) for p in paths]
    assert [m.fps for m in sources] == [Fraction(24000, 1001), Fraction(30000, 1001), Fraction(25)]
    assert all(m.audio[0].channels == 2 for m in sources)
    root = ET.fromstring(export_bytes(build_timeline(sources)))
    assert len(root.findall('.//sequence/media/video/track/clipitem')) == 3
    assert len(root.findall('.//sequence/media/audio/track/clipitem')) == 6
    assert [p.read_bytes() for p in paths] == original
