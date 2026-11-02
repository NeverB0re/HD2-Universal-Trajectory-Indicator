# Universal Trajectory Indicator development

## Current baseline (2026-11-02)

- The canonical workspace is `mods/throwable-arcs` on `main`, consolidated from the former `throwable-arcs-claude` linked worktree. That redundant worktree was removed after verifying the migrated files.
- Version 1.2.0 is released on GitHub and Nexus. Preserve the existing release ZIP and internal resource/settings identifiers.
- Current weapon direction uses the game avatar aim target; see `CROSSHAIR_AIM_FINDINGS.md` and `README.md`. The milestones and test-version notes below are historical, not a list of current unresolved defects.
- Local experiment archives, earlier research and the Python environment remain available. The local handover is excluded from Git.
- Continue development in this workspace with Codex; no second agent workspace is required.

## Goal and rules (2026-10-31)

- Final goal: show useful flight arcs for all weapons (especially rounds with drop), stratagems and throwables.
- Preserve existing stratagem/C4 arcs and the C4 mode icon. Discuss major behavior changes or feature removal with the user first.
- Prefer existing game data, loader APIs and source research over new game experiments. Measure only what those sources cannot establish.
- Optimize without deleting features. Passing offline checks is not proof of actual gameplay, accuracy or FPS.
- Keep feature-sized local commits. Push only a substantial stable milestone after real-game testing. No experimental pushes.
- Check the current branch and working-tree status before editing; preserve unrelated local files and changes.
- Ask before downloading additional mod/data files. Public source browsing and existing local research can be used first.

## Ordered milestones

1. **Calibration safety (implemented offline, runtime unverified):** validate loaded and newly learned grenade values; recover an invalid kind without discarding other valid kinds; preserve the original data before repair; cache medians outside the frame loop.
2. **Equipment and release identification (implemented offline; focused runtime check pending):** invalidate stale weapons; distinguish hand movement from release; refresh candidates on grenade input/pose transitions. Reference research found a hand node, but no proven direct local-avatar unit mapping. Multiplayer identity and actual quick-throw detection remain validation limits.
3. **Grenade trajectory accuracy:** align camera/feet/velocity snapshots to release time, fix the known time-reference error, use the current pose for release origin, initialize armour for grenades and verify perk factors. Reject inconsistent measurements before they become calibration. Retain learning rather than removing it without discussion.
4. **Weapon muzzle and prone arcs (test.5 origin/prone confirmed, direction regression; test.7 direction correction awaiting runtime):** the user moved to this milestone on 2026-11-01 after reporting that grenade arcs fit well. Use the installed assets' actual muzzle nodes, remove height-based prone suppression, and distinguish close third-person cameras from first person. Current evidence and targeted test are in `WEAPON_MUZZLES.md`.
5. **Coverage and distribution:** compare the supported weapon/throwable list with the current roster/data; complete missing supported behavior; reduce diagnostic I/O; package notices; document actual limitations.
6. **Runtime acceptance:** standing/crouching/prone, movement, armour, swapping weapons/grenades, host/client, key rebinding/controllers, respawn and persistent-data recovery. Release/push after the milestone passes, not merely after unit tests.

## Step 1: 1.1.1-test.1

Branch: `fix/grenade-calibration-validation` (based on `17a134b`).

- Reject non-finite values, malformed/sparse arrays, nonpositive speeds, backwards yaw (outside the forward hemisphere), and release origins outside the existing 3m reach bound. A generous 1000m/s numerical guard is not a measured grenade speed cap. These are safety bounds, not proof of correct calibration.
- An invalid legacy row restores that kind's measured defaults (or generic fallback for an unseeded kind); valid rows retain their calibration. Legacy arrays have no sample ids, so an invalid row cannot be repaired sample-by-sample reliably.
- Keep the existing `grenade_throws6` key. Before the first repair, preserve the loaded data in `grenade_throws6_before_validation1`, wrapped in `original`. Retain that first backup on later launches.
- If the backup cannot be saved, or the original file cannot be parsed/read, use safe values in memory and do not overwrite the original calibration during that launch. A normal save failure is logged.
- Newly measured backwards/non-finite/out-of-bounds values are rejected before changing the calibration. Full selection, release and outlier validation remain steps 2–3.
- Calculate per-kind medians lazily and cache them until accepted learning changes that kind; no sample sorting during steady rendering.

Validation: 80/80 main Lua 5.1 fake-loader tests passed, including the recorded Impact failure, preserving another kind, malformed numbers/arrays, backup and parse failures, existing backup retention, reversed-flight rejection and cache invalidation. This does not validate real hand animations, actual game persistence, runtime performance or final grenade accuracy.

The actual local `grenade_throws6` data was also replayed through the fake loader: Impact recovered, Giga calibration retained, and the live file's SHA256 remained unchanged. This was read-only replay, not a game run.

Test package: `test-builds/Stratagem and C4 Trajectory v1.1.1-test.1.zip`. CRC and embedded source match were checked. The builder now includes `THIRD_PARTY_NOTICES.txt` verbatim in the ZIP (a separate packaging fix). The ZIP has not been installed or runtime-verified; it is not copied into `release/`.

No game experiment is requested for step 1 alone: the data defect and cache behavior are reproducible offline. The current hand/release and prone problems still need the later milestones. Do not treat the test ZIP as a stable release or overwrite the user's live AppData during development.

## Step 2: 1.1.1-test.2

Reference research is recorded in `REFERENCE_FINDINGS.md`, with pinned NarrowHUD 2.0.0 source links. No new mod download was needed.

- Grenade candidates are selected by current hand pose and distance to `attach_hand_r`, including low/prone hands and poses 40/41/42. If the node is unavailable, retain the old feet-based compatibility fallback, still gated by readable hand pose. Therefore the fallback retains more ambiguity and is named in the diagnostic log.
- A fast movement starts a bounded candidate buffer; only actual separation from the hand confirms a release. This retains early samples/aim rather than adopting the camera angle several frames later. Pose-only cancellation does not start a flight.
- Weapon selection is continuously checked for distance to the player and, when available, the hand. A throwable pose invalidates a previously selected gun even if aim stays pressed.
- Reset grenade flights and movement history on player changes; do not learn an old player's flight across respawn/world changes.
- Resolve hand nodes once per player (missing nodes retry every five seconds), share a single hand-pose read per frame, avoid repeated candidate-position queries, and request watch refresh only at bounded input/pose edges. No per-frame world scan was added.
- Logs identify acquisition/loss and confirmed release, including `hand node` versus `feet fallback`. They do not stream position dumps every frame.

Validation: 95/95 Lua 5.1 fake-loader tests passed. The 15 new tests cover hand-versus-feet selection, weapon poses, fast hand swings, low/prone hands, mine/underhand poses, cancellation, aim snapshots, respawn, stale/slung weapons, weapon-to-grenade switching, bounded reads, asynchronous refresh, and ballistic release samples at 30/60/120fps. None of this proves actual animation, accuracy, performance, or multiplayer identity.

Focused runtime check for test.2 (use a familiar grenade such as Impact; no full weapon survey yet):

1. Standing, hold G and move the view; confirm the arc persists until release. The user confirmed that this game state commits the throw: manual cancel/stow or weapon switching while holding G is not a valid test.
2. Start by aiming a supported gun, then press G to prepare a grenade; confirm the old weapon arc gives way to the grenade. C4/stratagem calibration is unchanged; a brief familiar-use check can catch accidental regressions.
3. Hold the grenade prone, then try a short quick throw standing. Report any missing arc, flash, or stale arc; the log records whether detection used the hand node. Do not use landing accuracy as this stage's acceptance criterion: fixed feet-relative grenade origins, armour initialization and fit-time correction are still step 3.

The existing log path is `%APPDATA%\Arrowhead\Helldivers2\throwable_arcs.log`. No additional probe mod is required. The test package is `test-builds/Stratagem and C4 Trajectory v1.1.1-test.2.zip`; do not install it beside another Throwable Arcs version. Runtime has not been verified and no push is permitted yet.

User follow-up: Giga display works, confirmed with the local test.2 log showing pose 42, hand-node detection and physical separation. Other kinds and quick-throw timing remain unverified. The user reports a slight rightward landing miss and possibly longer actual forward-moving throws; those accuracy observations are not yet quantified. The synthetic unexpected-pose-change fixture is retained as an internal defensive check, not a claim that the player can cancel a G-held throw.

## Step 3: 1.1.1-test.3 (accuracy model; runtime check pending)

The user cannot test every throwable. `GRENADE_MODEL.md` records the alternative data path: 23 native HD2Runtime profiles plus separately measured Caltrops, with exact unit identities, attributed sources and a reproducible generator. The user approved the capability JSON download; its Git blob hash was verified. No additional runtime was installed.

- Existing per-kind speed/lift/yaw learning remains. Unmeasured kinds now get a native-curve baseline transferred from our measured standard grenade, instead of all using generic 21m/s. This transferred caller strength is empirical; it is not labelled a proven native input.
- Native kinds apply authored forward/backward strength adjustments. Drawing and learning use inverse equations, and the fitter restores vertical velocity to release time. 30/60/120fps ballistic fixtures recover the same launch speed/lift.
- Origins follow the currently held unit's actual pose. New calibration learns hand-relative release offsets; old standing feet offsets stay recorded for diagnosis. The unlearned 0.4m vertical allowance remains approximate.
- Grenade-only play initializes armour. Failed discovery retries at most once every five seconds; existing stratagem/C4 factors are preserved.
- One bounded comparison line per throw records the displayed launch and up to 16 actual samples, enabling remaining origin/yaw/drag errors to be investigated with the user's existing Giga rather than every grenade.
- Repeated prone weapon logs are deduplicated; varying failed-alignment diagnostics are limited to two per second. Weapon-prone suppression itself is unchanged, pending the weapon milestone.

Validation: 105/105 Lua 5.1 fake-loader tests passed. Added checks include exact drag-free release-time recovery, moving native-curve inverse at 30/60/120fps, grenade-only armour discovery/rate limiting, bounded comparison logging, 23 native profile mappings, distinct unlearned curve families, learned relative offsets and prone hand movement despite legacy standing samples. All prior main tests still pass. This is not proof of every kind's actual trajectory.

Next runtime evidence: only Giga, two stationary throws and two forward-walking throws with similar moderate aim and the same armour. No invalid G-held cancel/swap instruction and no request to acquire every grenade. The new telemetry will separate rightward offset from movement/drag errors. Test.3 remains local and unpushed until accuracy is checked.

## Step 3 follow-up: 1.1.1-test.4

User test.3 feedback: Giga still lands right of the line and its origin looks right of the release, producing a left-slanting path from the aimed view; range is closer but unsatisfactory. Melta lands farther than predicted. Impact looked accurate from approximately its third throw. Muzzle/prone weapon work is explicitly deferred above.

Read-only analysis of all 29 recorded comparisons is documented in `TEST3_FINDINGS.md`. No new mod download or unsafe Actor API probe was needed.

- Fit a 0.65s early airborne window beginning 0.15–0.2s after first motion, with at least 0.25s of data. Select using following velocities rather than the incoming hand-to-air jump, retry eligible windows, retain the 0.15m RMS limit and stop before sharp speed loss/contact. This excludes Melta's initial hand swing and reduces Giga's short-window direction bias.
- Reference angle/origin learning to the fresh last displayed hand/camera snapshot, rather than a different hand pose during the throw animation. Capture the missing hand anchor and camera basis in the displayed preview.
- On the first accepted new fit for a kind, preserve its old samples in `fit_backups` within the same save. Restart only the incompatible angle/relative-origin histories, retain speed history, preserve unrelated kinds, and persist `fit_revision=2` so it is not reset on every launch.
- New comparison records remain bounded and acceptance records include window span, RMS and fitted offset. No per-frame world scans or native physics-handle calls were added.

Validation: 110/110 main Lua 5.1 fake-loader tests passed, including recorded Giga/Melta/Impact replay fixtures, displayed-hand versus swing-hand regression, and backup/reload/second-fit checks. Older straight-line grenade helper data was corrected to include gravity so it tests an actual ballistic flight. All 29 sparse recorded traces were separately replayed: Giga 9/9, Melta 12/13 and Impact 7/7 accepted; test.3 actually accepted 6/9, 3/13 and 7/7 respectively. This is offline replay of old observations, not a new game accuracy result.

Focused next runtime check: Giga twice and Melta twice, about three seconds apart so the first fit can complete. Impact is covered by recorded replay; a live regression throw is optional when already equipped, not a required extra mission. No full roster survey is needed. Test.4 is local/unpushed and must replace, not accompany, test.3 in the mod manager.

User acceptance on 2026-11-01: grenade arcs fit well; proceed to the next issue. This is user runtime confirmation
for the tested grenades, not a claim that every catalog item and posture has been played. Preserve that result.

## Step 4: 1.1.1-test.5

See `WEAPON_MUZZLES.md` for the installed-build evidence, all 16 muzzle names/indices and verification boundaries.
The prior live probe already confirmed six supported muzzle nodes. Local Filediver extraction and a static reader
established the other supported nodes without requiring more weapon-specific experiments or any download.

- Actual animated muzzle positions replace the common 0.45m start; the legacy estimate remains a logged fallback.
- Remove explicit low-weapon-height suppression and use hand proximity for strongly lagging prone weapons.
- Use sight-node camera proximity to refine first-person hiding. This heuristic requires live view-mode testing.
- Resolve/cache indices per unit and world, read positions live, and retry unavailable names slowly.
- Grenade calibration/fitting is unchanged from the user-accepted test.4; existing C4/stratagem behavior is retained.

Validation: 119/119 main Lua 5.1 fake-loader tests passed, including actual-asset-derived parameterized muzzle checks
for all 16 weapons and the prior grenade regression fixtures. ZIP source/notice checks are required before delivery.
No real-game test.5 run, accuracy/FPS claim or remote push. Next check uses one currently equipped weapon through
standing/crouching/prone and first-/third-person view, plus a standing/prone shot when practical.


## Step 4 runtime follow-up: 1.1.1-test.6

The user confirmed test.5 muzzle alignment and prone availability, but reported leftward shot-direction error,
stronger standing/crouched. Keep the successful geometry. Test.6 adds a bounded passive shot-vector/projectile
recording window to distinguish direction/calibration/selection effects before changing aim math. It is a diagnostic
build, not an accuracy fix. See WEAPON_MUZZLES.md for limits and the six-shot one-weapon check. All 124 offline
Lua 5.1 tests pass; runtime accuracy remains unresolved. No remote push.


## Step 4 correction: 1.1.1-test.7

Test.6 measurements identify a frozen stationary yaw correction in prone GL-21: root/camera yaw differs by
1.72-2.28 degrees while the old acceptance gate allows only one degree from the cached correction. Actual
projectile yaw remains within 0.27 degrees of camera yaw in those two shots. Root and muzzle directions agree.
Implement independent yaw acceptance within an absolute three-degree envelope, retain stillness/dynamic lag and
large corner deflection protection, and make smoothing independent of FPS. Preserve all muzzle/ballistic/grenade
behavior. Recorded inputs reproduce the old failure; 128 tests pass after the change. See WEAPON_MUZZLES.md for
measurements, limits and the six-shot GL-21 check. Test.7 runtime pending; no remote push.


## Step 4 vehicle follow-up: 1.1.1-test.8

The user reports stationary passenger trajectory disagreement and false driver-seat arcs on right-click. No
verified seat/firing eligibility reader was found in inspected local/public sources. Preserve passenger support;
add bounded passive vehicle aim geometry/known animation-variable snapshots using existing guarded APIs before
choosing a driver gate. Test.8 includes test.7's unverified-in-game prone correction. All 131 tests pass; vehicle
eligibility and passenger accuracy are unresolved. See WEAPON_MUZZLES.md for the minimal stopped-car check.


## Step 4 fixed-profile correction: 1.1.1-test.9

User requests fixed weapon/context corrections instead of aiming-time convergence; driver remains falsely drawn.
Remove the live weapon-angle learner and shared per-kind history. GL-21 gets offline-fitted immutable height-group
profiles; other weapons/vehicle context use explicitly unmeasured fixed defaults. Preserve live muzzle/heading,
movement and ballistic physics. Confirmed passenger-then-driver order links driver snapshots 9-13 to low weapon
height; add a bounded elevated-FRV raised-weapon eligibility check without suppressing prone ground soldiers.
No verified seat enum is inferred from character_state. Reserve shot recording budget per weapon/profile so the
next passenger flight can actually be observed. All 138 tests pass; test.9 runtime and passenger ballistics remain
pending, along with unusual geometry/rapid turn coverage. See WEAPON_MUZZLES.md for data/limits.


## Step 4 coverage correction: 1.1.1-test.10

Test.9: user confirms grenade-launcher accuracy, reports GR-8 prone lateral error and continued supply-FRV driver
arcs. Add the omitted supply-FRV kind to the same raised-weapon guard. Add an explicitly estimated GR-8 low-root
fixed yaw correction from its one captured root/camera snapshot, keeping higher-root offsets and all GL-21 data.
No GR-8 projectile calibration is claimed; threshold/heading need runtime confirmation. Add vehicle kind/up-height
to bounded diagnostics. All 140 tests pass; no remote push. See WEAPON_MUZZLES.md for evidence and limitations.


## Step 4 terrain follow-up: 1.1.1-test.11

User confirms GR-8 prone test.10 fit, but terrain-induced body inclination changes alignment. The current loader
wrapper exposes forward and yaw, not roll, and existing logs lack a body frame. Use cached avatar aim/torso node
names already present in extracted metadata to record bounded shot-time vectors/positions. This is necessary
slope evidence, not a new calibration or a change to the accepted flat-ground aim. All 141 tests pass. Next:
compare flat/tilted prone GL-21 tracked rounds and GR-8 aim nodes before choosing a local-frame correction.


## Step 4 prone twist correction: 1.1.1-test.12

Test.11 confirms varying torso/weapon orientation while aiming sideways prone. Recover rigid weapon right/up
from existing animated muzzle/root positions and static bind metadata; no extra runtime experiment/API needed.
Apply fixed local-frame launch correction for prone GL-21/GR-8; keep world gravity/lift and other contexts.
Classify profiled prone poses by cached hips/chest geometry, retaining height fallback when unavailable.
Saved GL-21 twist records improve horizontally and in full initial direction, but residual error remains.
145 tests pass; test.12 runtime pending and GR-8 still lacks tracked projectile evidence. See WEAPON_MUZZLES.md.


## Step 4 FRV/data follow-up: 1.1.1-test.13

User distinguishes satisfactory tank passenger behavior from FRV upper-body twist and questions the unsupported
GR-8 +0.15deg proposal. Remove that proposal before packaging; verify test.12 GR-8 direction remains identical.
Apply a separate fixed local-frame FRV GL-21 candidate from its three recorded flights; retain all other FRV
weapon/tank calculations. Generate shared bind geometry with optional inspector Lua output. 149 tests pass.
User permits development projectile acquisition, but current native research/build code does not match and the
running-game module read is denied. No flight captured; no more GR-8 shooting requested until access is solved.
Evidence: WEAPON_MUZZLES.md and NATIVE_PROJECTILE_RESEARCH.md. No remote push.


## Step 4 historical trace recovery: 1.1.1-test.14

Old test.3-6 code did attempt new-unit GR-8 tracking; the current allowlist cannot establish that GR-8 is
untrackable. Correct that inference. Old raw GR-8 numbers were not recovered from searched current files, so
restore bounded Chef new-unit discovery, explicit candidate identity uncertainty and synchronized model sampling.
Do not apply a numerical correction yet. Strip all weapon/vehicle diagnostic blocks and hooks from stable builds.
152 tests pass; two-shot GR-8 capture pending. NATIVE_PROJECTILE_RESEARCH.md records the corrected evidence.
