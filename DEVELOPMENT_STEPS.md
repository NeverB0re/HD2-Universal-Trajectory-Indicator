# Throwable Arcs completion work

## Goal and rules (2026-10-31)

- Final goal: show useful flight arcs for all weapons (especially rounds with drop), stratagems and throwables.
- Preserve existing stratagem/C4 arcs and the C4 mode icon. Discuss major behavior changes or feature removal with the user first.
- Prefer existing game data, loader APIs and source research over new game experiments. Measure only what those sources cannot establish.
- Optimize without deleting features. Passing offline checks is not proof of actual gameplay, accuracy or FPS.
- Keep feature-sized local commits. Push only a substantial stable milestone after real-game testing. No experimental pushes.
- Another AI agent also works on this mod: check the current branch/status before editing and coordinate overlapping files through the user.

## Ordered milestones

1. **Calibration safety (implemented offline, runtime unverified):** validate loaded and newly learned grenade values; recover an invalid kind without discarding other valid kinds; preserve the original data before repair; cache medians outside the frame loop.
2. **Equipment and release identification (implemented offline; focused runtime check pending):** invalidate stale weapons; distinguish hand movement from release; refresh candidates on grenade input/pose transitions. Reference research found a hand node, but no proven direct local-avatar unit mapping. Multiplayer identity and actual quick-throw detection remain validation limits.
3. **Grenade trajectory accuracy:** align camera/feet/velocity snapshots to release time, fix the known time-reference error, use the current pose for release origin, initialize armour for grenades and verify perk factors. Reject inconsistent measurements before they become calibration. Retain learning rather than removing it without discussion.
4. **Prone weapon arcs:** determine actual muzzle/launch direction by available nodes/data, then minimal targeted shots if needed; replace the prone suppression only when the resulting arc is correct. Check close camera/first-person classification separately.
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

1. Standing, hold the grenade and move the view; confirm the arc persists until release. Put one away without throwing and aim the gun; confirm no grenade arc remains.
2. Keep aim held while switching a supported gun to the grenade; confirm the old weapon arc gives way to the grenade. C4/stratagem calibration is unchanged; a brief familiar-use check can catch accidental regressions.
3. Hold the grenade prone, then try a short quick throw standing. Report any missing arc, flash, or stale arc; the log records whether detection used the hand node. Do not use landing accuracy as this stage's acceptance criterion: fixed feet-relative grenade origins, armour initialization and fit-time correction are still step 3.

The existing log path is `%APPDATA%\Arrowhead\Helldivers2\throwable_arcs.log`. No additional probe mod is required. The test package is `test-builds/Stratagem and C4 Trajectory v1.1.1-test.2.zip`; do not install it beside another Throwable Arcs version. Runtime has not been verified and no push is permitted yet.
