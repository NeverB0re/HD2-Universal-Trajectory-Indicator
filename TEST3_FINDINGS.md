# Test.3 flight analysis and test.4 correction

2026-10-31. User observations and local `throwable_arcs.log`, Chef 1.4.1, test.3.

The 29 comparisons comprise 9 Giga, 13 Melta and 7 Impact throws. User reports remain the evidence for the visible result; the measurements below explain observed model errors without claiming a newly validated game fix.

## Findings

1. **Giga direction bias:** interpolating the drawn curve at matching horizontal forward distance gives early actual points slightly left of the displayed path and later points to its right. Fitting recorded points from roughly 0.16–0.8s gives a horizontal direction 1.77–3.74 degrees right of the old displayed direction, with 0.038–0.117m three-dimensional fit RMS. A fit based only on the first short segment therefore perpetuates the leftward bias. The observed unit-root path varies through flight; its cause (spin/root offset, smoothing or true motion) is not proven, so no speculative sideways-force formula was added.
2. **Melta learning failure:** the first 0.1–0.15s contains hand movement followed by a discontinuous transition into flight. The old fitter could pick an initially steady pair inside this motion, reject the resulting fit, and never try a genuine airborne window. Only 3 of 13 throws were accepted, all moving throws; standing lift stayed at its older 4.5-degree value. In most standing records, actual height at matched forward distance is roughly 0.7–1.0m above the old curve around 6–9m forward, consistent with the user's longer landing observation. These are airborne comparisons, not a terrain-distance benchmark.
3. **Different reference hand poses:** the last displayed preview and the first fast-motion snapshot differ by about 0.145–0.148s for most Giga/Impact throws, and about 0.036–0.038s for Melta. Test.3 learned a relative release offset against the later swing-hand position but applied it to the earlier displayed held position. This can shift the start even if fitted world coordinates are reasonable.
4. **Impact convergence:** all 7 Impact throws were accepted; the logged standing lift moves from the mixed old value toward approximately 5.3 degrees after the first two measurements. This agrees with the user's report of better alignment from about the third throw, but does not prove that every pose is accurate.

## Implemented correction

- Select an early airborne start in 0.15–0.2s, verify following motion rather than the incoming hand jump, fit up to 0.65s, and retry eligible candidate starts. Require at least 0.25s of fit data, keep the 0.15m RMS gate, and stop at sharp speed loss. Very short/collided flights do not become calibration; their existing arcs/native profiles remain available.
- Use the actual last displayed hand anchor and camera basis for learning when the preview is fresh (at most 0.25s old). Keep the release-time reference for fitting position and velocity consistent.
- Back up incompatible angle/relative-origin histories per kind in `fit_backups` on the first accepted revision-2 fit. Preserve speed samples and other kinds. Retain the backup and revision through save/reload. No local AppData was modified during development.
- Preserve native per-kind profiles, automatic learning, stratagem/C4 behavior and the current weapon behavior. The user's ordinary/prone muzzle-origin report is in the deferred weapon milestone.

## Verification and limits

| Kind | Test.3 actual accepted fits | Test.4 offline replay accepted fits |
| --- | ---: | ---: |
| Giga | 6 / 9 | 9 / 9 |
| Melta | 3 / 13 | 12 / 13 |
| Impact | 7 / 7 | 7 / 7 |

Three translated recorded-flight fixtures are committed under `tests/fixtures/`; there is no real-world/player-location information. Main fake-loader suite: 110 tests passed, including ballistic 30/60/120fps cases, recorded flights and the display-hand/swing-hand mismatch. Replay uses the sparse logged points; actual full-rate fit choices and live landing accuracy still require runtime confirmation. Increased fit acceptance is not itself proof of an accurate final trajectory.

For an upstream API alternative, [Stingray's Actor documentation](https://help.autodesk.com/cloudhelp/ENU/Stingray-Help/lua_ref/obj_stingray_Actor.html) describes physics velocity and center-of-mass reads. Their availability/semantics in this Helldivers build are unproven. No Actor calls or stored physics handles were added merely on that documentation's basis.
