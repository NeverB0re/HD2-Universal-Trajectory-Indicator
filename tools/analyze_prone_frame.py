"""Replay test.11 prone weapon frames. No game queries, new fitting at runtime, or downloads.
GL-21 pitch is estimated from recorded height versus range with the existing projectile model.
GR-8 comparison is against camera direction only, not an observed projectile.
"""
import json
import math
from pathlib import Path
from fit_weapon_aim import loss, yaw

BASE = Path(__file__).resolve().parents[1]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(v):
    length = math.sqrt(dot(v, v))
    return [x / length for x in v]


def weapon_frame(row, bind):
    v = row['vectors']
    forward = unit(v['root-forward'])
    delta = [b-a for a, b in zip(v['root-position'], v['muzzle-position'])]
    along = dot(delta, forward)
    plane = [delta[i] - along * forward[i] for i in range(3)]
    perpendicular = math.sqrt(dot(plane, plane))
    if abs(along-bind[1]) >= .03 or abs(perpendicular-math.hypot(bind[0], bind[2])) >= .015:
        raise ValueError('locator differs from the rigid asset geometry')
    rotated = cross(forward, plane)
    up = unit([bind[2]*plane[i] - bind[0]*rotated[i] for i in range(3)])
    return forward, cross(forward, up), up


def direction(row, bind, local_angles):
    forward, right, up = weapon_frame(row, bind)
    a, b = map(math.radians, local_angles)
    d = [forward[i]*math.cos(a)*math.cos(b) + right[i]*math.sin(a)*math.cos(b) + up[i]*math.sin(b)
         for i in range(3)]
    heading = math.atan2(d[1], d[0])
    pitch = math.atan2(d[2], math.hypot(d[0], d[1])) + math.radians(.6)
    return [math.cos(pitch)*math.cos(heading), math.cos(pitch)*math.sin(heading), math.sin(pitch)]


def observed_gl(row):
    p = row['samples']
    start = p[0][2:]
    points = [(math.hypot(q[2]-start[0], q[3]-start[1]), q[4]-start[2]) for q in p[1:]]
    lo, hi = -30., 60.
    for _ in range(40):
        a, b = (2*lo+hi)/3, (lo+2*hi)/3
        if loss(a, points) < loss(b, points):
            hi = b
        else:
            lo = a
    pitch = math.radians((lo+hi)/2)
    heading = math.atan2(p[-1][3]-p[0][3], p[-1][2]-p[0][2])
    return [math.cos(pitch)*math.cos(heading), math.cos(pitch)*math.sin(heading), math.sin(pitch)]


def analyze():
    rows = json.loads((BASE/'tests/fixtures/weapon_direction_test11.json').read_text(encoding='utf-8'))['shots']
    assets = {r['kind']: r['muzzle']['position'] for r in
              json.loads((BASE/'tests/fixtures/weapon_muzzle_nodes.json').read_text(encoding='utf-8'))['rows']}
    out = []
    for n in ('1', '2', '3', '4', '5', '6'):
        row = rows[n]
        kind = row['header'].split('kind=')[1].split()[0]
        angles = (-1.85, -.75) if kind == '02eecd0b1fa49630' else (-1.28277, -1.54815)
        predicted = direction(row, assets[kind], angles)
        actual = observed_gl(row) if row['samples'] else unit(row['vectors']['camera-forward'])
        previous = unit(row['vectors']['predicted-velocity'])
        error = lambda d: abs((yaw(d)-yaw(actual)+180)%360-180)
        entry = dict(shot=n, reference='recorded GL-21 flight' if row['samples'] else 'camera ONLY',
                     old_yaw_error=error(previous), new_yaw_error=error(predicted))
        if row['samples']:
            angular = lambda d: math.degrees(math.acos(max(-1., min(1., dot(d, actual)))))
            entry.update(old_3d_error=angular(previous), new_3d_error=angular(predicted))
        out.append(entry)
    return out


if __name__ == '__main__':
    print(json.dumps(analyze(), indent=2))
