"""Generate a bounded corpus and compare the application's exact probe command.

Raw JSON differences and application-level compatibility are distinct outcomes.
No candidate binary or media is copied to the report directory.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from playlist2premiere.probe import parse_probe
from playlist2premiere.timeline import build_timeline
from playlist2premiere.xml_export import export_bytes


def json_diff(left, right, path=''):
    if type(left) is not type(right):
        return [{'path': path, 'baseline': left, 'candidate': right}]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                result.append({'path': f'{path}/{key}', 'baseline': left.get(key), 'candidate': right.get(key)})
            else:
                result.extend(json_diff(left[key], right[key], f'{path}/{key}'))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [{'path': path, 'baseline': left, 'candidate': right}]
        return [difference for index, (a, b) in enumerate(zip(left, right)) for difference in json_diff(a, b, f'{path}/{index}')]
    return [] if left == right else [{'path': path, 'baseline': left, 'candidate': right}]


def probe_result(executable, path):
    command = [str(executable), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path.resolve())]
    start = time.monotonic()
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    result = {'command': command, 'exit_code': process.returncode, 'seconds': time.monotonic() - start,
              'stderr': process.stderr, 'stdout': process.stdout}
    if process.returncode == 0:
        result['metadata'] = json.loads(process.stdout)
    return result


def compare_app(path, baseline, candidate):
    results = []
    for result in (baseline, candidate):
        if result['exit_code']:
            results.append(('process_error', result['exit_code']))
        else:
            try:
                results.append(('media', parse_probe(path, result['metadata'])))
            except (ValueError, KeyError, TypeError) as error:
                results.append(('application_rejection', type(error).__name__, str(error)))
    return results[0] == results[1], results


def fixture_passes(same, process_ok, media_unchanged, accepted, require_acceptance):
    return same and process_ok and media_unchanged and (accepted or not require_acceptance)


def publish_summary(summary):
    filename = os.environ.get('GITHUB_STEP_SUMMARY')
    if not filename:
        return
    lines = ['# Experimental FFprobe comparison',
             f'Native Windows: {summary["native_windows"]}',
             f'Candidate size: **{summary["candidate_size_bytes"]} bytes**',
             f'Candidate SHA-256: `{summary["candidate_sha256"]}`',
             f'Comparison passed: {summary.get("comparison_passed", "pending")}', '',
             '| Fixture | Accepted by app | App equivalent | Raw JSON differences |',
             '| --- | --- | --- | --- |']
    for item in summary['fixtures']:
        lines.append(f'| {item["name"]} | {item.get("accepted_by_application", "error")} | {item.get("app_equivalent", "error")} | {item.get("raw_difference_count", "error")} |')
    lines += ['', 'Matching MKV duration rejections are baseline limitations, not usable-format validation.',
              'Experimental binary only; no distribution or source-compliance approval.']
    Path(filename).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(args):
    args.reports.mkdir(parents=True, exist_ok=True)
    args.media.mkdir(parents=True, exist_ok=True)
    fixtures = [
        ('h264-aac-25.mp4', 'libx264', '25', 'aac', False),
        ('h264-aac-ntsc.mp4', 'libx264', '30000/1001', 'aac', False),
        ('hevc-aac.mp4', 'libx265', '25', 'aac', False),
        ('h264-aac.mkv', 'libx264', '25', 'aac', False),
        ('h264-multiaudio.mp4', 'libx264', '25', 'aac', True),
    ]
    summary = {'experimental': True, 'fixtures': [], 'native_windows': __import__('sys').platform == 'win32',
               'candidate_size_bytes': args.candidate.stat().st_size,
               'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
               'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
               'limits': ['Generated corpus is not exhaustive', 'MKV may lack required per-stream durations',
                          'No AV1, compressed headers, UNC or UHD validation in this first corpus',
                          'Toolchain/static zlib source completeness remains under review']}
    (args.reports / 'comparison-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    failed = False
    for number, (name, codec, fps, audio, multi) in enumerate(fixtures, 1):
        path = (args.media / ('été & #1 + 100% ' + name)).resolve()
        command = [str(args.ffmpeg), '-nostdin', '-v', 'error', '-n', '-f', 'lavfi', '-i', f'color=s=320x180:r={fps}',
                   '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000']
        if multi:
            command += ['-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=44100']
        command += ['-map', '0:v', '-map', '1:a']
        if multi:
            command += ['-map', '2:a']
        command += ['-t', '2.002', '-c:v', codec, '-threads', '2', '-pix_fmt', 'yuv420p', '-c:a', audio, '-ac', '2']
        if codec == 'libx265':
            command += ['-x265-params', 'pools=1:frame-threads=1']
        command += [str(path)]
        try:
            generated = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
            (args.reports / f'{number}-generation.json').write_text(json.dumps({'command': command, 'exit_code': generated.returncode, 'stderr': generated.stderr}, indent=2), encoding='utf-8')
            if generated.returncode:
                raise RuntimeError('Fixture generation failed')
            original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            baseline = probe_result(args.baseline, path)
            candidate = probe_result(args.candidate, path)
            for label, result in [('baseline', baseline), ('candidate', candidate)]:
                (args.reports / f'{number}-{label}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            same, app = compare_app(path, baseline, candidate)
            differences = json_diff(baseline.get('metadata'), candidate.get('metadata'))
            (args.reports / f'{number}-differences.json').write_text(json.dumps(differences, indent=2), encoding='utf-8')
            accepted = all(item[0] == 'media' for item in app)
            process_ok = baseline['exit_code'] == candidate['exit_code'] == 0
            audio_count = len(candidate.get('metadata', {}).get('streams', []))
            if multi:
                audio_count = sum(s.get('codec_type') == 'audio' for s in candidate.get('metadata', {}).get('streams', []))
                if audio_count != 2:
                    same = False
            if same and accepted:
                old_xml = export_bytes(build_timeline([app[0][1]]))
                new_xml = export_bytes(build_timeline([app[1][1]]))
                if old_xml != new_xml:
                    same = False
            media_unchanged = original_hash == hashlib.sha256(path.read_bytes()).hexdigest()
            summary['fixtures'].append({'name': name, 'codec': codec, 'fps': fps, 'multi_audio': multi,
                                        'application_results': [repr(item) for item in app],
                                        'app_equivalent': same, 'accepted_by_application': accepted,
                                        'probe_processes_ok': process_ok, 'raw_difference_count': len(differences),
                                        'media_unchanged': media_unchanged})
            failed |= not fixture_passes(same, process_ok, media_unchanged, accepted, name.endswith('.mp4'))
        except Exception as error:
            summary['fixtures'].append({'name': name, 'error': f'{type(error).__name__}: {error}'})
            failed = True
        (args.reports / 'comparison-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    summary['comparison_passed'] = not failed
    summary['baseline_limitations'] = [item['name'] for item in summary['fixtures'] if item.get('probe_processes_ok') and not item.get('accepted_by_application')]
    (args.reports / 'comparison-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    publish_summary(summary)
    if failed:
        raise SystemExit('Probe comparison failed; inspect reports. Existing distribution is unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'baseline', 'ffmpeg', 'media', 'reports']:
        parser.add_argument('--' + name, type=Path, required=True)
    main(parser.parse_args())
