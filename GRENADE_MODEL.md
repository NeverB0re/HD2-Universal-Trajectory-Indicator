# Grenade model: data coverage and accuracy boundaries

## Sources and generation

Uses code / research from HD2Runtime by SkyeShade: https://github.com/SkyeShade/HD2Runtime

- Pinned revision: `a8c53396eb345c9fd79dae36a6f8564e85b4173a`, native snapshot build `F5FEE03DCFDB`.
- [Capability data](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/sdk/ThrowableAuthoringCapabilities.json): 23 resolved armory throwable identities, per-kind launch calibration and forward/backward strength adjustments.
- [Runtime resource identities](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/domains/throwable_authoring.lua): maps each display name to the exact thrown-unit resource. Do not guess this from a filename (e.g. Pyrotech is `zipper_grenade`, Immolation is `molotov_grenade`).
- [Native launch equation and limitations](https://github.com/SkyeShade/HD2Runtime/blob/a8c53396eb345c9fd79dae36a6f8564e85b4173a/docs/knife-melee.md).
- [Decoded component descriptions](https://github.com/shalzuth/HelldiversData/blob/0d18368a707a048d153aec7918f6c12127652283/data/components/ThrowableComponent.json): strength adjustment semantics and the 1m/s movement deadzone; `ThrowInfo.json` documents a default 5-degree lift. Defaults do not prove every caller/pose uses them.
- Caltrops are newer than that 23-item catalog. Their separate 10m/s seed is from NarrowHUD 2.0.0's 14 reported throws; it is labelled `measured`, not a fabricated native row. NarrowHUD hand-node and pose findings are in `REFERENCE_FINDINGS.md`.

The user approved the 1.7MB capability JSON download into the workspace research folder. Its Git blob hash was verified as `e4b843903962311976f0d788860568420d661cef`. Only a small launch-data subset is compiled into the mod; HD2Runtime is not installed or bundled. Full attribution/licence is shipped with the ZIP.

Regenerate with `python tools/generate_grenade_profiles.py path/to/ThrowableAuthoringCapabilities.json`. The script rejects an unreviewed build/contract or roster. `src/grenade_profiles.lua` records the source SHA256.

## Model

The native equation is `speed^2 = 18 * max(0, min + (max-min) * adjusted_strength)`, unless a positive speed override bypasses the curve. The data's min/max are calibration distances, not launch speeds or promised landing ranges.

| Profile family | Native maximum calibration |
| --- | ---: |
| Standard grenades/knife and most special grenades | 20 |
| G-48 Giga | 11 |
| G/40-K Melta Mine | 4.5 |
| TM-1 Lure Mine, G/SH-39 Shield | 4 |

The player caller's input strength is not published in that catalog. We transfer it from our existing 22.4m/s standard-grenade measurement, using the standard grenade's native min/max. This produces approximately 16.6m/s Giga, 10.6m/s Melta and 10m/s small deployables before individual overrides; those agree closely with previously obtained measurements. The transferred strength is an empirical model, not a claimed native constant. Existing kind-specific learned speeds/lifts/yaws remain authoritative over these defaults.

For native profiles, walking adjusts strength by +0.4 forward or -0.2 backward past the 1m/s deadzone, instead of adding the player's speed directly to m/s. The learner inverts that same equation. Caltrops/unknown legacy kinds keep the prior scalar carry fallback until a native curve is available. Current armour factors are preserved, and grenade-only use now triggers armour identification with rate-limited retries.

The origin follows the actual held unit in its current pose. A newly observed release learns an offset relative to that unit, not a fixed standing height above the feet. Old absolute feet measurements are retained for diagnosis but no longer dictate the rendered origin. Until relative data exists, the previous 0.4m upward release allowance is used. This allowance is an approximation, not authored per-pose animation data.

The fitter restores both position and vertical velocity to the same release-time reference. Drag correction uses the actual fit time window. The regression fixtures explicitly include 9.81m/s² gravity. Existing fixed per-kind drag values for Giga/Thermite are preserved; the native launch catalog does not expose in-flight drag/gravity for all thrown rigid bodies.

## What is and is not established

- No ownership/unlock is required to obtain the 23 static profiles. A player does not need to test every grenade to establish their basic launch-curve differences.
- 23 native profiles plus separately measured Caltrops are covered by the watcher. The two guided Seekers retain their existing exclusion from fixed ballistic arcs; homing paths are not solved by launch speed alone.
- The user confirmed Giga display works in test.2. Their slight rightward miss and possibly short moving prediction remain unquantified; summary logs do not contain raw flight positions for reconstructing those errors. No arbitrary yaw tweak was applied.
- Actual release animation, posture-dependent offsets, shared caller strength, movement application, drag and final collision/bounce still limit precision. Static profile coverage is not proof of exact landing points for every kind or posture.
- A `grenade compare` line now captures the last displayed launch state and at most 16 actual position samples, once after each throw. It adds no world scans or per-sample disk writes. This allows representative-family calibration without asking the user to own every item.
- The displayed arc is depth-tested world geometry, not a computed terrain-intersection or bounce simulation. Compare the first ground contact, not a final rolled resting place.

## Focused next check

Use only the already-owned Giga: two stationary throws and two forward-walking throws at a similar moderate aim angle with the same armour. The log is read locally afterwards; no new probe or screenshot is required. This checks common launch/offset/movement behavior, not every grenade individually. The remaining weapon-prone limitation is separate.

Holding G commits the game to throwing; it cannot be used as a manual cancel/stow or weapon-switch test. The corresponding synthetic pose-change fixture is only a defensive internal-state test.
