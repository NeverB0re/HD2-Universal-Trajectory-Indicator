# Weapon muzzle and prone work: test.5 through test.13

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


## Test.8: vehicle aim eligibility evidence (not a vehicle fix)

The user reports inaccurate passenger weapon arcs even with the vehicle stationary, and arcs in the driver's seat
on right-click although the character cannot actually lean out and aim/fire. This requires more than speed carry
changes. Current weapon eligibility only checks aim input, held-unit proximity/alignment and camera mode. The
existing `in_vehicle` function is a geometry heuristic for C4/icon behavior, not a seat identity or firing permission
API. It must not be used to claim a confirmed driver/passenger role. Passenger arcs must remain available.

Search of the local NarrowHUD and Chef loader sources did not yield a verified seat/firing-state reader. Public
HD2Runtime vehicle authoring documentation likewise does not promote seat components:
https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/docs/vehicle-authoring.md
This is a limitation of the inspected sources, not proof that no native reader exists. No new source download,
unsafe native probing or guessed animation enum has been introduced.

Test.8 includes test.7's on-foot yaw correction and adds bounded passive snapshots during a nearby vehicle aim
entry and 0.7 seconds later. Up to 16 snapshots per load record camera/feet/right-hand/selected-weapon geometry
and existing avatar animation variables `character_state`, `steering_turn`, `gunner_traverse`, `move_speed`,
`aim_horizontal`, `aim_vertical`. Variable presence is checked through the same player-kind guarded API already
used for `weapon_selected`; indices are cached with five-second missing retries. Missing values are logged as
missing, not treated as a driver flag. There is no new watch or world scan and no change to aim eligibility.
Lua 5.1's 200-local chunk limit requires storing this helper on the existing diagnostic table.

Vehicle diagnostic labels explicitly say proximity is not confirmed membership. Snapshots do not themselves
establish seat semantics or firing permission. Analyze alongside the user's known seat sequence and the bounded
projectile records already in test.6/7 before implementing any seat gate or separate passenger direction model.

Focused check with a supported weapon already owned (CB-9/GL-21/GP-20): stopped vehicle, driver right-click held
about one second, release; switch to passenger, aim about two seconds and fire two single shots. Driver requires
no firing. Note whether shots/line agree and which weapon was used. No moving-vehicle test is needed yet.
Test.8 already includes test.7; it does not require installing two builds. Vehicle correction remains unresolved.
All 131 offline Lua 5.1 tests pass, including idle-on-foot, no-fire entry/settled snapshots, bounded logging,
preserved passenger arcs and idle projectile scanning. No remote push or in-game test.8 accuracy claim.


## Test.9: fixed profiles supersede live weapon-angle learning

The user reports gradual convergence during passenger aim and again after dismounting, and requests fixed
weapon/context values after observations. Code confirms the earlier learned offset was keyed only by weapon
kind, so vehicle and on-foot observations could overwrite the same correction. Test.9 removes that live weapon
angle learner and its timers/history entirely. The grenade flight fitter is unchanged; this change concerns
weapon aiming offsets, not live camera/muzzle/movement/physics updates.

`weapon_profile` now chooses immutable yaw/pitch degrees. The measured GL-21 groups use root height above the
tracked player's feet: below 0.5m, 0.5-1.0m, and at least 1.0m. These are geometry groups supported by these logs,
not a verified native stance enum; unusual aim elevations, ramps or animation transitions can cross a boundary.
Profile selection happens immediately. There is no waiting for alignment with the camera and no saved learned
weapon offset. Actual weapon heading remains live, preserving aim lag and corner deflections.

| GL-21 geometry group | Yaw offset | Pitch offset (before existing +0.6deg launch lift) | Recorded flights |
| --- | ---: | ---: | ---: |
| low root (prone observations) | -1.84deg | 0.75deg | 5 |
| mid root (crouched observations) | -0.13deg | 0.95deg | 3 |
| high root (standing observations) | +0.06deg | 1.17deg | 6 |

`tools/fit_weapon_aim.py` reproduces these offline medians from test.6 and test.8 raw flight fixtures. Horizontal
heading comes directly from observed XY displacement. Vertical pitch is fitted against height versus horizontal
range using the existing 100m/s, drag and 120Hz gravity model, avoiding unmeasured release/frame timestamp delay.
The existing launch lift is included when converting fitted pitch into the stored correction. No engine speed,
drag, gravity, lifetime or movement constants are refitted.

The first two test.8 GL-21 shots differ greatly between sampled root direction and observed projectile direction
(2.7/4.5deg horizontally, approximately 9.8/11.8deg in the corresponding pitch correction). They are explicitly
excluded from fixed-profile fitting, not claimed solved. Current records cannot distinguish aim turning/settling
between input and release from other aim state effects. The fixed profiles fit the other captured geometry;
accuracy during rapid aim changes remains a separate required check.

Other weapons retain the previous unmeasured fixed default (0deg yaw, 1.5deg pitch). Elevated vehicle geometry
selects a separate unmeasured vehicle default with those same numbers, never a GL-21 on-foot profile. No vehicle
projectile was captured in this session: all nine shot samples were spent before boarding. Thus a passenger
correction must not be invented from these weapon/hand snapshots alone. Geometry classification still uses the
existing vehicle proximity heuristic plus feet at least 0.35m above the vehicle root. It is not authoritative
seat membership, and standing on a vehicle/tilted terrain remain limits.

The user confirmed passenger shooting first, then repeated driver right-click tests; death occurred in the front
passenger seat. Snapshots 9-13 show the fixed driver hand/root height near 0.463m while camera directions change.
Settled passenger snapshots 2/4/6 show 1.08-1.15m; 14/15 are excluded from normal calibration because of the later
passenger/death context. `character_state=3`, steering and gunner values occur in both seats, so none is used as
a driver enum. FRV-family weapon arcs now require the weapon root to rise at least 0.7m above feet when vehicle
geometry is elevated. This hides the measured driver pose and lowered passenger entry pose, without changing
C4 eligibility. The gate is a measured pose heuristic, not a universal driver-seat API; tilted/other seats need
coverage. Only the known FRV / heavy-FRV kinds are gated (local resource list names confirm these hashes).
Ground-level prone soldiers near the vehicle are excluded from this gate.

Recorder budgets now allow three shots per weapon/profile, with a global cap of 16. One weapon can use at most
nine shots across its three on-foot groups, leaving capacity for its passenger profile. Trying many weapons can
still exhaust the global cap, so the focused check should use one weapon. Logs include the selected fixed profile. The 0.35s bounded watch window
is retained only as passive development evidence and never feeds a displayed correction. No new download,
continuous world scan or persistent weapon calibration is introduced.

Verification: 138 Lua 5.1 tests pass. Captured stable GL-21 inputs are checked from the first frame against actual
horizontal flight and early-flight height (within 0.25m vertically for all 14 selected recorded flights). Tests
also cover unchanged lines with time/FPS, immediate geometry-profile switches, immediate return to the identical
on-foot path after dismount, large corner deflection, recorded driver/passenger poses, prone beside a grounded
FRV, context/global recording budgets, and existing grenade/C4/stratagem behavior. These are replay/fake-loader
checks; test.9 has not been tested in game, and neither all-weapon accuracy nor moving-vehicle accuracy is proven.

Next minimal check: install only test.9. Stopped FRV driver right-click should hide the weapon arc; passenger
GL-52/CB-9/GL-21 may then fire two single shots after raising the weapon. Use the same weapon after dismounting
and compare immediately versus several seconds later while keeping the actual aim/weapon pose unchanged.
There is no calibration wait requirement. State which weapon was used and whether the line/impact shifts;
passenger accuracy is still pending the first captured passenger rounds. No remote push.


## Test.10: supply FRV coverage and estimated GR-8 low-root yaw

User confirms GL trajectories fit in test.9, driver arcs persist in a **supply FRV**, and GR-8 agrees standing /
crouched but is laterally displaced prone. Keep GL-21 profiles and the fixed, non-learning architecture unchanged.
Raw test.9 records are preserved in `tests/fixtures/weapon_direction_test9.json`.

The driver guard only listed the regular FRV and flamer FRV. The supply FRV (`9b2140378640432e`) was watched but
omitted from the guard. The installed resource list maps it to `vehicles/frv_supply/frv_supply.unit`. Add this
third FRV kind to the existing raised-weapon check. No tank/exosuit suppression or broader radius/height gate is
introduced. Existing geometry limitations remain. Vehicle snapshots now also name the selected vehicle kind and
feet-above-vehicle-root height so a further failure can distinguish a kind omission from a geometry rejection.
Recorded supply-driver poses still have the expected ~0.46m hand/root height, but vehicle-root height was not
logged previously, so do not claim this omission was the only possible cause. Runtime confirmation is required.

GR-8 shot 1 has root height 0.5129m, no meaningful player movement, root-camera yaw -1.3556deg and identical root /
muzzle forward axes. The supported projectile watcher has no verified GR-8 projectile mapping. Its local weapon
archive lists the weapon, optic and magazine units, not a clear projectile unit; no guessed projectile hash or
broad live scan is added. Thus this snapshot is **not an actual GR-8 flight calibration**.

Use an explicit fixed estimate for GR-8 only when its root is below 0.65m above tracked feet: yaw offset -1.35deg,
with the existing pitch offset 1.5deg. This estimate aligns that captured heading with the camera; it is based on
other recorded stationary weapons' near-camera round direction, not proof of GR-8 shot direction. The 0.65m band
is estimated from the one prone record plus margin; a low crouch, slope or unusual animation could overlap it.
Higher GR-8 roots retain exactly the old 0deg yaw / 1.5deg pitch fallback, preserving the reported standing and
crouched behavior in those height groups. All GL-21 values, speeds, gravity, drag, origins and movement remain
unchanged. Vehicle context is still separate and no offset is learned over time.

All 140 Lua 5.1 tests pass, including supply-driver hiding / passenger preservation and immediate, stable GR-8
low-root estimated heading without changing higher-root values. The GR-8 test checks alignment with the captured
camera as an estimate; it does not assert a measured projectile match. Existing recorded GL-21 flight tests pass.
Next check requires only supply-driver right-click and one or two GR-8 shots prone; note remaining lateral error.
No GL-21 retest is required for unchanged profiles. Test.10 runtime pending; no remote push.


## Test.11: prone body tilt evidence

User confirms the test.10 GR-8 prone correction fits on ordinary ground, but uneven terrain changes body angle
and the arc disagrees again. Standing/crouching remain satisfactory. Preserve the confirmed flat-ground values.
A fixed world-yaw correction does not by itself account for a changing body/weapon local frame. Height-band
selection may also change on uneven terrain. Neither causal contribution is established by the existing records.

The loader implementation documents `chef.unit_rotation` as forward XYZ plus yaw; its fourth result is NOT roll.
Reading that result as roll, or rotating corrections by an unmeasured terrain normal, would be invalid. Current
shot logs contain no torso basis/roll, so they cannot validate a body-frame compensation. No guessed slope gain,
new live learning or universal camera convergence has been applied.

The already extracted avatar joint metadata names `weapon_aim`, `aim_weapon`, `boss_aim`, `hips`, `chest`,
`l_clavicle`, `r_clavicle`. Names establish node presence, not the meaning of their runtime axes. Test.11 resolves
these names through the existing guarded unit-node interface, caches per avatar/world (missing retry five seconds),
and logs position/forward vectors only at bounded shot snapshots. The existing sixteen-shot / three-per-profile
budget remains. No extra watch, world scan, per-frame skeleton read or new native API is introduced. Missing
nodes are logged and never used as fabricated orientation values. Logging never changes a displayed trajectory.

The paired clavicles and hip/chest positions can establish an observed torso frame; aim-node forward vectors can
be compared with GL-21's actually tracked projectile direction. Possible next fixes are a fixed correction applied
in the appropriate local frame, or a verified aim-node basis that bypasses terrain-induced visual weapon bias.
Both require distinguishing the avatar aim node from a visual animation helper. Do not equate node names with
actual shot direction before observation. Gravity must remain world-down even if the launch direction is corrected
in a local frame. Vehicle context must remain separate.

Verification: all 141 Lua 5.1 tests pass, including distinct captured aim-node directions, missing-node tolerance,
no skeleton logging without a shot or while holding the trigger, and identical rendered arcs before/after logging.
Existing fixed profiles, origin, ballistic physics, grenade/C4/stratagem behavior are unchanged. The test.10 game
log also contains supply-FRV blocked-aim messages; final vehicle runtime acceptance is not inferred from messages
alone. This build is diagnostic, not a completed uneven-ground correction. No remote push.

Minimal required evidence: with GL-21, fire one stationary prone shot on flat ground and one where uneven ground
visibly tilts the torso; use a similar aim direction/elevation and a distant fixed surface. GL-21 is needed because
its round is traceable, unlike GR-8. For direct GR-8 comparison, repeat those two conditions with GR-8 and note
which side the real impact differs from the arc. No standing/crouched or broad all-weapon survey is requested.


## Test.12: prone correction in the weapon frame

The user observes side error while turning to look sideways prone, even without rough ground. Test.11 captured
three GL-21 tracked flights and three GR-8 snapshots plus one unusable short vehicle crossbow flight. Avatar aim
node forward vectors do not track the actual GL-21 direction consistently; node names are not shot semantics.
Raw observations are preserved in `tests/fixtures/weapon_direction_test11.json`.

Two problems are visible. GL-21 shot 5 is prone (hips 0.178m above feet, torso elevation 11.9deg) despite weapon
root height 0.5245m, so the old height-only logic selected the mid-root correction. Also, the weapon's own up axis
rotates strongly as the torso twists: reconstructed GL-21 roll is about +18deg, +15deg, -97deg in shots 3-5.
Subtracting fixed WORLD yaw/pitch cannot express the same correction when the weapon rolls this much.

No extra experiment/native quaternion API was needed to recover weapon roll. The existing muzzle/root positions,
root forward F, and already extracted bind-muzzle position (x,y,z) determine the other two rigid weapon axes:

- P = live muzzle minus root, with its component along F removed.
- In the weapon's orthonormal basis, P = x R + z U and F cross P = z R - x U.
- Therefore U is parallel to z P minus x (F cross P); normalize it, then R = F cross U.

The observations agree with the static locator geometry: GL-21 along about 0.4377m, perpendicular about 0.0959m;
GR-8 along 0.3886m, perpendicular 0.1685m. Runtime verifies along/perpendicular lengths against bind data, so a
missing locator/legacy offset or changed animated geometry falls back to the old world-offset calculation.
No hardcoded node indices, terrain query, inverse graphics or guessed roll angle is used.

Test.12 applies fixed right/forward/up direction weights in this recovered weapon basis for confirmed prone
GL-21/GR-8 only. GL-21 uses local right -1.85deg and local up -0.75deg, retaining the ordinary-prone baseline rather
than fitting a new curve to the three twist cases. GR-8 local angles -1.28277/-1.54815deg are the exact conversion
of the user-accepted world correction in test.11's flat GR-8 reference shot 1. They are not new GR-8 projectile
measurements. Weights are precomputed at load and never learned on equip/aim. The final existing +0.6deg lift,
movement inheritance and gravity remain in world coordinates; only the launch aiming correction is transformed.

Prone selection now uses two avatar nodes, hips and chest, cached per avatar/world and queried once per frame
only for profiled aimed on-foot weapons. A low pelvis and non-upright torso indicate prone even if the gun rises
while twisting. Missing/degenerate nodes fall back to legacy weapon-height bands. The geometric thresholds are
heuristics (hips -0.15..0.45m above feet, torso span 0.1..0.8m with absolute elevation at most about 53deg), not an
engine stance flag. Very steep ground, unusual poses, changed avatar anatomy and uneven foot/root placement
remain limitations. Standing/crouched high-pelvis inputs use the old offsets. Vehicle context is separate.

`tools/analyze_prone_frame.py` reproduces the comparison from raw saved positions and static muzzle metadata:

| GL-21 test.11 shot | Previous yaw error | New yaw error | Previous full initial direction error | New full direction error |
| --- | ---: | ---: | ---: | ---: |
| 3 | 0.836deg | 0.630deg | 1.242deg | 0.699deg |
| 4 | 0.767deg | 0.561deg | 0.871deg | 0.542deg |
| 5 | 1.104deg | 0.027deg | 1.964deg | 0.852deg |

Horizontal actual direction comes from tracked XY positions. Vertical direction is estimated using the existing
GL-21 speed/drag/gravity model against height versus range. These are recorded-input replays, not test.12 game
results. The shot-5 residual is largely vertical; this is a partial correction, not full all-angle accuracy.
GR-8 remains untracked: comparison against CAMERA ONLY improves from 0.679 to 0.111deg and 1.299 to 0.710deg in
snapshots 2/6, while reference shot 1 is preserved. This does not establish the actual GR-8 flight direction.

145 Lua 5.1 tests pass. Checks include all previous stable GL flight records, twisted-prone tracked records from
the first frame, no convergence with time, the GR-8 accepted reference, a rigid 90deg weapon-roll case, crouch
preservation with a lowered gun, corner/aim lag with a physically rigid rotated locator, fallback geometry,
vehicle eligibility, and grenade/C4/stratagem regressions. Diagnostic logs now distinguish weapon-local from
world-offset direction; logged legacy offset fields alone are not the final local correction.

Next check: GL-21 and GR-8, prone on ordinary ground, aim forward/left/right without moving the lower body more
than necessary; one single shot in each direction. Six shots fit the existing three-per-weapon/profile budget.
Report remaining horizontal AND vertical error. No new terrain search or standing/crouched survey is requested.
No test.12 runtime accuracy claim or remote push.


## Test.13: FRV-only GL-21 frame trial; no GR-8 vertical trim

User reports small GR-8 prone vertical disagreement after test.12, while prone horizontal alignment appears good.
Tank passenger aiming appears accurate and rotates the whole body, whereas FRV leaning-out aiming twists the
upper body with fixed lower body; side/downward aim increases error. Preserve tank behavior. These are user
observations, not measurements of a cause common to every weapon.

A proposed +0.15deg GR-8 trim was an arbitrary trial value, not calculated from flight data. The user challenged
it, and it was removed before packaging. All GR-8 prone launch directions are unchanged from test.12, verified
against all three test.12 GR-8 snapshots in `weapon_direction_test12.json` (both pitch and yaw). There is no hidden
camera fit, re-learning or vertical trim. Camera disagreement alone is not projectile disagreement.

For FRV GL-21 only, reconstruct the same rigid weapon frame used prone, but use a separate FRV correction from
actual recorded test.9 shots 9-11. Their fitted local right/up pairs are approximately (-0.261,-0.998),
(+0.528,-0.904), (-0.326,-1.373) degrees; means approximately (-0.020,-1.092), rounded to 0/-1.1 degrees.
This preserves a measured-data origin for the values; only three old samples exist, not independent validation.
Full initial direction replay errors improve 0.624->0.281, 0.721->0.563, 0.471->0.425 degrees. Only GL-21 in a
regular/flamer/supply FRV selects this candidate. Tanks and other FRV weapons retain the prior world correction.
Very side/downward FRV accuracy still requires observation; synthetic roll/vertical tests prove finite geometry,
not actual hit accuracy. The FRV driver gate remains unchanged.

`src/weapon_frames.lua` contains named muzzle bind coordinates for all sixteen supported assets, generated from
the already verified local unit fixture. Build-time embedding avoids runtime file reads and new dependencies.
The prone frame's geometry now comes from this shared table; the correction coefficients are unchanged.
`tools/inspect_weapon_nodes.py --lua-output ...` can regenerate it alongside the evidence fixture after an asset
update, reducing manual coordinate maintenance. No game extraction/download was repeated for this change.

All 149 Lua 5.1 tests pass, including saved GR-8 direction preservation, both tank variants' unchanged recorded
launch, actual FRV GL-21 replay improvement, side-roll/straight-down finite geometry, all-sixteen named muzzle
coverage and unchanged unmeasured weapon modes. No FPS or in-game accuracy claim is made.

The user also authorized a development-only GR-8 projectile collector if necessary. Public native pool research
was found, but the build/layout and access checks fail for this installation. See NATIVE_PROJECTILE_RESEARCH.md
for exact evidence. No usable native collector or GR-8 flight acquisition is claimed, no package downloaded or
installed, and no GR-8 vertical value changed. No collector is in the ZIP. Do not request more GR-8 shots without
first establishing a functioning measurement path.

Focused optional test.13 check: GL-21 only, stationary FRV passenger, one forward and one side/downward shot.
No tank or prone GR-8 repeat is needed for code intentionally unchanged in this build. Runtime pending; no push.
