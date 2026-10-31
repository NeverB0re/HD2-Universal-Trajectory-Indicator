# Reference findings for equipment/release detection

Checked 2026-10-31. Public source was read through GitHub; no additional mod archive was downloaded or installed.

## NarrowHUD 2.0.0

Pinned source: [597968c2b9e556812e0376b8a6627926df1f2524](https://github.com/luka189/NarrowHUD/commit/597968c2b9e556812e0376b8a6627926df1f2524).

- [12_throw.lua](https://github.com/luka189/NarrowHUD/blob/597968c2b9e556812e0376b8a6627926df1f2524/src/modules/12_throw.lua) uses the Helldiver's `attach_hand_r` node and a 0.8m three-dimensional hand radius to identify grenade kinds. This is better evidence than a feet-only cylinder and works with a lowered hand. Its measured equipment poses include 41 for standard grenades, 40 for several mines, and 42 for Melta/Giga. We therefore do not require pose 41 exclusively.
- [05_hand.lua](https://github.com/luka189/NarrowHUD/blob/597968c2b9e556812e0376b8a6627926df1f2524/src/modules/05_hand.lua) excludes throwable poses from weapon selection. We use the same distinction plus continuous proximity checks on our cached weapon.
- The same file documents that the session unit synchronizer returned no avatar unit in their hosted/joined games; current NarrowHUD also falls back to the Helldiver nearest the camera. This is upstream evidence, not our own validation. We did not add repeated network mapping probes or claim the multiplayer identity ambiguity is solved.
- Their throw implementation falls back to a standard grenade or remembered kind when no unit is currently confirmed. Our existing requirement for an actual grenade unit is retained, avoiding an arc for an empty grenade slot.
- Their throw speeds, armour factors and release offsets differ from our fitted model. We did not replace our existing stratagem/C4 calibration with those numbers. Trajectory fitting is a later milestone, separate from selection.
- Based on NarrowHUD by luka189. Its full licence is already included in `THIRD_PARTY_NOTICES.txt`, including in the built ZIP.

## Chef Shared Loader

[Official API documentation](https://github.com/Th3chef/Chef-Shared-Loader/blob/main/docs/MODDING.md) describes `chef.watch` as a list spread over frames with a refresh request; `refresh()` is not proof that a newly created unit can be read immediately. The new code requests a bounded refresh on relevant input/pose transitions and waits for a real candidate. It does not force a world scan every frame or invent a generic grenade before detection.

The short-input test models a delayed refresh, not a guarantee of every quick throw on the actual installed loader. The runtime check must establish whether a grenade's short-lived in-hand unit is observed in time. If it is not, inspect loader list timing before inventing another game-level experiment or changing the no-unit/no-arc rule.

## HUDdle

[HUDdle's public page](https://www.nexusmods.com/helldivers2/mods/18108) describes trajectories and credits NarrowHUD for weapon/hand reading. Its page requires author permission for modifying/reusing its assets. No package or implementation from HUDdle was imported. NarrowHUD's public source provides the hand-detection method needed for this milestone, so no download request is currently necessary.
