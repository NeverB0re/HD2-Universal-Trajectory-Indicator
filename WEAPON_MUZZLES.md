# Weapon muzzle and prone work: test.5

2026-11-01. Based on local installed Steam build 26251122. The user reports grenade arcs fit well after test.4;
this milestone changes weapon selection/origin/view classification only. Grenade fitting and saved calibration are unchanged.

## Evidence before implementation

- The old Weapon Probe log already confirmed live `attach_muzzle` nodes on GL-21, GL-52, GP-20, P-34 and CB-9, and
  `muzzle` on RL-77. The implementation still used an approximate 0.45m forward offset from the weapon root.
- Existing Filediver was used to extract local unit/bone metadata. No new mod or data download was needed, and no
  game file was changed. The full unit joint lists, unlike the smaller animated-bone name lists, contain muzzle
  attachment locators.
- All 16 supported units have a muzzle locator and `sight`. The parser's one-based indices agree with the six
  previously observed runtime indices. The implementation resolves names through `chef.unit_node`; these indices
  are not hardcoded into runtime Lua.
- [Filediver unit layout](https://github.com/xypwn/filediver/blob/21ae4cb7c6293ecb98f4a69ad225d35823439045/stingray/unit/unit.go) and
  [hash convention](https://github.com/xypwn/filediver/blob/21ae4cb7c6293ecb98f4a69ad225d35823439045/stingray/hash.go) describe the static reader.
  Its BSD-3-Clause notice is included in `THIRD_PARTY_NOTICES.txt` and the test ZIP.

| Weapon | Muzzle node | Installed one-based joint index (evidence only) |
| --- | --- | ---: |
| GL-21 | attach_muzzle | 22 |
| GL-52 | attach_muzzle | 41 |
| GL-28 | attach_muzzle | 26 |
| GL-15 | attach_muzzle | 23 |
| GP-31 | attach_muzzle | 21 |
| GP-20 | attach_muzzle | 20 |
| P-34 | attach_muzzle | 28 |
| CB-9 | attach_muzzle | 34 |
| SG-8P | attach_muzzle | 31 |
| RL-77 | muzzle | 35 |
| GR-8 | muzzle | 26 |
| EAT-17 | muzzle | 17 |
| EAT-700 | muzzle | 26 |
| EAT-411 | muzzle | 23 |
| PLAS-45 | attach_muzzle | 24 |
| AR/GL-21 | attach_muzzle | 23 |

Examples of muzzle bind position (forward, up from root): GL-21 (0.438, 0.096)m, GP-20 (0.211, 0.081)m,
PLAS-45 (0.441, 0.184)m. The old common offset (0.45, 0)m was too low or too far forward for these examples;
PLAS-45's special fallback (0.8, 0.12)m was especially far forward. These are bind-pose facts, not runtime shot measurements.

## Implemented behavior

- Draw from the live animated muzzle node's world position, including lowered/prone and rolled weapon poses.
- Keep the old offsets only as a logged compatibility fallback when the node is missing or its position is invalid.
- Remove the explicit suppression based on weapon height below 0.6m. It was not an actual stance detector.
- Strong hand proximity can select a weapon whose barrel lags the camera while prone. Prefer the closest supported
  root actually at the hand over a slung candidate; retain alignment-based selection when the hand is unavailable.
- Keep the existing weapon direction, movement, drag and lifetime model. The inspected muzzle locators have the same
  local forward axis as the root, so no unverified node-direction rotation or new ballistic constants were introduced.
- Retain first-person hiding. For a camera already near the weapon root, use its proximity to `sight` (0.35m) to
  distinguish a sight camera from close prone third person. Missing sight data keeps the old 0.9m root fallback.
  This remains a geometry heuristic, not a confirmed engine camera-mode API, and needs the targeted live check.
- Cache node indices per unit/world; retry missing nodes only every five seconds. Read animated positions live.
  No additional world scan or per-frame node-name search was added.

## Reproduction and verification

`tools/inspect_weapon_nodes.py` reads the extracted main files and emits `tests/fixtures/weapon_muzzle_nodes.json`,
including per-asset hashes, locator positions and indices. It is a development reader, not a runtime dependency.
The fixture drives parameterized fake-loader checks for all 16 supported weapon names/positions, including the
One-Two's fire-mode gate. All 119 main Lua 5.1 tests pass, including prior grenade recorded-flight regression tests.
Additional checks cover prone display, a steep camera/barrel difference at the hand, first-person hiding, close
prone third person, animated movement, invalid-node fallback, cached name lookup and changed-world node indices.

Static node presence and fake-loader tests do not prove shot accuracy, visible model alignment, performance or
camera classification in the game. The One-Two's underbarrel alignment and individual unusual weapon animations
remain candidates for later coverage checks; no new shooting survey is requested just to establish their node names.

## Focused runtime check

Use one already-equipped supported weapon (for example GL-21): aim standing, crouched and prone; move the view
up/down and left/right, then switch between first and third person. Confirm the line begins at the visible muzzle,
stays available prone in third person, and stays hidden in first person. Compare one standing and one prone shot
when practical to determine whether the existing direction model also needs stance-specific work. No new probe,
weapon unlock or extra mod download is required. Report the weapon and any remaining origin/direction/missing-line
issue; `throwable_arcs.log` names the selected muzzle node or the compatibility fallback.

Test.5 has not been run in game and is not a stable release. No remote push is authorized by offline checks alone.
