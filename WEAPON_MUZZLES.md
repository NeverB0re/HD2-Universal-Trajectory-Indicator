# Weapon muzzle and prone work: test.5 through test.7

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

## Runtime result and test.6 direction evidence

The user confirmed on 2026-11-01 that test.5 starts at the visible muzzle and displays while prone. However, the
arc now lies left of actual fire, with greater disagreement standing/crouched than prone. Test.5 is not stable.
The direction formula itself was unchanged, but that does not establish that its root/camera correction remains
valid with the selected unit and animated origin. Static node axes do not establish their runtime rotation.
The existing old Weapon Probe log records muzzle and root directions plus earlier projectiles, but does not
measure this test.5 regression. Current throwable_arcs.log has no corresponding weapon shot vectors.

Test.6 preserves test.5 geometry and ballistics and adds passive, bounded evidence only. For the first nine trigger
presses while a supported third-person weapon arc is drawn, it logs camera/root/muzzle vectors, root height above
feet, the active learned yaw/pitch offsets, player movement and the exact predicted initial velocity. The muzzle
forward read uses the same loader node-rotation API already used by Weapon Probe. It does not calibrate to it.

A paused loader watch resumes for 0.35 seconds after a logged shot, listing known projectile kinds every 0.05s.
It logs up to three nearby candidate units and their positions every 0.02s; it then pauses again. Existing watch
items are excluded. A candidate is explicitly unverified: another player, an old round appearing on refresh, or
multiple rounds can confound association. Only a continuous flight consistent with this shot should be analyzed.
No projectile observation changes calibration or a displayed arc. There is no new direct world scan or download.

Known traceable pairs are GL-21/GL-52, GP-20, CB-9, P-34 and RL-77, from existing Weapon Probe evidence. Other
weapons still log vectors but have no presumed projectile mapping; Epoch's projectile was not a unit in earlier
measurements. Prefer GL-21 or GP-20 for this focused test, since the user already used those weapons.

Use one such weapon, stationary, in third person, aiming at a distant fixed surface. Wait about one second after
each stance/aim change and fire two single shots standing, two crouched, two prone. Keep the same aim point when
practical. No extra weapon survey or grenade test is needed. After exiting, analyze the existing
`%APPDATA%\Arrowhead\Helldivers2\throwable_arcs.log`. If no candidate flight was observed, vector records alone
must not be represented as projectile accuracy evidence.

All 124 Lua 5.1 tests pass, including bounded diagnostic activation, session budget, world-change cancellation,
recording distinct root/node rotations, and unchanged drawn arcs. No test.6 real-game run or remote push.


## Test.7: bounded yaw relearning after stance changes

The user ran test.6 and reported standing/crouched alignment but prone disagreement. The 12:27 session contains
nine sampled shots: GP-20 shots 1-2, GL-21 shots 3-9. The later 12:36 restart has no samples; do not select the
last version banner blindly when analyzing the log. Original measured vectors/positions are preserved in
`tests/fixtures/weapon_direction_test6.json`. The root height groups agree with the user's stance sequence, but
runtime code does not classify stance from this height.

All seven GL-21 flights have a single candidate originating within 0.6-1.6cm of the sampled muzzle, followed by
continuous outward flight. Root and muzzle forward vectors agree. Thus switching to muzzle rotation would not
correct this measured yaw error. Horizontal flight direction is measured from first-to-last observed XY positions;
it does not depend on fitting gravity, speed, drag or release time.

| GL-21 shots | Height group | Actual minus camera yaw | Original predicted minus actual yaw |
| --- | --- | --- | --- |
| 3, 4, 9 | standing | -0.109, -0.225, +0.044 deg | +0.101, +0.221, -0.067 deg |
| 5, 6 | crouched | +0.031, -0.321 deg | -0.323, +0.150 deg |
| 7, 8 | prone | -0.079, -0.262 deg | -1.301, -1.673 deg |

Prone root-minus-camera yaw is -1.722 / -2.277 degrees. The cached yaw offset remained at -0.342 degrees for both
shots: the previous one-degree joint yaw/pitch acceptance test rejected the new difference. This also froze pitch
learning when yaw was out of range. GP-20 shot 1 shows the reciprocal problem: its outlying pitch difference
prevented yaw learning. GP-20 shot 2 was moving (about 2.1m/s); do not treat it as stationary stance evidence.

Changes in test.7:

- Learn stationary yaw independently of the existing pitch gate, inside an absolute +/-3 degree root/camera yaw
  envelope. This accommodates the observed 2.28 degree difference plus margin. It does not label every barrel
  deflection as a stance offset. Larger differences retain the previous correction, preserving the recorded
  near-corner 5.3 degree case; unlike a gate relative to the last learned value, the envelope cannot drift there.
- Retain root-following while turning and the existing 0.5 second camera/weapon settling requirement. Do not
  force the arc onto the camera during aim lag. Changing pose needs settling/relearning, about two seconds in
  the verification below. The boundary remains heuristic; unobserved weapons/poses can exceed it.
- Keep pitch's one-degree acceptance rule and all launch lift, speed, movement, drag, lifetime and origin math.
  Separate yaw/pitch acceptance allows one valid component to learn while the other is rejected. No new vertical
  ballistic fit is claimed from these horizontal comparisons.
- Scale smoothing with elapsed time (same response as 0.05/frame at 60Hz) and reset the stillness timer when the
  unit/world changes or updates are interrupted. This prevents performance-dependent settling or carrying a
  previous weapon's stillness timer into a newly selected unit.
- Retain the bounded passive diagnostic recorder for the focused test. It does not auto-calibrate to candidates.

Verification: all 128 Lua 5.1 tests pass. Replaying shots 3-9 in order, holding each captured aim for two seconds,
produces horizontal errors +0.066, +0.182, -0.073, +0.279, +0.040, +0.226, -0.061 degrees. Restoring only the old
`weapon_aim` function in memory makes the two prone regression cases fail. Additional checks cover independent
yaw learning, 30/60/120Hz settling, the large corner case after a prone correction, and existing dynamic aim lag.
This replay establishes the stationary horizontal correction on these captured inputs, not actual in-game
accuracy after installation, vertical accuracy or all-weapon coverage.

Next live check: GL-21 first, stationary third person, wait about two seconds after each stance change, then two
single shots each standing/crouched/prone. Also note whether the arc retains the correct origin while changing
stance. No grenade retest or new weapon unlock is required. Test.7 is a local test build; no remote push.
