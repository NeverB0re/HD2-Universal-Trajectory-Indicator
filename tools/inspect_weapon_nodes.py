"""Read muzzle/sight facts from locally extracted unit main files, without running the game.

Input root contains targets.json and units/<resource>.unit.main from Filediver.
Joint-list layout: https://github.com/xypwn/filediver/blob/21ae4cb7c6293ecb98f4a69ad225d35823439045/stingray/unit/unit.go
Hash convention: https://github.com/xypwn/filediver/blob/21ae4cb7c6293ecb98f4a69ad225d35823439045/stingray/hash.go
The reader uses Filediver's published format findings (BSD-3-Clause; see THIRD_PARTY_NOTICES.txt).
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

SPEC = importlib.util.spec_from_file_location('arc_build', Path(__file__).resolve().parents[1] / 'build.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def inspect(root, game_build):
    rows = []
    for target in json.loads((root / 'targets.json').read_text(encoding='utf-8')):
        asset = target['path'].removesuffix('.bones') + '.unit.main'
        raw = (root / 'units' / asset).read_bytes()
        offset = struct.unpack_from('<I', raw, 52)[0]
        count = struct.unpack_from('<I', raw, offset)[0]
        if not 1 <= count <= 4096 or offset + 16 + count * 136 > len(raw):
            raise ValueError('Review changed joint layout: ' + asset)
        hashes = struct.unpack_from('<' + 'I' * count, raw, offset + 16 + 132 * count)

        def node(name):
            h = BUILD.murmur64(name.encode()) >> 32
            if h not in hashes:
                return None
            i = hashes.index(h)
            matrix = struct.unpack_from('<16f', raw, offset + 16 + 64 * count + 64 * i)
            return {'index': i + 1, 'position': list(matrix[12:15]), 'forward': list(matrix[4:7])}

        name = 'attach_muzzle' if node('attach_muzzle') else 'muzzle'
        muzzle, sight = node(name), node('sight')
        if not muzzle or not sight:
            raise ValueError('Review missing muzzle/sight: ' + asset)
        rows.append({'kind': target['kind'], 'asset': asset, 'sha256': hashlib.sha256(raw).hexdigest(),
                     'node': name, 'muzzle': muzzle, 'sight': sight})
    if len(rows) != 16:
        raise ValueError('Review changed supported roster')
    return {'game_build': game_build, 'runtime_indices': 'resolved by name; indices below are evidence only',
            'rows': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-root', required=True, type=Path)
    parser.add_argument('--game-build', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.research_root, args.game_build), indent=2) + '\n',
                           encoding='utf-8', newline='\n')
    print('wrote', args.output)
