# Local Diver HUD reference inspection (2026-11-01)

User supplied two archives on the desktop and authorized internal analysis. No package,
helper executable, fonts or addon was installed or executed. HUD+ was not downloaded.

| Archive | SHA-256 |
| --- | --- |
| Diver-HUD-Lua51-1.2.7-with-Icons.zip | 4620a6dc89a200eed84823f66758ecc93cb53d9b50bbe2aa612e987adf2ec652 |
| Diver-HUD-ScreenHelper-1.7.6.zip | 97a402c320f0671f1a1201c37594d35116cff1abde2cf8748cc31cc60eb310ed |

Evidence inspected: manifest, Korean README, notices, addon Lua text and helper Lua
adapters/contracts. Private working copies are under `research/diver-hud` in the parent
workspace; no third-party code or assets are included in this repository or our ZIP.

The supplied 1.2.7 package is a Chef >=1.3.0 addon. Its documented features include health,
ammunition, reload/charge bars, cooked-grenade fuse, squad data, stratagem landing marks and
compass destroyer position. The documented landing marks are not a weapon trajectory preview.
Neither a dynamic weapon reticle accessor nor a ballistic flight implementation was located
in this inspection. Text searches for reticle/trajectory/ballistic, aiming-node names and
the usual crosshair terminology did not identify one; the crosshair description found was
the cooked-grenade timer's screen placement. Absence of named matches alone is not proof
that every possible indirect access path has been ruled out.

ScreenHelper documentation describes Windows Graphics Capture of requested screen regions
for stratagem cooldowns, menus, backpack bars and resupply cooldown. Its supplied Lua adapters
cover these tasks. It is not established as a native reticle-direction reader or a reticle
image tracker. Do not add an external screen helper dependency based on this reference.

The October DC post advertising reticles and trajectories must not be treated as evidence
that this later Lua51 1.2.7 package still implements those features. No all-weapon launch
formula can be derived from the inspected package. No replacement aim model is applied.

The locally retained Chef source has no named crosshair/reticle/aim-target getter in its
loader modules; `Window.ui_state` is window/UI boolean state, not reticle coordinates.
This is limited source evidence, not proof of impossibility in the native game or a newer
loader. Prioritize a supported native aim-direction/world-target accessor; 2D pixel
coordinates alone leave depth/parallax unresolved. Existing test.14 projectile recordings
remain independent validation data for any future direction accessor.
