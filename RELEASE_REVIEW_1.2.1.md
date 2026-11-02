# Release review: 1.2.1

Reviewed 2026-11-02 against the previous stable release, 1.2.0.

## Accepted changes

- Suppress weapon overlays on the ship and reject empty-hand poses.
- Compare player weapon roots before applying ballistic support filtering; a nearby holstered supported gun cannot bypass a stronger unsupported candidate. Exact ambiguous candidates produce no overlay.
- Include 107 asset-listed player weapon roots for identification. This does not add trajectory models for unsupported weapons.
- Rename source/development files and the new log; retain resource identity, settings keys and manifest Guid for compatibility.
- Publish matching English/Korean changelog and Nexus description source. Preserve prior release notes and ZIP.

## Evidence

- The user accepted test.3 after testing; test.2's ship/emplacement suppression was separately confirmed. The saved log records test.3 on Chef 1.5.1 and unsupported chemgun/energy-weapon candidates being rejected.
- All 206 main tests and 7 trace-evidence tests pass on the release source.
- 13 additional checks executed the actual Lua extracted from the final ZIP, covering ship/emplacement hands, unsupported weapons, cache invalidation, no-hand fallback, prone aiming, first-person geometry, weapon arcs and the C4 icon toggle.
- The 107-root catalog matches the existing Filediver listing (`generate_weapon_units.py --check`). Runtime uses the existing shared watch at its existing 0.5 s interval. The per-frame candidate loop covers watched weapon instances, not 107 global world scans; it must compare candidates to prevent cache bypass.
- Before normal stable-build stripping, accepted gameplay source 716bcf4 differs only in VERSION. The packaged Lua exactly matches build.py's stable output.
- All development collectors and their hooks are absent from the final package. Archive structure, six ZIP entries, resource hash, manifest Guid and ZIP integrity pass. Existing 1.2.0 ZIP is unchanged.
- Test.3 loader samples show average 0.060-0.238 ms and maxima up to 53 ms. These include development collectors and do not establish stable-package frame-time maxima or a controlled performance comparison.

## Artifact

- `release/Universal Trajectory Indicator v1.2.1.zip`: 88,535 bytes.
- SHA-256: `d15a14395c57c78db647f376acc785c755ccdb99997d0d7c325930ddddf0a6e5`.
- GitHub release notes: `release/RELEASE_NOTES_1.2.1.md`.
- Nexus description: `PUBLISH_NEXUS.txt`; English/Korean changelogs: `NEXUS_EXTRAS.txt`.

## Scope limits

The existing positional/directional held-weapon identification remains an inference, not an exact equipped-unit API. New asset kinds need catalog maintenance. This release does not prove complete coverage of every game weapon, non-host multiplayer, all camera mods or all terrain intersections. These remain maintenance work under the project's full coverage objective, not claims established by this patch. Nexus upload is performed by the user as agreed; local description/changelog updates alone do not establish a published Nexus update.
