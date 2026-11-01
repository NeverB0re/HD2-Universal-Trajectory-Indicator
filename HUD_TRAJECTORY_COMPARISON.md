# External HUD trajectory methods: 2026-11-01

Research only. Runtime Lua and the test.10 package are unchanged. No mod/source package download or game experiment.

## Sources actually inspected

- NarrowHUD pinned commit `6802a892a31fedb8fa7bf25d2de5226824dccc97`,
  [12_drop.lua](https://github.com/luka189/NarrowHUD/blob/6802a892a31fedb8fa7bf25d2de5226824dccc97/src/modules/12_drop.lua).
  This module is newer than the locally retained NarrowHUD source snapshot, which did not contain its drop module.
- [HUDdle author description/changelog](https://www.nexusmods.com/helldivers2/mods/18108?tab=description).
  Description evidence only; its runtime source was not inspected. It describes aiming from muzzle to the point
  under the crosshair and corrections for landing alignment. This does not establish a proven all-weapon API.
- HUD Ballistic Trajectory Overlay DX11 repository was located, but GitHub connector access returned 404 and
  browser text did not expose the Lua body. Do not infer its direction implementation from the feature list.

## NarrowHUD mechanism and approximations

The inspected module constructs a target 100m along the camera forward ray, then points from the right-hand node
toward that target. Its launch origin is approximated forward/sideways from the hand, rather than read from each
weapon's animated muzzle. It does not use a weapon-root yaw bias per stance for this direction calculation.

It numerically integrates gravity and quadratic drag using per-projectile speed, mass, diameter, drag and gravity
factor data. Its pitch-based flight cache uses half-degree keys. These are ideas to evaluate, not copied source.
Caching resolution can itself affect aim accuracy and should be selected from an error budget.

The displayed line skips the near part: generally 10m of path, or 3m for slow lobbed projectiles. That helps conceal
origin mismatch and is incompatible with our requirement to show the correct trajectory from the actual muzzle.
Do not reproduce that omission. Keep the actual muzzle-node work already confirmed by the user.

Conceptual common direction candidate: choose a target along the camera ray and normalize target minus the actual
muzzle position. A real engine aim/target intersection would be preferable to assuming a universal 100m distance.
A nearby obstruction, weapon aim lag and passenger camera geometry require separate validation. This is geometric
convergence, not trial-and-error per-weapon angle learning; camera/muzzle changes still update the resulting vector.

## Existing-data comparison (horizontal only)

Inputs: all GL-21 flights with at least two recorded positions in weapon_direction_test6/test8/test9 fixtures.
No claim that these are all stationary, independent validation samples, or new test runs. Fourteen of these records
were already used when fitting the current fixed profiles. Actual heading is the XY displacement between first and
last observations. The comparison uses actual recorded muzzle position, unlike NarrowHUD's approximate hand origin.

| Context | Samples | Direction model | Mean absolute yaw error | Maximum absolute yaw error |
| --- | ---: | --- | ---: | ---: |
| on foot | 23 | current fixed root-angle profiles | 0.433deg | 4.482deg |
| on foot | 23 | camera-parallel | 0.229deg | 0.785deg |
| on foot | 23 | actual muzzle toward camera ray at 100m | 0.182deg | 0.680deg |
| vehicle | 3 | current fixed root-angle fallback | 0.412deg | 0.457deg |
| vehicle | 3 | camera-parallel | 0.866deg | 1.862deg |
| vehicle | 3 | actual muzzle toward camera ray at 100m | 0.726deg | 1.443deg |

This is evidence for investigating a shared on-foot direction model. It is not evidence for replacing all aiming
with screen-center convergence: the vehicle comparison gets worse, no GR-8 projectile was tracked, and this table
does not validate vertical pitch, release timing, movement inheritance, nearby obstructions or rapid-turn aim lag.
Existing corner observations also warn against blindly forcing a lagging/deflected weapon toward screen center.

## Development implication

Prioritize a shared muzzle-to-aim-target direction method over growing a separate empirical yaw table for every
weapon. Retain weapon-specific projectile physics. Preserve current source behavior until a comparison candidate
handles the confirmed muzzle/prone work and relevant aim-lag/vehicle cases. Use the existing recorded flights first;
ask for only representative live checks needed to resolve remaining cases. No runtime feature removal, new test
build or remote push was performed for this research.


## Implementation boundary discovered after approving the common method

The user's acceptance explicitly requires any stance, target location and distance, without learning on equip.
The inspected Chef Shared Loader documentation at commit `400cc03aa558f30b5f84c6c0e7f840b4fb8e92ba` states
that its Lua API has no world raycast; `ray_box` tests a supplied box or a unit's own box only:
https://github.com/Th3chef/Chef-Shared-Loader/blob/400cc03aa558f30b5f84c6c0e7f840b4fb8e92ba/README.md
https://github.com/Th3chef/Chef-Shared-Loader/blob/400cc03aa558f30b5f84c6c0e7f840b4fb8e92ba/CHANGELOG.md
This does not prove that no engine/native alternative exists. It does mean a fixed-distance camera-ray target
cannot be represented as the actual target intersection, and unit boxes alone miss terrain/walls/rocks.

The direction operation itself is universal and stateless: normalize(actual target minus animated muzzle).
To use it faithfully at any distance requires a verified actual aim target or equivalent shot-direction provider.
The user also requires real weapon aim lag to remain correct: screen center alone is not proof of the current
barrel's fire direction while turning or next to an obstruction. No production direction replacement was applied.

`tools/compare_aim_models.py --distance 100` now reproduces the preceding saved-flight comparison without
running the game or downloading a package. It separates the immutable convergence-distance assumption from the
live muzzle/camera inputs, and contains no calibration state. It supports other positive distances for analysis;
choosing a best distance from these samples does not prove all-distance accuracy. The full goal remains open.

A 100m convergence test build would be a bounded approximation experiment and requires the user's acceptance of
that narrower scope under their rule about indirect approaches. Otherwise continue investigating an actual
engine aim-target/direction path before replacing confirmed production behavior. No new in-game experiment is
requested to establish the documented API limitation.
