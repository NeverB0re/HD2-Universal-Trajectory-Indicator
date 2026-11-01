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

## Actual test.14 capture and stance evidence budget (test.15)

The next user run DID capture two GR-8 candidate series of kind `4fd8795ed60f5579`:
shot 3 standing (nine positions), shot 4 prone (four positions). Both first appear within
0.025/0.034m of the click-frame muzzle and move at approximately the nominal 250m/s.
The installed resource listing contains this unit hash but gives no resolved resource name.
This is strong shot correlation, not an engine-provided shooter-id association. Raw candidate,
body and synchronized records are preserved in `tests/fixtures/weapon_direction_test14.json`.

`tools/analyze_native_flights.py` fits height against horizontal distance with each weapon's
existing nominal speed/gravity/drag held fixed. It avoids treating time since input as time
since emission. Its pitch describes the first observed position, not a separately verified
launch instant. With these assumptions, GR-8 vertical residual RMS is below 0.0001m over
the recorded segments. This does not prove the model at every range or identify the engine's
aim algorithm. No physics or angle parameter is fitted into the game.

For shot 4, root yaw error is -0.01868deg while the current corrected display error is
-0.65217deg. Thus the roll correction makes this actual prone shot worse. Standing shot 3
display yaw/pitch error is approximately -0.20843/+0.09904deg; prone shot 4 approximately
-0.65217/+0.24879deg. Earlier GL-21 prone captures did benefit from the local correction.
One prone GR-8 flight cannot determine a universal replacement; do not turn these two shots
into a new all-weapon constant or claim the old camera-derived GR-8 profile is validated.

The same run contains three CB-9 standing clicks. Its prediction profile is shared across
stances, so the three-per-profile recorder budget prevented any further prone CB-9 clicks
from being recorded. Test.15 separates diagnostic budgets by geometric stance as well as
weapon/profile. This classification is not an engine stance flag and does not change aim.
The global sixteen-shot cap, three-per-context cap, 0.35s tracking window, GR-8 discovery
bounds and release-time stripping remain. A maximum eight-pose/0.25s pre-click history,
cleared on unit/world changes, distinguishes pre-emission pose from post-click recoil or
animation changes. It never scans the world or learns an aim value during idle aiming.

Test.15 intentionally retains test.14 trajectory math. Its next necessary evidence is
stationary prone GR-8 and CB-9 shots aimed forward, left and right while the lower body stays
fixed, three per weapon, with sufficient clear flight distance. Existing standing controls
are retained; no standing repeat, vehicle experiment or unowned weapon is needed. Compare
the native flight against pre-click/click/first-appearance poses before replacing a model.
155 Lua 5.1 tests pass, including the separate unknown-profile stance budgets and bounded,
unmixed history; these checks are not in-game accuracy validation. No remote push.

## User steering: native dynamic reticle before more stance experiments

Investigate the native circular aiming reticle's live direction/target inputs before asking
for the test.15 stance matrix. No new all-weapon correction is established or applied.

Primary public leads checked 2026-11-01:

- HD2 HUD+ author DC post, https://gall.dcinside.com/mgallery/board/view/?id=helldiversseries&no=874903
  describes native-coordinate dynamic AMR reticles in 0.1.7/0.1.8. This is a stronger
  coordinate-acquisition lead than merely enabling a weapon's hidden native reticle.
- Author's changelog and current status, https://www.nexusmods.com/helldivers2/mods/15298?tab=description
  confirms earlier positional integration; also reports suspension after 7.2.0 because
  real-time data access no longer works through the former architecture. A historical
  method is not proof of a compatible current-build accessor. Package not downloaded yet.
- HD2Runtime https://raw.githubusercontent.com/SkyeShade/HD2Runtime/master/docs/weapon-reticles.md
  describes a crosshair-style enum toggle in WeaponDataComponentData, not a live reticle
  coordinate or shot-direction accessor. Do not confuse visibility controls with aim data.
- The 3rd Person Sniper Reticles author describes native-reticle activation:
  https://www.nexusmods.com/helldivers2/mods/17918?tab=description
  No package inspection or direction-access claim has been made.
- Diver HUD post https://gall.dcinside.com/mgallery/board/view/?id=helldiversseries&no=904895
  is another candidate. Download permission was requested before finding the more specific
  HUD+ post. No download or installation has occurred.

Prefer a supported read of the engine's world-space aim direction/target. If only a 2D
screen position is available, camera unprojection gives a ray from the CAMERA; without
depth, it cannot uniquely determine a ray from a different projectile origin. Do not
silently choose a fixed world distance. First inspect what native data the reference
actually reads and how it projects it; retain existing trajectories until validated.

User authorized download/internal analysis of the linked Diver HUD package. The original
MEGA file handle `dug3QKAB` returned API result `-9` on two metadata attempts; no archive was
received or installed, so no internal code analysis is claimed. HD2 HUD+ is a distinct
package and its download has not yet been authorized. Prefer its original author download
over an unofficial continuation; use the native-coordinate mechanism as research only.

## Resume actual-flight comparison after reference inspection

The supplied current Diver HUD and HD2 Crosshair package results are documented separately
in DIVER_HUD_RESEARCH.md and CROSSHAIR_MOD_RESEARCH.md. Neither supplied package yielded a
native shot-direction accessor. The user explicitly resumes the prior actual-flight route.

Test.15 already contains the necessary separate diagnostic stance budgets and eight-frame
pre-click history. Its ZIP has been rechecked for CRC, version and those recorder markers.
No extra angle/physics change or new package version is justified before this evidence.

The current log still ends with test.14. No test.15 in-game validation is claimed. The
minimal next capture remains six stationary prone shots: GR-8 and CB-9, each forward,
left and right while the lower body is kept fixed. Settle aim for about one second before
each click and allow at least one second after it. Use clear, distant terrain (roughly
60m or more) so early impacts do not truncate the 0.35s sample. Existing standing controls
are sufficient; no vehicle run or additional weapon is required. These are validation
observations for an offline fixed model, never in-game learning.

Evidence tooling now retains pre-click and post-click poses separately and compares every
pose rather than choosing the lowest-error snapshot as proof of a firing timestamp:

```powershell
.venv\Scripts\python.exe -B tools/capture_weapon_trace.py "$env:APPDATA\Arrowhead\Helldivers2\throwable_arcs.log" --version 1.1.1-test.15 --output path-to-new-capture.json
.venv\Scripts\python.exe -B tools/analyze_native_flights.py --input path-to-new-capture.json
.venv\Scripts\python.exe -B tests/test_weapon_trace_tools.py
```

The exporter separates runs even when shot numbers restart, refuses stale/missing versions
or an empty newest matching run, preserves all candidate series and refuses to overwrite
an existing output file. It does not modify the game or its logs. Seven offline integrity
tests pass. Exporting the real test.14 log exactly reproduces all five saved shot headers,
vectors, candidates, tracks, synchronized poses and summaries; GR-8 error measurements
remain unchanged. These checks validate evidence handling, not a prone accuracy fix.
