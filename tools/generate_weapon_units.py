"""Regenerate player weapon root identities from an existing Filediver all.txt.

No game access or downloads. Example:
  python tools/generate_weapon_units.py path/to/all.txt --check
"""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HEADER = """-- Player weapon root kinds from the existing installed-game Filediver resource listing (2026-11-02).
-- Only primary_weapons, sidearm_weapons and support_weapons with directory == unit basename;
-- excludes magazines, hoses, attachments, projectiles and backpacks. Names/hashes are resource identities,
-- not copied game code. Filediver resource-list provenance is credited in THIRD_PARTY_NOTICES.txt.
-- Include unsupported weapons for held-weapon selection; this catalog does NOT enable their trajectories.
return [[
"""
PATTERN = re.compile(
    r'content/fac_helldivers/equipment/(?:primary_weapons|support_weapons|sidearm_weapons)/'
    r'([^/]+)/([^/]+)\.unit, 0x([0-9a-f]{16})\.'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('listing', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'src' / 'weapon_units.lua')
    parser.add_argument('--check', action='store_true', help='compare without writing')
    args = parser.parse_args()
    roots = {}
    for line in args.listing.read_text(encoding='utf-8').splitlines():
        match = PATTERN.match(line)
        if match and match[1] == match[2]:
            roots[match[3]] = match[1]
    if not roots:
        parser.error('no player weapon roots found; output left untouched')
    data = (HEADER + ''.join(kind + ' ' + name + '\n' for kind, name in sorted(roots.items())) + ']]\n').encode('utf-8')
    if args.check:
        if args.output.read_bytes() != data:
            parser.error('catalog differs from this listing; review before regenerating')
    else:
        args.output.write_bytes(data)
    print('%d player weapon roots; catalog %s' % (len(roots), 'verified' if args.check else 'written'))


if __name__ == '__main__':
    main()
