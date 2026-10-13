import importlib.util
from pathlib import Path
from fractions import Fraction

spec = importlib.util.spec_from_file_location('compare_probes', Path(__file__).parents[1] / 'scripts/experimental/compare_probes.py')
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def metadata():
    return {'streams': [{'index': 0, 'codec_type': 'video', 'avg_frame_rate': '25/1', 'r_frame_rate': '25/1',
                         'width': 1920, 'height': 1080, 'duration_ts': 318, 'time_base': '1/25', 'start_time': '0'}],
            'format': {'duration': '12.72'}}


def test_raw_metadata_changes_are_not_hidden():
    assert compare.json_diff({'streams': [{'width': 1920}]}, {'streams': [{'width': 1280}]}) == [
        {'path': '/streams/0/width', 'baseline': 1920, 'candidate': 1280}]
    assert compare.json_diff({'a': 1}, {'a': 1, 'b': 2})


def test_application_equivalence_requires_matching_timing(tmp_path):
    left, right = {'exit_code': 0, 'metadata': metadata()}, {'exit_code': 0, 'metadata': metadata()}
    same, results = compare.compare_app(tmp_path / 'media.mp4', left, right)
    assert same and results[0][1].duration == Fraction(318, 25)
    right['metadata']['streams'][0]['duration_ts'] = 319
    assert not compare.compare_app(tmp_path / 'media.mp4', left, right)[0]


def test_identical_application_rejections_remain_rejections(tmp_path):
    data = metadata()
    del data['streams'][0]['duration_ts']
    result = {'exit_code': 0, 'metadata': data}
    same, outcomes = compare.compare_app(tmp_path / 'media.mkv', result, result)
    assert same
    assert all(outcome[0] == 'application_rejection' for outcome in outcomes)


def test_exact_probe_arguments_and_timeout(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps(metadata()), stderr='')
    monkeypatch.setattr(compare.subprocess, 'run', run)
    path = tmp_path / 'été & #1 + 100%.mp4'
    result = compare.probe_result('candidate.exe', path)
    assert calls[0][0] == ['candidate.exe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path.resolve())]
    assert calls[0][1]['timeout'] == 120
    assert 'shell' not in calls[0][1]
    assert result['exit_code'] == 0
