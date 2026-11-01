"""Offline GL-21 fixed-profile evidence; never imported by the game. Run with Python 3.
Uses horizontal range instead of engine timestamps, avoiding unknown spawn/observation delay.
Fits launch pitch with the existing 120Hz gravity/drag model; speed/drag are held fixed.
The first two test.8 shots have large root/projectile disagreement and are excluded explicitly,
not claimed fixed. They need synchronized aim/release evidence before a motion model is fitted.
"""
import json
import math
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SELECT = {"weapon_direction_test6.json": [3, 4, 5, 6, 7, 8, 9],
          "weapon_direction_test8.json": [3, 4, 5, 6, 7, 8, 9]}


def yaw(v):
    return math.degrees(math.atan2(v[1], v[0]))


def pitch(v):
    return math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))


def loss(angle, points):
    a = math.radians(angle)
    vx, vz, x, z, i, errors = 100 * math.cos(a), 100 * math.sin(a), 0., 0., 0, []
    dt = 1 / 120
    for _ in range(720):
        drag = .00047 * 38.4 * math.hypot(vx, vz) * dt
        vx, vz = vx * (1 - drag), vz * (1 - drag) - 9.81 * dt
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


def analyze():
    rows, groups = [], {k: [] for k in ('low-root', 'mid-root', 'high-root')}
    for filename, numbers in SELECT.items():
        source = json.loads((BASE / 'tests/fixtures' / filename).read_text(encoding='utf-8'))['shots']
        for number in numbers:
            row = source[str(number)]
            samples, vectors = row['samples'], row['vectors']
            origin, end = samples[0][2:], samples[-1][2:]
            points = [(math.hypot(p[2] - origin[0], p[3] - origin[1]), p[4] - origin[2]) for p in samples[1:]]
            lo, hi = -30., 60.
            for _ in range(40):
                a, b = (2 * lo + hi) / 3, (lo + 2 * hi) / 3
                if loss(a, points) < loss(b, points):
                    hi = b
                else:
                    lo = a
            fitted = (lo + hi) / 2
            actual_yaw = yaw([b - a for a, b in zip(origin, end)])
            yaw_off = (yaw(vectors['root-forward']) - actual_yaw + 180) % 360 - 180
            pitch_off = pitch(vectors['root-forward']) - fitted + .6
            height = float(row['header'].split('root-height=')[1])
            group = 'low-root' if height < .5 else ('mid-root' if height < 1 else 'high-root')
            result = dict(source=filename, shot=number, group=group, yaw=yaw_off, pitch=pitch_off,
                          vertical_rms=math.sqrt(loss(fitted, points)))
            groups[group].append(result)
            rows.append(result)
    return dict(measurements=rows, profiles={name: dict(count=len(rs),
                yaw=round(statistics.median(r['yaw'] for r in rs), 2),
                pitch=round(statistics.median(r['pitch'] for r in rs), 2)) for name, rs in groups.items()})


if __name__ == '__main__':
    print(json.dumps(analyze(), indent=2))
