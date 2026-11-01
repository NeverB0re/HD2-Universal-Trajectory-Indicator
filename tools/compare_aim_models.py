"""Compare fixed-root and camera-target convergence against saved GL-21 flights.
Read-only analysis, no runtime imports, game queries, learning, or source changes.
A chosen distance is an approximation, not an actual engine aim target. Horizontal error only.
Usage: python tools/compare_aim_models.py --distance 100
"""
import argparse
import json
import math
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def direction_to(muzzle, target):
    delta = tuple(b - a for a, b in zip(muzzle, target))
    length = math.sqrt(sum(v * v for v in delta))
    if not math.isfinite(length) or length < 1e-6:
        return None
    return tuple(v / length for v in delta)


def yaw(v):
    return math.degrees(math.atan2(v[1], v[0]))


def compare(distance):
    groups = {}
    for filename in ('weapon_direction_test6.json', 'weapon_direction_test8.json', 'weapon_direction_test9.json'):
        rows = json.loads((BASE / 'tests/fixtures' / filename).read_text(encoding='utf-8'))['shots']
        for number, row in rows.items():
            samples, vectors = row['samples'], row['vectors']
            if 'kind=02eecd0b1fa49630' not in row['header'] or len(samples) < 2:
                continue
            first, last = samples[0][2:], samples[-1][2:]
            actual = yaw(tuple(b - a for a, b in zip(first, last)))
            camera, forward = vectors['camera-position'], vectors['camera-forward']
            target = tuple(c + distance * f for c, f in zip(camera, forward))
            candidate = direction_to(vectors['muzzle-position'], target)
            context = 'vehicle' if 'vehicle/' in row.get('applied_offset', '') else 'on-foot'
            height = float(row['header'].split('root-height=')[1])
            offset = 0 if context == 'vehicle' else (-1.84 if height < .5 else (-.13 if height < 1 else .06))
            models = {'fixed-root': yaw(vectors['root-forward']) - offset,
                      'camera-parallel': yaw(forward), 'muzzle-to-camera-target': yaw(candidate)}
            for model, predicted in models.items():
                error = abs((predicted - actual + 180) % 360 - 180)
                groups.setdefault((context, model), []).append(error)
    return [dict(context=context, model=model, count=len(errors),
                 mean_abs_yaw_deg=round(statistics.mean(errors), 6), max_abs_yaw_deg=round(max(errors), 6))
            for (context, model), errors in groups.items()]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distance', type=float, default=100)
    args = parser.parse_args()
    if not math.isfinite(args.distance) or args.distance <= 0:
        parser.error('distance must be positive and finite')
    print(json.dumps(dict(distance_assumption_m=args.distance, horizontal_only=True,
                         results=compare(args.distance)), indent=2))
