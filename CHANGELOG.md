# Changelog

## 1.2.1 — 2026-11-02

Changes from 1.2.0:

- Fix weapon arcs appearing while on the ship or operating an emplacement.
- Fix unwanted arcs below unsupported weapons, including the Sterilizer and Cremator, when aiming high or diving.
- Improve held-weapon detection so a holstered supported weapon cannot override the weapon actually being aimed.
- New logs use universal_trajectory_indicator.log. Existing settings and learned grenade throws carry over.
- Trajectory physics and grenade calibration are unchanged from 1.2.0.

Validation: user gameplay acceptance of 1.2.1-test.3 with Chef Shared Loader 1.5.1; automated checks and stable-package checks recorded in RELEASE_REVIEW_1.2.1.md.

## 1.2.0

- Renamed the mod to Universal Trajectory Indicator.
- Read weapon aim targets from the game instead of stance/distance corrections.
- Added optional first-person arcs, aim circles for selected rifles, per-weapon switches, arc width and solid arcs.

Earlier release notes are retained in NEXUS_EXTRAS.txt.
