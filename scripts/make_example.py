"""Generate three real test clips and an XML referring to their absolute paths."""
from pathlib import Path
import subprocess
from playlist2premiere.probe import probe
from playlist2premiere.timeline import build_timeline
from playlist2premiere.xml_export import write_xml


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / 'examples' / 'media'
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, (color, rate, size) in enumerate([('red', '24000/1001', '640x360'), ('green', '30000/1001', '1280x720'), ('blue', '25', '640x360')], 1):
        path = directory / f'clip{index}.mp4'
        if path.exists():
            raise FileExistsError(f'Exemple existant, ne sera pas écrasé : {path}')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-f', 'lavfi', '-i', f'color=c={color}:s={size}:r={rate}', '-f', 'lavfi', '-i', f'sine=frequency={index * 440}:sample_rate=48000', '-t', '2.002', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ac', '2', '-shortest', str(path)], check=True)
        paths.append(path)
    playlist = root / 'examples' / 'three_clips.pls'
    playlist.write_text('[playlist]\n' + ''.join(f'File{i}=media/{path.name}\n' for i, path in enumerate(paths, 1)) + 'NumberOfEntries=3\nVersion=2\n', encoding='utf-8')
    destination = root / 'examples' / 'three_clips.xml'
    write_xml(build_timeline([probe(path) for path in paths]), destination, 'Trois clips — test Premiere 2026')
    print(destination)


if __name__ == '__main__':
    main()
