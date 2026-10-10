"""FCP 7 xmeml v5. Source in/out are media-relative frames, not invented timecode."""
from pathlib import Path
from fractions import Fraction
import os
import tempfile
import xml.etree.ElementTree as ET
from .timeline import Timeline, rate_parts, frames


def node(parent, tag, value=None, **attrs):
    child = ET.SubElement(parent, tag, attrs)
    if value is not None:
        child.text = str(value)
    return child


def rate(parent, fps):
    base, ntsc = rate_parts(fps)
    element = node(parent, 'rate')
    node(element, 'timebase', base)
    node(element, 'ntsc', 'TRUE' if ntsc else 'FALSE')


def video_format(parent, width, height, fps):
    sample = node(parent, 'samplecharacteristics')
    rate(sample, fps)
    node(sample, 'width', width)
    node(sample, 'height', height)
    node(sample, 'anamorphic', 'FALSE')
    node(sample, 'pixelaspectratio', 'square')
    node(sample, 'fielddominance', 'none')


def export_bytes(timeline: Timeline, name='Playlist2Premiere') -> bytes:
    root = ET.Element('xmeml', version='5')
    sequence = node(root, 'sequence', id='sequence-1')
    node(sequence, 'name', name)
    node(sequence, 'duration', timeline.duration)
    rate(sequence, timeline.settings.fps)
    media_node = node(sequence, 'media')
    video = node(media_node, 'video')
    video_format(node(video, 'format'), timeline.settings.width, timeline.settings.height, timeline.settings.fps)
    video_track = node(video, 'track')
    audio = node(media_node, 'audio')
    audio_sample = node(node(audio, 'format'), 'samplecharacteristics')
    node(audio_sample, 'depth', 16)
    node(audio_sample, 'samplerate', 48000)
    audio_tracks = []
    file_ids = {}
    defined = set()
    for number, clip in enumerate(timeline.clips, 1):
        source = clip.media
        file_id = file_ids.setdefault(source.path, f'file-{len(file_ids) + 1}')
        video_id = f'clip-{number}-video'
        links = [(video_id, 'video', 1)]
        audio_specs = []
        channel_index = 0
        for stream in source.audio:
            offset = stream.start - source.start
            begin = max(Fraction(0), offset)
            end = min(source.duration, offset + stream.duration)
            for channel in range(stream.channels):
                channel_index += 1
                if end <= begin:
                    continue
                # Sequence boundaries derive from this clip's quantized video start.
                seq_start = min(clip.end, clip.start + frames(begin, timeline.settings.fps))
                seq_end = min(clip.end, clip.start + frames(end, timeline.settings.fps))
                if seq_end <= seq_start:
                    continue
                audio_id = f'clip-{number}-audio-{channel_index}'
                audio_specs.append((audio_id, channel_index, seq_start, seq_end, frames(begin - offset, source.fps), frames(end - offset, source.fps)))
                links.append((audio_id, 'audio', channel_index))
        def make_clip(parent, clip_id, kind, track_index, start, end, source_in, source_out):
            element = node(parent, 'clipitem', id=clip_id)
            node(element, 'name', source.path.name)
            node(element, 'enabled', 'TRUE')
            node(element, 'duration', clip.source_end)
            rate(element, source.fps)
            for tag, value in [('start', start), ('end', end), ('in', source_in), ('out', source_out)]:
                node(element, tag, value)
            file_element = node(element, 'file', id=file_id)
            if file_id not in defined:
                defined.add(file_id)
                node(file_element, 'name', source.path.name)
                node(file_element, 'pathurl', source.path.as_uri())
                rate(file_element, source.fps)
                node(file_element, 'duration', clip.source_end)
                fm = node(file_element, 'media')
                video_format(node(fm, 'video'), source.width, source.height, source.fps)
                for stream in source.audio:
                    fa = node(fm, 'audio')
                    sc = node(fa, 'samplecharacteristics')
                    node(sc, 'samplerate', stream.sample_rate)
                    node(sc, 'channelcount', stream.channels)
                    node(fa, 'channelcount', stream.channels)
            st = node(element, 'sourcetrack')
            node(st, 'mediatype', kind)
            node(st, 'trackindex', track_index)
            for reference, mediatype, target_track in links:
                link = node(element, 'link')
                node(link, 'linkclipref', reference)
                node(link, 'mediatype', mediatype)
                node(link, 'trackindex', target_track)
                node(link, 'clipindex', number if mediatype == 'video' else 1)
            return element
        make_clip(video_track, video_id, 'video', 1, clip.start, clip.end, 0, clip.source_end)
        for spec in audio_specs:
            audio_id, channel, start, end, source_in, source_out = spec
            while len(audio_tracks) < channel:
                audio_tracks.append(node(audio, 'track'))
            make_clip(audio_tracks[channel - 1], audio_id, 'audio', channel, start, end, source_in, source_out)
    # Link clipindex counts clips actually present on each destination track.
    positions = {}
    for kind in ('video', 'audio'):
        for index, track in enumerate(media_node.findall(f'{kind}/track'), 1):
            for position, item in enumerate(track.findall('clipitem'), 1):
                positions[item.attrib['id']] = (index, position)
    for link in sequence.findall('.//clipitem/link'):
        index, position = positions[link.findtext('linkclipref')]
        link.find('trackindex').text = str(index)
        link.find('clipindex').text = str(position)
    ET.indent(root, space='  ')
    return b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding='utf-8') + b'\n'


def write_xml(timeline: Timeline, destination: Path, name='Playlist2Premiere'):
    destination = destination.resolve()
    if destination.suffix.lower() != '.xml':
        raise ValueError('La destination doit avoir une extension .xml')
    if any(c.media.path == destination for c in timeline.clips):
        raise ValueError('La destination est un média source')
    payload = export_bytes(timeline, name)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False, suffix='.tmp') as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        os.replace(temporary, destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
