# Supplied HD2 Crosshair package (2026-11-01)

Inspected `C:\Users\JMS\Desktop\HD2-Crosshair.zip`, supplied by the user for method
research. SHA-256: `1a9a017aee39d471a20a97e27c808037fa36ed659713a44d4c212e812b8328b1`.
ZIP CRC validation passed. Nothing was installed or executed; game files are unchanged.
Private inspection artifacts are in the parent workspace's `research/hd2-crosshair`.
No third-party source or game-data payload is redistributed in this repository.

## What it does

The manifest offers two independent choices:

- Crosshair: third person for R-40 Sightliner, APW-1 Anti-Materiel Rifle and AMW-20 Apex;
  first person for B/FLAM-80 Cremator, GL-28 Belt-Fed Grenade Launcher and M-1000 Maxigun.
- Nova: substitutes AMR draw/holster animation references for LAS-44 Nova, per README.

The approximately 14KB bootstrap implements a file-data selector/transaction, not a reticle
renderer. Its target is `data/game/generated_entities.dl_bin`. The payload is pinned to
Steam build 26251122 and contains a 47,259,444-byte original plus a 47,259,456-byte candidate
and small option edits. This accounts for nearly all of the approximately 94.6MB archive.
The small Crosshair/Nova `.stream` files are selection tokens, not drawing code.

At startup it scans deployed patch slots, resolves selected profiles, validates the existing
target against known original/candidate bytes and stages a verified replacement. It retains
an original sidecar and uses temporary/rollback files. Its shutdown hook restores the original
profile on a normal exit. The README specifically describes recovery after forced exit and
warns against stacking other boot/data replacements. The inspected code supports these file
lifecycle claims, but no live install/restore was tested.

The pool's crosshair-off option has six one-byte edits relative to its crosshair-on base;
the on option has no extra edits. Nova-on has two four-byte reference edits. These are
profile-relative binary edits, NOT proven direct edits of six one-byte boolean fields:
the native record layout/member semantics have not been decoded here. Do not misreport
them as the older HD2Runtime `crosshair_type` enum change without that extra evidence.

## Relevance to trajectory direction

The bootstrap contains no per-frame reticle/aim-target reader, world-to-screen projection,
projectile tracker or reticle drawing routine. Its render/update callbacks preserve existing
callbacks or use no-ops. This is native-reticle activation through data configuration; the
game itself supplies whatever reticle behavior the selected data enables.

Consequently this package does not expose the world direction/target behind the circular
reticle, and it does not provide a replacement for our prone launch-direction calculation.
Enabling a hidden reticle and reading its live coordinates are different capabilities.
No additional installation or firing experiment is justified merely to establish the
bootstrap's method. Existing projectile captures remain the reference for evaluating a
future native aim accessor. No trajectory constants or runtime behavior were changed.
