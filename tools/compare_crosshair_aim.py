"""Offline: do tracked rounds fly from the muzzle to a point on the camera ray? Never imported by the game.

For each recorded flight: the launch direction (heading from the track, pitch fitted with the weapon's own speed,
gravity and drag, height against range), then the angle to each direction model. "best distance" gives each flight the
one distance along the camera ray that fits it best: a single number against two angles, so a small residual means the
family is right. Usage: python tools/compare_crosshair_aim.py [--flights]
"""
import argparse
import json
import math
import statistics
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / 'tests/fixtures'
SOURCES = ('6', '8', '9', '11', '14', '15')
# weapon kind: round kind, speed, gravity factor, drag term, name
WEAPONS = {
    '02eecd0b1fa49630': ('a6cd8a90185b6567', 100., 1., 38.4, 'GL-21'),
    '9f80d67a12a7e40f': ('4fd8795ed60f5579', 250., 1., .657, 'GR-8'),
    'f49227a0630a3f7f': ('8f063c5d3929316e', 100., .5, 2.25, 'CB-9'),
    'e91f569c2ad8af01': ('ccf18b6315a3d67f', 100., 1., 0., 'P-34'),
}


def unit(a):
    n = math.sqrt(sum(x * x for x in a))
    return [x / n for x in a]


def angle(a, b):
    return math.degrees(math.acos(max(-1., min(1., sum(x * y for x, y in zip(unit(a), unit(b)))))))


def launch(samples, muzzle, speed, gravity, drag):
    heading = math.atan2(samples[-1][2] - samples[0][2], samples[-1][1] - samples[0][1])
    hx, hy = math.cos(heading), math.sin(heading)
    points = [((s[1] - muzzle[0]) * hx + (s[2] - muzzle[1]) * hy, s[3] - muzzle[2]) for s in samples]

    def loss(pitch):
        a = math.radians(pitch)
        vx, vz = speed * math.cos(a), speed * math.sin(a)
        x = z = 0.
        i, errors, dt = 0, [], 1 / 120
        for _ in range(720):
            d = 4.7e-4 * drag * math.hypot(vx, vz) * dt
            vx, vz = vx * (1 - d), vz * (1 - d) - 9.81 * gravity * dt
            nx, nz = x + vx * dt, z + vz * dt
            while i < len(points) and points[i][0] <= nx:
                if points[i][0] >= x:
                    errors.append(points[i][1] - (z + (nz - z) * (points[i][0] - x) / (nx - x)))
                i += 1
            if i == len(points):
                break
            x, z = nx, nz
        if len(errors) < 2:
            return float('inf')
        mean = sum(errors) / len(errors)       # the height of the start is free, not forced to the muzzle's
        return sum((e - mean) ** 2 for e in errors)

    lo, hi = -80., 80.
    for _ in range(60):
        a, b = (2 * lo + hi) / 3, (lo + 2 * hi) / 3
        if loss(a) < loss(b):
            hi = b
        else:
            lo = a
    pitch = math.radians((lo + hi) / 2)
    return [math.cos(pitch) * hx, math.cos(pitch) * hy, math.sin(pitch)], points[-1][0]


def flights():
    for source in SOURCES:
        shots = json.loads((FIXTURES / f'weapon_direction_test{source}.json').read_text(encoding='utf-8'))['shots']
        for number, row in shots.items():
            kind = row['header'].split('kind=')[1].split()[0]
            weapon = WEAPONS.get(kind)
            if not weapon:
                continue
            if 'tracks' in row:
                tracks = [row['tracks'][c] for c, r in row['candidates'].items() if r == weapon[0]]
                samples = next((t for t in tracks if len(t) >= 3), None)
            else:
                samples = [s[1:] for s in row['samples']] if len(row['samples']) >= 3 else None
            if not samples or math.hypot(samples[-1][1] - samples[0][1], samples[-1][2] - samples[0][2]) < 3:
                continue
            v = row['vectors']
            actual, span = launch(samples, v['muzzle-position'], *weapon[1:4])
            yield dict(source=source, number=number, name=weapon[4], vectors=v, actual=actual, span=span,
                       height=float(row['header'].split('root-height=')[1].split()[0]),
                       moving=math.hypot(*v['player-velocity'][:2]))


def toward(v, distance):
    c, f, m = v['camera-position'], v['camera-forward'], v['muzzle-position']
    return [c[i] + distance * f[i] - m[i] for i in range(3)]


def best_distance(row):
    grid = [3 * 1.04 ** i for i in range(180)] + [1e7]
    return min((angle(toward(row['vectors'], d), row['actual']), d) for d in grid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flights', action='store_true', help='one line per flight')
    args = parser.parse_args()
    rows = list(flights())
    groups = {'all': lambda r: True, 'prone (<0.6 m)': lambda r: r['height'] < .6, 'others': lambda r: r['height'] >= .6}
    models = {'barrel': lambda r: r['vectors']['root-forward'],
              'drawn at the time': lambda r: r['vectors']['predicted-velocity'],
              'camera, parallel': lambda r: r['vectors']['camera-forward']}
    for distance in (50, 100, 200):
        models[f'crosshair at {distance} m'] = lambda r, d=distance: toward(r['vectors'], d)
    models['crosshair, best distance'] = lambda r: toward(r['vectors'], best_distance(r)[1])
    print('degrees off the launch direction: mean / max')
    print(f"{'':26}" + ''.join(f'{g:>22}' for g in groups))
    for name, model in models.items():
        cells = []
        for keep in groups.values():
            errors = [angle(model(r), r['actual']) for r in rows if keep(r)]
            cells.append(f'{statistics.mean(errors):8.2f} /{max(errors):6.2f} ({len(errors):2})')
        print(f'{name:26}' + ''.join(f'{c:>22}' for c in cells))
    if args.flights:
        for r in rows:
            residual, distance = best_distance(r)
            print(f"test.{r['source']:>2} shot {r['number']:>2} {r['name']:5} height {r['height']:.2f} moving {r['moving']:.1f}"
                  f" | barrel {angle(r['vectors']['root-forward'], r['actual']):5.2f}"
                  f" camera {angle(r['vectors']['camera-forward'], r['actual']):5.2f}"
                  f" | best {distance if distance < 1e6 else float('inf'):7.1f} m residual {residual:.2f}")


if __name__ == '__main__':
    main()
