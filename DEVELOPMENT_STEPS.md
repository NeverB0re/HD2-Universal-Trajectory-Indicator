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
2. **Equipment and release identification:** establish my player and held weapon/throwable reliably; invalidate stale weapons; distinguish hand movement from release; handle short grenade inputs. Research current loader and game object APIs first. Add targeted diagnostics only for missing evidence.
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
