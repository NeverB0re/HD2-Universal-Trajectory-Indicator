"""Draw the mod's thumbnail, src/icon.png: a recoilless rifle's muzzle and the dashed arc coming out of it."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import png_rgba  # noqa: E402

SIZE, SCALE = 512, 4
BACK, GUN, ARC = (18, 22, 27), (236, 240, 232), (70, 235, 95)
ORIGIN, ANGLE = (82, 492), math.radians(60)   # the barrel, from its back at the picture's edge
LENGTH = 205                                  # to the muzzle's end
APEX_ALONG, ARC_END = 170, 290                # across the picture from the muzzle: to the arc's top, to its end
WIDTH, DASH, GAP = 11, 40, 28                 # the arc: half its width, a dash and a gap along it


def in_gun(x, y):
    """Is the point (in the picture's pixels) in the side view of the barrel?"""
    dx, dy = x - ORIGIN[0], y - ORIGIN[1]
    u = dx * math.cos(ANGLE) - dy * math.sin(ANGLE)
    v = abs(dx * math.sin(ANGLE) + dy * math.cos(ANGLE))
    if u < -40 or u > LENGTH:
        return False
    if u >= 150:                              # the flared muzzle
        return v <= 30 + (u - 150) * 0.34
    if 85 <= u <= 112:                        # the collar
        return v <= 40
    return v <= 26


def arc_mask():
    """The dashes, as round-ended strokes stamped along the arc: one byte per pixel at SCALE times the size."""
    n = SIZE * SCALE
    mask = bytearray(n * n)
    mx = ORIGIN[0] + (LENGTH + 18) * math.cos(ANGLE)
    my = ORIGIN[1] - (LENGTH + 18) * math.sin(ANGLE)
    slope, along, walked, last = math.tan(ANGLE), 0.0, 0.0, None
    r = WIDTH * SCALE
    while along <= ARC_END:
        x, y = mx + along, my - slope * along + slope * along * along / (2 * APEX_ALONG)
        if last:
            walked += math.hypot(x - last[0], y - last[1])
        last = (x, y)
        if walked % (DASH + GAP) < DASH:
            cx, cy = int(x * SCALE), int(y * SCALE)
            for j in range(-r, r + 1):
                row = cy + j
                if 0 <= row < n:
                    half = int(math.sqrt(r * r - j * j))
                    a, b = max(0, cx - half), min(n, cx + half + 1)
                    if a < b:
                        mask[row * n + a:row * n + b] = b"\1" * (b - a)
        along += 0.25
    return mask


def main():
    n = SIZE * SCALE
    arc = arc_mask()
    rows = []
    for py in range(SIZE):
        row = []
        for px in range(SIZE):
            gun = drawn = 0
            for sy in range(SCALE):
                for sx in range(SCALE):
                    if arc[(py * SCALE + sy) * n + px * SCALE + sx]:
                        drawn += 1
                    elif in_gun(px + (sx + .5) / SCALE, py + (sy + .5) / SCALE):
                        gun += 1
            total = SCALE * SCALE
            rest = total - gun - drawn
            row.append(tuple(int((GUN[i] * gun + ARC[i] * drawn + BACK[i] * rest) / total + .5) for i in range(3)) + (255,))
        rows.append(row)
    png_rgba.write(os.path.join(HERE, "..", "src", "icon.png"), rows)


if __name__ == "__main__":
    main()
