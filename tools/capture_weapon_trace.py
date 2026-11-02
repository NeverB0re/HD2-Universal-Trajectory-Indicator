"""Save one test-build run's weapon evidence without mixing repeated shot numbers.

Read-only game log access. Output is a new offline JSON file; an existing file is never
overwritten. --version refuses a stale run instead of silently analyzing an older build.
"""
import argparse
import json
import math
import re
from pathlib import Path

VERSION = re.compile(r'(?:Universal Trajectory Indicator|Stratagem and C4 Trajectory) ([\w.\-]+), loader')
ENTRY = re.compile(r'weapon direction (\d+) (.*)$')
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
VECTOR = re.compile(r'([\w-]+) (' + NUMBER + r') (' + NUMBER + r') (' + NUMBER + r')$')
POSE = re.compile(r'(dt|muzzle|root|forward|camera|camera-forward)=([^=]+?)(?= [\w-]+=|$)')


def pose(text):
    result = {}
    for key, raw in POSE.findall(text):
        values = [float(x) for x in raw.split()]
        if len(values) != (1 if key == 'dt' else 3) or not all(map(math.isfinite, values)):
            raise ValueError('invalid pose field: ' + key)
        result[key] = values[0] if key == 'dt' else values
    if set(result) != {'dt', 'muzzle', 'root', 'forward', 'camera', 'camera-forward'}:
        raise ValueError('incomplete synchronized pose')
    return result


def parse_runs(text):
    runs, run = [], None
    for line in text.splitlines():
        version = VERSION.search(line)
        if version:
            run = dict(version=version[1], shots={})
            runs.append(run)
            continue
        entry = ENTRY.search(line)
        if not entry or run is None:
            continue
        number, detail = entry.groups()
        if detail.startswith('shot '):
            if number in run['shots']:
                raise ValueError('duplicate shot number within one run: ' + number)
            run['shots'][number] = dict(header=detail, vectors={}, tracks={}, candidates={},
                                       sync=[], pre_shot=[], summaries=[])
            continue
        row = run['shots'].get(number)
        if row is None:
            continue  # a truncated log can begin after a shot header
        if detail.startswith(('sync ', 'pre-shot ')):
            label, values = detail.split(' ', 1)
            observation = pose(values)
            if label == 'pre-shot' and not -.25 <= observation['dt'] < 0:
                raise ValueError('pre-shot time is outside the recorder window')
            row['pre_shot' if label == 'pre-shot' else 'sync'].append(observation)
        elif detail.startswith('offset-deg '):
            row['offset'] = detail
        elif detail.startswith('evidence-stance='):
            row['evidence_stance'] = detail.split('=', 1)[1].split(';', 1)[0]
        elif detail.startswith('candidate-summary '):
            row['summaries'].append(detail)
        elif detail.startswith('sample-end '):
            row['sample_end'] = detail
        elif detail.startswith('candidate '):
            match = re.match(r'candidate (\d+) kind=([0-9a-f]{16})[; ]', detail)
            if not match:
                raise ValueError('invalid candidate record')
            row['candidates'][match[1]] = match[2]
        elif detail.startswith('track='):
            match = re.fullmatch(r'track=(\d+) dt=(' + NUMBER + r') position=(' + NUMBER +
                                 r') (' + NUMBER + r') (' + NUMBER + r')', detail)
            if not match:
                raise ValueError('invalid projectile position record')
            row['tracks'].setdefault(match[1], []).append([float(x) for x in match.groups()[1:]])
        else:
            match = VECTOR.fullmatch(detail)
            if match:
                row['vectors'][match[1]] = [float(x) for x in match.groups()[1:]]
    return runs


def select_run(runs, version=None):
    matches = [r for r in runs if version is None or r['version'] == version]
    if not matches:
        raise ValueError('requested version has no recorded run: ' + str(version))
    run = matches[-1]  # do not fall back to a prior run if the newest is empty
    if not run['shots']:
        raise ValueError('newest matching run contains no weapon shots')
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--version')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run = select_run(parse_runs(args.log.read_text(encoding='utf-8', errors='replace')), args.version)
    result = dict(source=str(args.log.resolve()), **run)
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print('Saved %s: %d shots from %s' % (args.output, len(run['shots']), run['version']))


if __name__ == '__main__':
    main()
