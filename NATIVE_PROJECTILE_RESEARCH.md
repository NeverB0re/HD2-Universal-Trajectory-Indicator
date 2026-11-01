# GR-8 native projectile measurement: 2026-11-01

## User requirement and current status

The user requests measured corrections, not arbitrary test angles, and authorizes development-only projectile
tracking when needed. Search public data before requesting shots; exclude acquisition tools from release ZIPs.
The proposed +0.15deg GR-8 prone trim had no numerical measurement basis and was removed BEFORE any test.13
ZIP was produced. GR-8 test.12 initial direction is preserved. No GR-8 actual flight has yet been captured.

## Public sources reviewed (no package download or installation)

- [HD2Runtime build profile](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/schemas/build_profile.json)
- [Read-only projectile pool access in event_world.lua](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/runtime/event_world.lua#L753)
- [Pool layout/code evidence in projectile_rows.lua](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/domains/projectile_rows.lua)
- [Per-shot flight members](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/runtime/projectile_shots.lua)
- [Update migration workflow](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/docs/game-update-migration.md)

The pool records actual position, velocity, distance, lifetime and source/owner/creditor, so a read-only accessor
could capture non-unit-driven projectiles that the current model-unit watcher cannot. Per-shot modification and
homing APIs also WRITE flight data; they are not appropriate for observing unmodified ballistics. No such API was
activated. Static projectile data alone cannot quantify an animation-dependent initial-direction discrepancy.

## Why the published addresses were not used

The public profile is for 2026-09-26 / Steam build 25480438, DLL SHA256
`2E2C3B7C2500646DADD5F2B4C6E0504DBB7E7896139F64CDDC0D1813C718F51E`.
The installed DLL SHA256 is
`61DCFCD201DACBF3545C97BEB8A5A6186E9850D2670BF60B0E058320B477F6DF`.
Offline PE-section-mapped comparison: 0 of 60 published pool code pins match at their published RVAs.
The old pool-global RVA 0x347CEA8 is also beyond this installed PE's SizeOfImage 0x3382000.
This establishes that directly using those addresses is unjustified. It does not establish the loaded module's
layout, the reason for disk-code differences, or that no other read path can exist.

The user then opened the game and waited on the ship, without firing or installing another mod.
Read-only Windows checks on that process:

- OpenProcess with QUERY_LIMITED_INFORMATION | VM_READ: handle opened.
- Ordinary managed process-module metadata did not expose the game modules.
- K32EnumProcessModulesEx: failed, WinError 5 (access denied).
- VirtualQueryEx / K32GetMappedFileNameW located a runtime.dll image mapping.
- ReadProcessMemory of its two-byte PE signature: failed, WinError 5.

All handles were closed. No process writes, remote threads, injection, protection changes, registry edits or
bypass tools were used. The tests do not prove which component denied access. No game-memory dump, projectile
pool read, projectile write or new GR-8 shot measurement was performed. The user was told waiting could end.

## Remaining dependency

A verified current-build read-only projectile accessor is needed (a supported in-game interface, or a permitted
external reader with newly verified layout). The current Chef Lua unit watcher cannot substitute a camera or
animation-node value for an observed GR-8 projectile. Do not attach an arbitrary projectile resource id or carry
old native addresses forward. No further GR-8 shots are requested until a working acquisition path exists.

A future collector should be separate from the installed mod: bounded duration/shot count, local-player/source
identity checks, slot-reuse/in-flight guards, finite-value validation, timestamps plus velocity/position, and
correlation to the mod's shot/muzzle/body records. Record actual vanilla shots; never modify them to measure them.
No collector was bundled into test.13 or any release ZIP. Existing development-only Lua unit tracking remains
bounded; removing all development tracing from a stable release remains a release gate.


## Historical correction and restored Chef path (test.14)

The user recalls earlier actual-round checks. Git confirms `248c528` (1.1.0-test.3) and `3698ed7` (test.6) used
World.units before/after the click and followed new moving units without a projectile-kind allowlist. The test.6
source explicitly notes that test.3 GR-8 rounds disappeared before 0.3s and shortens the comparison to about 20m.
The historical algorithm could misassociate another new moving unit; that comment alone is not a validated
projectile identity or a numerical launch-angle calibration. However, it directly contradicts treating the recent
allowlist's missing GR-8 entry as evidence that GR-8 cannot have a trackable unit. That earlier inference was wrong.
External native access failure remains true but does not exhaust the in-game Lua route.

Searched current Arrowhead log directory, workspace research/fixtures and tracked Git file history. The surviving
weapon_probe.log has no GR-8 model/shot match; its known round tracks belong to other weapons. The current
throwable_arcs.log covers later runs, not the old test.3-6 checks. No old `shot check GR-8 ... round KIND` or GR-8
`flight` position series was recovered from those locations. Git preserves code and notes, not the absent runtime
numbers, so a correction cannot be recalculated from the historical comment alone. This does not establish that
no user-held backup or other conversation record exists.

Test.14 restores a bounded version of that in-game new-unit discovery for GR-8 only. It uses guarded Chef APIs,
not process memory access or an old native address. Baseline at aiming/equipping (at most six arms per load), at
most six full unit enumerations within 0.14s after a recorded click, at most 64 newly seen handles examined per
scan and twelve nearby candidates. The dangerous runtime-built kind is excluded before position reads. Candidate
positions continue only in the existing 0.35s window / sixteen-shot global budget and three-per-weapon/profile cap.
No baseline or discovery scan is repeated continuously while holding aim.

All candidates keep their kind and independent position series. Summaries label continuous multi-sample motion
with mean speed 0.5..1.5 times the weapon's nominal speed as plausible, but identity remains explicitly unverified.
Static/reload/animation units are not silently called projectiles and no candidate changes a displayed arc or a
calibration. Actual resource identity, source ambiguity, first-seen timing and trajectory continuity must be checked
from the next trace before deriving GR-8 coefficients. Simultaneous model/camera records at each sample separate
input-frame measurements from actual appearance. The historical farthest-unit winner heuristic is not reinstated.

Build-time development markers remove BOTH weapon and vehicle collectors plus their update/shutdown hooks from
non-test versions. The stable-source compile/runtime test verifies no weapon_diagnostic, candidate-summary,
GR-8 discovery or vehicle-aim recorder remains, while weapon arcs work. No native external collector is included.
A live GR-8 flight is still pending; do not represent restored capability in a fake-loader test as captured data.
