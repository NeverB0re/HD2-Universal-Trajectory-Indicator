"""Offline test.14 replay. No game reads or runtime fitting.

Fit elevation against range, not wall-clock time: discovery/render delay is unknown.
Keep each weapon's existing speed, gravity and drag fixed. A kind/speed match is
correlation evidence, not an engine-provided shooter/projectile identity.
"""
import argparse
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MODELS = {
    '9f80d67a12a7e40f': ('4fd8795ed60f5579', 250., 1., .657),
    'f49227a0630a3f7f': ('8f063c5d3929316e', 100., .5, 2.25),
}


def angles(v):
    return math.degrees(math.atan2(v[1], v[0])), math.degrees(math.atan2(v[2], math.hypot(*v[:2])))


def elevation_loss(angle, points, speed, gravity, drag_coefficient):
    a = math.radians(angle)
    vx, vz = speed * math.cos(a), speed * math.sin(a)
    x = z = 0.
    i, errors, dt = 0, [], 1 / 120
    for _ in range(720):
        drag = .00047 * drag_coefficient * math.hypot(vx, vz) * dt
        vx, vz = vx * (1 - drag), vz * (1 - drag) - 9.81 * gravity * dt
        nx, nz = x + vx * dt, z + vz * dt
        while i < len(points) and points[i][0] <= nx:
            distance, actual = points[i]
            predicted = z + (nz - z) * (distance - x) / (nx - x)
            errors.append((predicted - actual) ** 2)
            i += 1
        if i == len(points):
            return sum(errors) / len(errors)
        x, z = nx, nz
    return float('inf')


def fit(samples, model):
    start, end = samples[0][1:], samples[-1][1:]
    points = [(math.hypot(p[1] - start[0], p[2] - start[1]), p[3] - start[2]) for p in samples[1:]]
    lo, hi = -80., 80.
    for _ in range(60):
        a, b = (2 * lo + hi) / 3, (lo + 2 * hi) / 3
        if elevation_loss(a, points, *model[1:]) < elevation_loss(b, points, *model[1:]):
            hi = b
        else:
            lo = a
    pitch = (lo + hi) / 2
    return dict(yaw_deg=angles([b - a for a, b in zip(start, end)])[0],
                pitch_deg=pitch, vertical_rms_m=math.sqrt(elevation_loss(pitch, points, *model[1:])))


def analyze(path=None):
    path = Path(path) if path else BASE / 'tests/fixtures/weapon_direction_test14.json'
    shots = json.loads(path.read_text(encoding='utf-8'))['shots']
    results = []
    for number, row in shots.items():
        kind = row['header'].split('kind=')[1].split()[0]
        model = MODELS.get(kind)
        if not model:
            continue
        for candidate, resource in row['candidates'].items():
            if resource != model[0]:
                continue
            samples = row['tracks'][candidate]
            if len(samples) < 3:
                continue
            observed = fit(samples, model)
            root, predicted = [angles(row['vectors'][k]) for k in ('root-forward', 'predicted-velocity')]
            wrap = lambda a: (a + 180) % 360 - 180
            # Compare ALL poses, not just the one with minimum error. A best-matching pose is
            # not automatically the engine's firing pose; later snapshots can include recoil.
            comparisons = []
            poses = [('pre-shot', p) for p in row.get('pre_shot', [])]
            poses += [('sync', p) for p in row.get('sync', [])]
            for label, p in poses:
                heading, elevation = angles(p['forward'])
                comparisons.append(dict(label=label, dt=p['dt'],
                    root_yaw_error_deg=wrap(heading-observed['yaw_deg']),
                    root_pitch_minus_flight_deg=elevation-observed['pitch_deg'],
                    muzzle_to_first_position_m=math.dist(p['muzzle'], samples[0][1:])))
            observed.update(shot=number, kind=kind, candidate_kind=resource, samples=len(samples),
                root_height_m=float(row['header'].split('root-height=')[1]),
                root_yaw_error_deg=wrap(root[0] - observed['yaw_deg']),
                displayed_yaw_error_deg=wrap(predicted[0] - observed['yaw_deg']),
                displayed_pitch_error_deg=predicted[1] - observed['pitch_deg'],
                first_seen_to_click_muzzle_m=math.dist(samples[0][1:], row['vectors']['muzzle-position']),
                first_seen_delay_s=samples[0][0],
                stationary_click=math.hypot(*row['vectors']['player-velocity'][:2]) < .1,
                pose_comparisons=comparisons,
                caveat='pitch at first observation, nominal speed/drag held fixed; not a universal calibration')
            results.append(observed)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='JSON exported by capture_weapon_trace.py')
    args = parser.parse_args()
    print(json.dumps(analyze(args.input), indent=2))
