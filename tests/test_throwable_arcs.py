"""Stratagem and C4 Trajectory on PUC Lua 5.1 (lupa) against a fake Chef Shared Loader:  python tests/test_throwable_arcs.py"""
import importlib.util
import json
import math
import os
import re
import unittest

import lupa.lua51 as lua51

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "..", "src", "throwable_arcs.lua")
_spec = importlib.util.spec_from_file_location("ta_build", os.path.join(HERE, "..", "build.py"))
ta_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ta_build)   # the mod's build.py: the source with its armour table in

FAKE = r"""
local fake = { t = 0, logs = {}, down = {}, pressed = {}, mouse = {}, wheel = 0, lines = {}, calls = {}, cam = nil,
               watches = {}, saved = {}, opts = {}, changes = {}, shapes = {}, settings = {} }
local world = newproxy(true)

local PLAYER = '4d1c334d294dfa97'
fake.me = { kind = PLAYER, x = 0, y = 0, z = 0 }
fake.mine = { kind = '465f4895f3dc98d1', x = 0.2, y = 0.3, z = 1.6 }   -- my backpack
fake.runtime = { kind = '46cab355bd8d4d37', x = 1, y = 1, z = 1 }
fake.units = { fake.me, fake.mine, fake.runtime }

local E = {
  ['World.units'] = function() local out = {}; for i, u in ipairs(fake.units) do out[i] = u end; return out end,
  -- every type declares the fields the mod reads (C4's options, owner and carry, a fire mode, the player's avatar)
  ['Network.object_info'] = function(t)
    return { fields = { { id = '31f86165' }, { id = '3ccffa7f' }, { id = '788b9753' }, { id = '49c250a6' },
                        { id = '0f27c68e' } } }
  end,
}
fake.E = E
local function call(name, ...)
  fake.calls[name] = (fake.calls[name] or 0) + 1
  local f = E[name]
  if not f then return nil, 'missing' end
  local r = { pcall(f, ...) }
  if not r[1] then return nil, 'error: ' .. tostring(r[2]) end
  return r[2], r[3], r[4], r[5]
end

chef = {
  api = 3, loader_version = '1.2.1',
  has = function() return true end, own_log = function() return true end,
  log = function(fmt, ...) fake.logs[#fake.logs + 1] = string.format(fmt, ...) end,
  time = function() return fake.t end,
  call = call, call_kind = function(name, kind, ...) return call(name, ...) end,
  world = function() return world end, world_id = function() return 4 end, in_mission = function() return false end,
  camera = function() return fake.cam end,
  unit_alive = function(u) return u.dead ~= true end,
  unit_kind = function(u) return u.kind end,
  unit_rotation = function(u, node)
    local f = node and u.node_f and u.node_f[node] or u.f
    if f then return f[1], f[2], f[3], 0 end
  end,
  unit_position = function(u, node)
    if u.kind == '46cab355bd8d4d37' then error('NATIVE CRASH: asked a runtime-built unit') end
    if node and u.nodes and u.nodes[node] then
      local p = u.nodes[node]; return p[1], p[2], p[3]
    end
    return u.x, u.y, u.z
  end,
  unit_node = function(u, name)
    fake.node_lookups = (fake.node_lookups or 0) + 1
    if u.named_nodes then return u.named_nodes[name] end
    if name == 'attach_hand_r' and u.nodes and u.nodes[7] then return 7 end
  end,
  watch = function(kinds)
    local w = { items = {}, kinds = kinds, active = true, lists = 0 }
    function w.stop() fake.watch_stopped = true end
    function w.pause() w.active = false end
    function w.resume() w.active = true end
    function w.refresh()
      w.refreshes = (w.refreshes or 0) + 1
      if fake.watch_period then w.next_list = math.min(w.next_list or 0, fake.t + 1 / 60) end
    end
    fake.watches[#fake.watches + 1] = w
    return w
  end,
  key_down = function(k) return fake.down[k] == true end,
  key_pressed = function(k) return fake.pressed[k] == true end,
  mouse_down = function(b) return fake.mouse[b] == true end,
  wheel = function() return fake.wheel end,
  line = function(x1, y1, z1, x2, y2, z2, c)
    fake.lines[#fake.lines + 1] = { x1, y1, z1, x2, y2, z2 }
    fake.line_color = c
  end,
  color = function(r, g, b, a) return { r, g, b, a } end,
  screen = function() return 1920, 1200 end,
  lights = function() return 0 end,
  save_table = function(name, t)
    fake.save_calls = (fake.save_calls or 0) + 1
    if fake.save_fail_name == name then return false, 'test: disk full' end
    fake.saved[name] = t; return true
  end,
  load_table = function(name)
    if fake.load_fail_name == name then return nil, 'test: parse failed' end
    return fake.saved[name]
  end,
  title = function() end,
  TOP = 100000,
  option = function(id, spec)
    local v = fake.opts[id]
    if v == nil then v = spec.default end
    return v
  end,
  on_change = function(id, fn) fake.changes[id] = fn end,
  rect = function(...) fake.shapes[#fake.shapes + 1] = 'rect' end,
  triangle = function(...) fake.shapes[#fake.shapes + 1] = 'triangle' end,
  circle = function(...) fake.shapes[#fake.shapes + 1] = 'circle' end,
  ring = function(...) fake.shapes[#fake.shapes + 1] = 'ring' end,
  setting = function(path) return fake.settings[path] end,
  bitmap = function(tex, x, y, w, h, c, layer)
    if fake.no_bitmap then return false end
    fake.shapes[#fake.shapes + 1] = 'bitmap ' .. tex
    return true
  end,
  texture_sizes = function(map) fake.sizes = map end,
  bind = function(id, default)
    fake.bound = fake.bound or default
    return { key = function() return fake.bound end, down = function() return fake.down[fake.bound] == true end }
  end,
}

function fake.look(pitch_deg)
  local p = math.rad(pitch_deg)
  fake.cam = { x = 0, y = 0, z = 2, fx = math.cos(p), fy = 0, fz = math.sin(p), fov = 0.96 }
end
fake.look(0)

function fake.frame(M, dt)
  fake.t = fake.t + dt
  if fake.ball and not fake.ball.still then
    local b, f = fake.ball, fake.t - fake.ball.t0
    if f < 0.1 then
      b.x, b.y, b.z = 0.4 - f * 3, -0.3, 1.5   -- still the hand's swing: back, before the throw
    else
      f = f - 0.1
      b.x, b.y, b.z = 1.0 + b.vx * f, 0, 2 + b.vz * f - 0.5 * b.g * f * f
      if b.z <= 0 then b.z, b.still = 0, true end   -- lands and stays: its velocity jumps to 0
    end
  end
  for _, w in ipairs(fake.watches) do
    if w.active and (not fake.watch_period or fake.t >= (w.next_list or 0)) then
      w.items, w.lists = {}, w.lists + 1
      w.next_list = fake.t + (fake.watch_period or 0)
      for _, u in ipairs(fake.units) do if w.kinds[u.kind] then w.items[#w.items + 1] = { unit = u, kind = u.kind } end end
    end
  end
  fake.lines, fake.shapes = {}, {}
  M.update(dt)
  fake.pressed, fake.wheel = {}, 0
end

-- thrown now: the ball in hand flies from 0.1 s on (test.13: no other ball appears); before, the hand swings it
function fake.throw(kind, speed, pitch_deg, g, held)
  local p = math.rad(pitch_deg)
  local b = held or { kind = kind }
  b.t0, b.vx, b.vz, b.g, b.still, b.x, b.y, b.z = fake.t, speed * math.cos(p), speed * math.sin(p), g, nil, 0.4, -0.3, 1.5
  fake.ball = b
  if not held then fake.units[#fake.units + 1] = b end
end
return fake
"""


class ArcTest(unittest.TestCase):
    def setUp(self):
        self.lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.fake = self.lua.execute(FAKE)
        self.M = self.load()

    def load(self):
        return self.lua.execute(ta_build.built_source(), self.lua.globals().chef)

    def frames(self, n, dt=1 / 60):
        for _ in range(n):
            self.fake.frame(self.M, dt)

    def lines(self):
        return [tuple(l.values()) for l in self.fake.lines.values()]

    def logs(self):
        return "\n".join(self.fake.logs.values())

    def add_unit(self, kind, x, y, z):
        return self.lua.eval("function(f, k, x, y, z) local u = { kind = k, x = x, y = y, z = z }; "
                             "f.units[#f.units + 1] = u; return u end")(self.fake, kind, x, y, z)

    def ball_watch(self):
        return [w for w in self.fake.watches.values() if w.kinds["16f397ca5f51f271"]][-1]

    def stratagem_key(self, key="left ctrl"):
        self.fake["down"][key] = True
        self.frames(20)
        self.fake["down"][key] = False
        self.frames(20)

    def ready_ball(self, at=(-0.05, -0.3, 1.5)):
        """A ball in my right hand: held 0.35 m farther ahead while its code goes in, then pulled back (lit)."""
        ball = self.add_unit("16f397ca5f51f271", at[0] + 0.35, at[1], at[2])
        self.frames(6)
        self.lua.eval("function(b, x) b.x = x end")(ball, at[0])
        self.frames(6)
        return ball

    def aim(self, pitch=10, at=(-0.05, -0.3, 1.5)):
        self.stratagem_key()
        self.fake.look(pitch)
        self.ball = self.ready_ball(at)
        self.fake["mouse"]["left"] = True
        self.frames(2)

    # ------------------------------------------------------------------ grenades (1.1.0)
    def nade_in_hand(self, kind):
        """a grenade of KIND in my right hand (a unit, as the game makes one from G down)"""
        return self.add_unit(kind, 0.3, -0.3, 1.5)

    def throw_nade(self, nade, speed, frames=200, extra=None):
        """let go horizontally with gravity, at SPEED for FRAMES frames (no terrain in this fixture)."""
        self.lua.eval("""function(f, n, v, s) local elapsed = 0; f.fly = function()
          n.x = n.x + v / 60
          n.z = n.z - 9.81 * (elapsed + 1 / 120) / 60; elapsed = elapsed + 1 / 60
          if s then s.x = s.x + 3 / 60 end end end""")(self.fake, nade, speed, extra)
        for _ in range(frames):
            self.fake.fly()
            self.frames(1)

    def test_no_grenade_no_arc(self):
        self.fake["down"]["g"] = True                 # test.17 drew an arc from the air with no grenade to throw
        self.frames(20)
        self.assertEqual(self.lines(), [])

    def test_a_grenade_arc_while_g_is_held_and_its_throw_learned(self):
        nade = self.nade_in_hand("db922a7afc42894b")  # an Arc grenade
        self.fake["down"]["g"] = True                 # 1.1.0: held, the grenade is "cooked"; its arc shows
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.fake["down"]["g"] = False
        self.throw_nade(nade, 18)
        self.assertRegex(self.logs(), r"grenade db922a7afc42894b thrown: 1[78]\.\d m/s \+\d\.\d deg up \+0\.0 right, "
                                      r"from 0\.[2-4]\d ahead 0\.30 right 1\.[45]\d up; now 22\.2 m/s")
        saved = self.fake.saved["grenade_throws6"]
        self.assertAlmostEqual(saved.known["db922a7afc42894b"].speed[4], 18, delta=0.5)

    def test_a_grenade_drawn_with_its_key_and_aimed(self):
        self.nade_in_hand("c5c05fcb5747c799")
        self.fake["mouse"]["right"] = True            # aimed (or cooked with left)
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)

    def test_a_long_cooked_grenade_and_its_spoon(self):
        nade = self.nade_in_hand("c5c05fcb5747c799")
        self.fake["down"]["g"] = True
        self.frames(180)                              # 3 s
        self.fake["down"]["g"] = False
        spoon = self.add_unit("3e433ad461c14d69", 0.3, -0.3, 1.5)   # (not a throwable: never taken for one)
        self.throw_nade(nade, 20, extra=spoon)
        self.assertRegex(self.logs(), r"grenade c5c05fcb5747c799 thrown: (19|20|21)\.\d m/s")
        self.assertNotIn("3e433ad461c14d69", self.logs().split("catch:")[0])

    def test_a_grenade_steady_only_on_the_ground_isnt_learned(self):
        nade = self.nade_in_hand("ee4c107b941ab7f4")  # a Melta mine
        self.fake["down"]["g"] = True
        self.frames(3)
        self.fake["down"]["g"] = False
        # off the hand at 12 m/s, then it bounces about for half a second and slides steadily (test.19)
        self.lua.eval("""function(f, n) local k = 0; f.fly = function()
          k = k + 1
          if k <= 1 then n.x = n.x + 12 / 60
          elseif k <= 30 then n.z = 1.5 + 0.3 * (k % 2); n.x = n.x + (k % 3) * 0.05
          else n.x = n.x + 8 / 60 end
        end end""")(self.fake, nade)
        for _ in range(200):
            self.fake.fly()
            self.frames(1)
        self.assertRegex(self.logs(), r"grenade ee4c107b941ab7f4 thrown: not measured \((steady only|no steady|not a throw)")

    def test_a_seeker_grenade_gets_no_arc(self):
        self.nade_in_hand("2d398d1ec35e0838")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])

    def right_hand_at(self, x=0.3, y=-0.3, z=1.5):
        self.fake.me.nodes = self.lua.table_from({7: self.lua.table_from([x, y, z])})

    def test_grenade_by_my_feet_is_not_the_one_in_my_hand(self):
        self.right_hand_at()
        self.hand_pose(41)
        self.add_unit("7686544f539bb9b7", 0.2, -0.1, 0.3)
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])
        self.assertNotIn("grenade hand:", self.logs())

    def test_hand_proximity_picks_the_held_kind_over_a_nearer_mine_at_my_feet(self):
        self.right_hand_at()
        self.hand_pose(41)
        self.add_unit("46333fc9e3d4bd34", 0.1, -0.1, 0.3)
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.assertIn("grenade hand: 7686544f539bb9b7 (pose 41, hand node)", self.logs())
        self.assertNotIn("grenade hand: 46333fc9e3d4bd34", self.logs())

    def test_a_nearby_grenade_does_not_draw_in_a_weapon_hand_pose(self):
        self.right_hand_at()
        self.hand_pose(10)
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])

    def test_a_fast_hand_swing_keeps_the_grenade_arc_without_learning_a_throw(self):
        self.right_hand_at()
        self.hand_pose(41)
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        for i in range(1, 6):
            nade.x = .3 + .2 * i
            self.fake.me.nodes[7][1] = nade.x
            self.frames(1)
            self.assertGreater(len(self.lines()), 20)
        self.frames(180)
        self.assertNotIn("grenade release:", self.logs())
        self.assertIsNone(self.fake.saved["grenade_throws6"])

    def test_low_prone_grenade_is_found_at_the_hand_without_a_feet_height_cutoff(self):
        self.right_hand_at(z=0.05)
        self.hand_pose(41)
        self.add_unit("7686544f539bb9b7", .3, -.3, .05)
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)

    def test_mines_and_underhand_grenades_accept_their_actual_hand_poses(self):
        for pose, kind in ((40, "2968deba6d6c2f09"), (42, "ee4c107b941ab7f4"), (42, "46333fc9e3d4bd34")):
            with self.subTest(pose=pose, kind=kind):
                self.setUp()
                self.right_hand_at()
                self.hand_pose(pose)
                self.nade_in_hand(kind)
                self.fake["down"]["g"] = True
                self.frames(3)
                self.assertGreater(len(self.lines()), 20)

    def test_unexpected_pose_change_without_separation_does_not_start_a_flight(self):
        # Defensive state-transition fixture, not an action possible while holding G in the actual game.
        self.right_hand_at()
        self.hand_pose(41)
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.fake.grip = 10
        self.frames(200)
        self.assertLessEqual(len(self.lines()), 1)
        self.assertNotIn("grenade release:", self.logs())
        self.assertIsNone(self.fake.saved["grenade_throws6"])

    def test_confirmed_release_uses_early_samples_and_the_aim_before_separation(self):
        self.right_hand_at()
        self.hand_pose(41)
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.fake["down"]["g"] = False
        for _ in range(2):
            nade.x += 22 / 60
            self.frames(1)
        # A camera turn before separation must not turn this already-started throw into a backwards measurement.
        self.fake.cam.fx = -1
        self.throw_nade(nade, 22)
        self.assertIn("grenade release: 7686544f539bb9b7 (separated from hand node)", self.logs())
        k = self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"]
        self.assertAlmostEqual(k.speed[2], 22, delta=.5)
        self.assertAlmostEqual(k.yaw[1], 0, delta=.1)
        self.assertAlmostEqual(k.ahead[1], .3, delta=.05)

    def test_a_flight_is_not_learned_across_respawn(self):
        self.right_hand_at()
        self.hand_pose(41)
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.throw_nade(nade, 22, frames=5)
        self.fake.me.dead = True
        self.fake.me = self.add_unit("4d1c334d294dfa97", 0, 0, 0)
        self.right_hand_at()
        self.throw_nade(nade, 22)
        self.assertIsNone(self.fake.saved["grenade_throws6"])

    def test_release_confirmation_keeps_ballistic_samples_at_different_frame_rates(self):
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                self.setUp()
                self.right_hand_at()
                self.hand_pose(41)
                nade = self.nade_in_hand("7686544f539bb9b7")
                self.fake["down"]["g"] = True
                self.frames(3, 1 / fps)
                self.fake["down"]["g"] = False
                vx, vz = 22 * math.cos(math.radians(5)), 22 * math.sin(math.radians(5))
                for i in range(1, 3 * fps + 1):
                    t = i / fps
                    nade.x, nade.z = .3 + vx * t, 1.5 + vz * t - 4.905 * t * t
                    self.frames(1, 1 / fps)
                row = self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"]
                self.assertAlmostEqual(row.speed[2], 22, delta=.5)
                self.assertAlmostEqual(row.ahead[1], .3, delta=.05)
                self.assertAlmostEqual(row.lift[1], 5, delta=.001,
                                       msg="vertical velocity must be restored to the release time")

    def test_walking_throw_learning_inverts_the_native_strength_model(self):
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                self.setUp()
                self.right_hand_at()
                self.hand_pose(41)
                nade = self.nade_in_hand("7686544f539bb9b7")
                self.fake.look(25)
                self.fake["down"]["g"] = True
                for _ in range(fps // 2):
                    self.fake.me.x += 2.2 / fps
                    nade.x = self.fake.me.x + .3
                    self.fake.me.nodes[7][1] = nade.x
                    self.frames(1, 1 / fps)
                start = nade.x
                self.fake["down"]["g"] = False
                # Native authored curve: +0.4 strength over a 19.9m calibration span adds 143.28 to speed^2.
                launched = math.sqrt(22 * 22 + 143.28)
                vx, vz = launched * math.cos(math.radians(30)), launched * math.sin(math.radians(30))
                for i in range(1, 3 * fps + 1):
                    t = i / fps
                    self.fake.me.x += 2.2 / fps
                    self.fake.me.nodes[7][1] = self.fake.me.x + .3
                    nade.x, nade.z = start + vx * t, 1.5 + vz * t - 4.905 * t * t
                    self.frames(1, 1 / fps)
                row = self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"]
                self.assertAlmostEqual(row.speed[2], 22, delta=.001)
                self.assertAlmostEqual(row.walk[1], 5, delta=.001)

    def test_grenade_only_play_initializes_armour_and_does_not_scan_each_frame(self):
        self.wear("SA-25 Steel Trooper")
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertIn("throw range +30%", self.logs())
        scans = self.fake.calls["World.units"]
        self.frames(120)
        self.assertEqual(self.fake.calls["World.units"], scans)
        self.fake["down"]["g"] = False
        self.throw_nade(nade, 22)
        self.assertIn("bonus=1.200", self.logs(), "uses the existing measured perk factor; no retuning here")

    def test_failed_grenade_armour_lookup_is_rate_limited(self):
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(240)
        self.assertEqual(self.fake.calls["World.units"], 1)

    def test_comparison_trace_is_bounded_and_written_once_after_a_throw(self):
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(60)
        self.assertNotIn("grenade compare:", self.logs())
        self.fake["down"]["g"] = False
        self.throw_nade(nade, 22)
        rows = [l for l in self.logs().splitlines() if "grenade compare:" in l]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("preview_age=0.0000", row)
        self.assertIn("along=0.0000 bonus=1.000", row)
        self.assertGreater(len(row.split("samples=")[1].split(";")), 5)
        self.assertLessEqual(len(row.split("samples=")[1].split(";")), 16)
        self.frames(120)
        self.assertEqual(self.logs().count("grenade compare:"), 1)

    def test_native_profiles_cover_the_catalogue_and_preserve_distinct_curves(self):
        path = os.path.join(HERE, '..', 'src', 'grenade_profiles.lua')
        with open(path, encoding='utf-8') as f:
            profiles = self.lua.execute(f.read())
        native = [p for p in profiles.values() if p[2] is not None]
        self.assertEqual(len(native), 23)
        self.assertEqual(profiles['6b11fc757618c57e'][2], 20)
        self.assertEqual(profiles['46333fc9e3d4bd34'][2], 11)
        self.assertEqual(profiles['ee4c107b941ab7f4'][2], 4.5)
        self.assertEqual(profiles['a20683199dfc19e8'][2], 4)
        self.assertEqual(profiles['1b9ac59697006337'][2], 4)
        self.assertEqual(profiles['2968deba6d6c2f09'].measured, 10)
        watches = [w for w in self.fake.watches.values() if w.kinds['7686544f539bb9b7']]
        for kind in profiles.keys():
            self.assertTrue(watches[0].kinds[kind], kind)

    def test_unlearned_kinds_use_authored_curve_families_instead_of_one_generic_speed(self):
        # Existing standard measurement transfers the caller strength; native 4m curves predict ~10m/s, not 21.
        for kind, expected in (('3fa94f58f596bc0b', 22.4), ('1b9ac59697006337', 9.9928),
                               ('a20683199dfc19e8', 9.9928), ('2968deba6d6c2f09', 10)):
            with self.subTest(kind=kind):
                self.setUp()
                self.right_hand_at()
                self.hand_pose(41)
                self.fake.look(30)
                self.nade_in_hand(kind)
                self.fake['down']['g'] = True
                self.frames(3)
                line = self.lines()[1]            # centre strand: no width offset
                speed = (line[3] - line[0]) / .03 / math.cos(math.radians(35))
                self.assertAlmostEqual(speed, expected, delta=.02)

    def test_grenade_origin_follows_the_actual_low_hand_despite_legacy_standing_samples(self):
        self.load_calibration("""return {known = {['46333fc9e3d4bd34'] = {
          speed={16.8}, lift={5}, ahead={.2}, right={.3}, up={1.9},
          offset_ahead={.1}, offset_right={.2}, offset_up={.3} }}}""")
        self.right_hand_at()
        self.hand_pose(42)
        nade = self.nade_in_hand('46333fc9e3d4bd34')
        self.fake['down']['g'] = True
        self.frames(3)
        standing = self.lines()[1]
        nade.z = .05
        self.fake.me.nodes[7][3] = .05
        self.frames(1)
        prone = self.lines()[1]
        self.assertAlmostEqual(standing[2] - prone[2], 1.45, delta=.001)
        self.assertAlmostEqual(prone[1], -.5, delta=.001)

    def test_a_measured_release_is_saved_relative_to_the_held_object(self):
        self.right_hand_at()
        self.hand_pose(41)
        nade = self.nade_in_hand('7686544f539bb9b7')
        self.fake['down']['g'] = True
        self.frames(3)
        self.fake['down']['g'] = False
        self.throw_nade(nade, 22)
        row = self.fake.saved['grenade_throws6'].known['7686544f539bb9b7']
        self.assertAlmostEqual(row.offset_ahead[1], 0, delta=.001)
        self.assertAlmostEqual(row.offset_right[1], 0, delta=.001)
        self.assertIsNotNone(row.offset_up[1])

    def replay_recorded_flight(self, label, calibration=None):
        with open(os.path.join(HERE, 'fixtures', 'grenade_flights_test3.json'), encoding='utf-8') as f:
            row = next(r for r in json.load(f) if r['label'] == label)
        if calibration:
            self.load_calibration(calibration)
        self.right_hand_at()
        self.hand_pose(41 if label == 'impact' else 42)
        v = row['preview_velocity']
        length = math.sqrt(sum(x * x for x in v))
        self.fake.cam.fx, self.fake.cam.fy, self.fake.cam.fz = (x / length for x in v)
        nade = self.nade_in_hand(row['kind'])
        self.fake['down']['g'] = True
        self.frames(3)
        self.fake['down']['g'] = False
        previous = 0
        for t, x, y, z in row['points'][1:]:
            nade.x, nade.y, nade.z = x, y, z
            self.frames(1, t - previous)
            previous = t
        self.frames(80)
        return self.fake.saved['grenade_throws6'], row['kind']

    def test_recorded_giga_learns_the_later_flight_direction_instead_of_the_early_left_bias(self):
        saved, kind = self.replay_recorded_flight('giga')
        self.assertEqual(saved.known[kind].fit_revision, 2)
        self.assertGreater(saved.known[kind].yaw[1], 1,
                           'recorded flight heads right of the old displayed direction')
        self.assertLess(saved.known[kind].yaw[1], 4)

    def test_recorded_melta_fits_after_the_hand_swing_instead_of_rejecting_the_whole_throw(self):
        saved, kind = self.replay_recorded_flight('melta')
        self.assertEqual(saved.known[kind].fit_revision, 2)
        self.assertIsNotNone(saved.known[kind].offset_up[1])
        self.assertNotIn('thrown: not measured', self.logs())

    def test_recorded_impact_remains_measurable_with_the_longer_airborne_window(self):
        saved, kind = self.replay_recorded_flight('impact')
        self.assertAlmostEqual(saved.known[kind].yaw[1], 0, delta=.05)
        self.assertAlmostEqual(saved.known[kind].speed[2], 22.4, delta=.3)

    def test_reference_migration_preserves_old_angles_and_keeps_speeds(self):
        saved, kind = self.replay_recorded_flight('melta', """return {known = {
          ['ee4c107b941ab7f4'] = {speed={10.6}, lift={4.5}, yaw={-3},
           offset_ahead={.1},offset_right={.4},offset_up={-.3}}}}""")
        old = saved.fit_backups[kind]
        self.assertEqual(old.yaw[1], -3)
        self.assertEqual(old.offset_right[1], .4)
        self.assertEqual(old.lift[1], 4.5)
        self.assertEqual(saved.known[kind].speed[1], 10.6)
        self.assertIsNone(saved.known[kind].yaw[2], 'old bias must not dilute the new measurement')
        self.M = self.load()
        self.assertEqual(self.fake.saved['grenade_throws6'].fit_backups[kind].yaw[1], -3)
        saved_again, _ = self.replay_recorded_flight('melta')
        self.assertEqual(saved_again.fit_backups[kind].yaw[1], -3)
        self.assertIsNotNone(saved_again.known[kind].yaw[2], 'revision survives reload; second fit appends normally')

    def test_release_offsets_reference_the_displayed_hand_before_the_throw_animation(self):
        self.right_hand_at()
        self.hand_pose(41)
        nade = self.nade_in_hand('7686544f539bb9b7')
        self.fake['down']['g'] = True
        self.frames(3)
        self.fake['down']['g'] = False
        for _ in range(12):
            nade.x -= .02
            nade.y -= .01
            self.fake.me.nodes[7][1], self.fake.me.nodes[7][2] = nade.x, nade.y
            self.frames(1)
        vx, vz = 22 * math.cos(math.radians(5)), 22 * math.sin(math.radians(5))
        for i in range(1, 181):
            t = i / 60
            nade.x, nade.y, nade.z = .5 + vx * t, -.3, 1.9 + vz * t - 4.905 * t * t
            self.frames(1)
        row = self.fake.saved['grenade_throws6'].known['7686544f539bb9b7']
        self.assertAlmostEqual(row.offset_ahead[1], .2, delta=.001)
        self.assertAlmostEqual(row.offset_right[1], 0, delta=.001)
        self.assertAlmostEqual(row.offset_up[1], .4, delta=.001)

    def test_weapon_cache_is_revalidated_after_the_weapon_leaves_me(self):
        gun = self.weapon_in_hand(self.GL)
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        gun.x = 20
        self.frames(1)
        self.assertEqual(len(self.lines()), 1, "clear old arc instead of drawing from the distant gun")

    def test_a_slung_weapon_cannot_stay_selected_away_from_the_hand(self):
        gun = self.weapon_in_hand(self.GL)
        self.right_hand_at(gun.x, gun.y, gun.z)
        self.hand_pose(10)
        self.fake["mouse"]["right"] = True
        self.frames(3)
        gun.y += 1.2
        self.frames(1)
        self.assertEqual(len(self.lines()), 1)

    def test_switching_to_a_grenade_invalidates_the_weapon_even_with_aim_held(self):
        gun = self.weapon_in_hand(self.GL)
        self.right_hand_at(gun.x, gun.y, gun.z)
        self.hand_pose(10)
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.right_hand_at()
        self.fake.grip = 41
        self.nade_in_hand("7686544f539bb9b7")
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.assertIn("weapon aimed: none (throwable hand pose)", self.logs())
        self.assertIn("grenade hand: 7686544f539bb9b7", self.logs())
        self.assertAlmostEqual(self.lines()[0][1], -.3, delta=.02,
                               msg="current held grenade, not the gun's y=-.2 muzzle")

    def test_hand_node_lookup_and_pose_reads_are_bounded(self):
        self.right_hand_at()
        self.hand_pose(41)
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["mouse"]["right"] = True
        self.frames(3)
        lookups = self.fake.node_lookups
        reads = self.fake.calls["Unit.animation_get_variable"]
        self.frames(120)
        self.assertEqual(self.fake.node_lookups, lookups)
        self.assertEqual(self.fake.calls["Unit.animation_get_variable"] - reads, 120)

    def test_a_throw_pose_requests_an_async_watch_refresh_without_per_frame_scans(self):
        self.fake.watch_period = .5
        self.frames(1)                               # empty list already obtained
        self.right_hand_at()
        self.hand_pose(41)
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(1)
        self.assertEqual(self.lines(), [], "refresh does not invent a unit before the list arrives")
        self.frames(1)
        self.assertGreater(len(self.lines()), 20)
        watch = next(w for w in self.fake.watches.values() if w.kinds["7686544f539bb9b7"])
        self.frames(120)
        self.assertEqual(watch.refreshes, 1)

    def load_calibration(self, lua_data):
        self.fake.saved["grenade_throws6"] = self.lua.execute(lua_data)
        self.M = self.load()

    def test_reversed_impact_save_is_backed_up_and_recovers_only_its_kind(self):
        # The actual failure's values, independent of a player's AppData path.
        self.load_calibration("""return { known = {
          ['7686544f539bb9b7'] = { speed = {22.4, 11.282289459520273},
            lift = {4.2, 36.294324305242611}, yaw = {-168.02903044072511},
            ahead = {0.571565}, right = {0.529908}, up = {1.374827} },
          ['46333fc9e3d4bd34'] = {speed = {17.2}, lift = {5}, yaw = {-2},
            ahead = {.3}, right = {.2}, up = {1.8}} } }""")
        backup = self.fake.saved["grenade_throws6_before_validation1"].original
        repaired = self.fake.saved["grenade_throws6"].known
        self.assertAlmostEqual(backup.known["7686544f539bb9b7"].yaw[1], -168.02903044072511)
        self.assertAlmostEqual(repaired["7686544f539bb9b7"].speed[1], 22.4)
        self.assertIsNone(repaired["7686544f539bb9b7"].speed[2])
        self.assertAlmostEqual(repaired["46333fc9e3d4bd34"].speed[1], 17.2)
        self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertGreater(self.lines()[0][3], self.lines()[0][0], "recovered Impact flies forward")
        calls = self.fake.save_calls
        self.M = self.load()
        self.assertEqual(self.fake.save_calls, calls, "clean reloading does not rewrite either file")

    def test_valid_calibration_is_retained_without_a_write(self):
        self.load_calibration("""return { known = { ['7686544f539bb9b7'] = {
          speed = {22}, lift = {5}, yaw = {2}, ahead = {.5}, right = {.3}, up = {1.6} } } }""")
        self.assertIsNone(self.fake.save_calls)
        self.assertAlmostEqual(self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"].yaw[1], 2)

    def test_bad_saved_numbers_and_shapes_restore_defaults(self):
        for bad in ("0/0", "math.huge", "-math.huge", "'22'", "-1"):
            with self.subTest(bad=bad):
                self.load_calibration("return {known = {['7686544f539bb9b7'] = {speed = {%s}}}}" % bad)
                self.assertAlmostEqual(self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"].speed[1], 22.4)
        for data in ("{speed = {[2] = 22}}", "{speed = {22}, yaw = 'bad'}",
                     "{speed = {22}, ahead = {3}, right = {3}, up = {1}}",
                     "{speed = {22}, ahead = {.3}}", "{speed = {}}"):
            with self.subTest(data=data):
                self.load_calibration("return {known = {['7686544f539bb9b7'] = %s}}" % data)
                self.assertAlmostEqual(self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"].speed[1], 22.4)

    def test_calibration_recovery_does_not_replace_an_existing_backup(self):
        self.fake.saved["grenade_throws6_before_validation1"] = self.lua.execute("return {original = {marker = 'first'}}")
        self.load_calibration("return {known = {['7686544f539bb9b7'] = {speed = {0}}}}")
        self.assertEqual(self.fake.saved["grenade_throws6_before_validation1"].original.marker, "first")

    def test_calibration_backup_failure_leaves_original_file_untouched(self):
        self.fake.save_fail_name = "grenade_throws6_before_validation1"
        self.load_calibration("return {known = {['7686544f539bb9b7'] = {speed = {0}, yaw = {-168}}}}")
        self.assertEqual(self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"].yaw[1], -168)
        self.assertIn("original not overwritten", self.logs())
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertGreater(self.lines()[0][3], self.lines()[0][0])
        self.fake["down"]["g"] = False
        self.throw_nade(nade, 22)
        self.assertEqual(self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"].yaw[1], -168,
                         "later learning must not overwrite a file whose backup failed")

    def test_malformed_calibration_root_is_preserved_before_repair(self):
        self.load_calibration("return {known = 'damaged'}")
        self.assertEqual(self.fake.saved["grenade_throws6_before_validation1"].original.known, "damaged")
        self.assertAlmostEqual(self.fake.saved["grenade_throws6"].known["7686544f539bb9b7"].speed[1], 22.4)

    def test_an_unreadable_calibration_is_not_overwritten_by_later_learning(self):
        self.fake.saved["grenade_throws6"] = "unreadable original bytes"
        self.fake.load_fail_name = "grenade_throws6"
        self.M = self.load()
        self.assertIn("load failed (test: parse failed); original not overwritten", self.logs())
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.fake["down"]["g"] = False
        self.throw_nade(nade, 22)
        self.assertEqual(self.fake.saved["grenade_throws6"], "unreadable original bytes")
        self.assertIsNone(self.fake.save_calls)

    def test_a_backwards_flight_cannot_become_a_forward_aims_calibration(self):
        nade = self.nade_in_hand("7686544f539bb9b7")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.fake["down"]["g"] = False
        self.throw_nade(nade, -18)
        self.assertIsNone(self.fake.saved["grenade_throws6"])
        self.assertIn("not measured (invalid yaw", self.logs())

    def test_grenade_medians_are_cached_until_an_accepted_throw(self):
        self.lua.execute("""local sort = table.sort; sort_count = 0
          table.sort = function(t, ...) sort_count = sort_count + 1; return sort(t, ...) end""")
        nade = self.nade_in_hand("db922a7afc42894b")
        self.fake["down"]["g"] = True
        self.frames(3)
        count = self.lua.globals().sort_count
        self.assertGreater(count, 0)
        self.frames(120)
        self.assertEqual(self.lua.globals().sort_count, count, "no sorting at render frequency")
        self.fake["down"]["g"] = False
        self.throw_nade(nade, 18)
        after_learning = self.lua.globals().sort_count
        nade.dead = True
        self.nade_in_hand("db922a7afc42894b")
        self.fake["down"]["g"] = True
        self.frames(3)
        self.assertGreater(self.lua.globals().sort_count, after_learning, "accepted learning invalidates the cache")
        refreshed = self.lua.globals().sort_count
        self.frames(120)
        self.assertEqual(self.lua.globals().sort_count, refreshed)

    def test_the_arc_starts_where_the_ball_is_let_go_and_goes_on_below_my_feet(self):
        self.aim(10)
        lines = self.lines()
        self.assertEqual(len(lines) % 3, 0, "3 lines side by side per segment")
        first = lines[1][:3]                        # the middle one
        self.assertAlmostEqual(first[0], -0.05, delta=0.02)
        self.assertAlmostEqual(first[1], -0.3, delta=0.02)
        self.assertAlmostEqual(first[2], 1.9, delta=0.02, msg="let go 0.4 m above where it is held")
        # dashed: a drawn piece often doesn't start where the last one ended
        centre = lines[0::2]
        gaps = sum(1 for a, b in zip(centre, centre[1:]) if math.dist(a[3:], b[:3]) > 0.05)
        self.assertGreater(gaps, 5)
        # ends 15 m under my feet (the game hides what is under the ground)
        self.assertLess(min(l[5] for l in lines), -15)
        self.assertGreater(min(l[5] for l in lines), -17)

    def test_prone(self):
        # lying down, the ball in hand is about at my feet' height, with no pull-back: it rises into the aim
        self.aim(5, at=(0.6, -0.2, -0.15))
        self.assertEqual(self.lines(), [], "not yet: no pull-back lying down")
        self.lua.eval("function(b) b.z = 0.15 end")(self.ball)
        self.frames(2)
        lines = self.lines()
        self.assertGreater(len(lines), 20)
        self.assertAlmostEqual(lines[0][2], 0.55, delta=0.05)
        # a plain throw: the climb angle changes little from one piece to the next
        centre = lines[0::2]
        ang = [math.atan2(l[5] - l[2], math.hypot(l[3] - l[0], l[4] - l[1])) for l in centre[:15]]
        self.assertLess(max(abs(a - b) for a, b in zip(ang, ang[1:])), math.radians(6))

    def test_dashes_stay_put_when_the_camera_moves(self):
        # the arc hangs on the ball and the camera's heading only: the camera moving back leaves it where it is
        self.aim(10)
        before = self.lines()
        self.lua.eval("function(f) f.cam.x = f.cam.x - 1 end")(self.fake)
        self.frames(1)
        after = self.lines()
        ends = lambda ls: [round(l[3], 3) for l in ls[0::2]]
        self.assertEqual(ends(before)[16:26], ends(after)[16:26])
        self.assertEqual(len(before), len(after))

    def test_the_arc_stays_until_the_ball_leaves_the_hand(self):
        self.aim()
        self.fake["mouse"]["left"] = False          # let go: the swing, the ball still in hand
        self.frames(5)
        self.assertGreater(len(self.lines()), 20, "kept while the ball is in hand")
        self.lua.eval("function(b) b.x = b.x + 2 end")(self.ball)   # it flies
        self.frames(1)
        self.assertEqual([l[2] for l in self.lines()], [-10000], "one empty line resets the line object")
        self.frames(1)
        self.assertEqual(self.lines(), [])

    def test_the_hold_ends_by_itself(self):
        self.aim()
        self.fake["mouse"]["left"] = False          # let go, and nothing ever leaves the hand
        self.frames(30)
        self.assertGreater(len(self.lines()), 20)
        self.frames(10)                             # 0.6 s
        self.assertEqual(self.lines(), [])

    def test_right_mouse_aims_a_stratagem(self):
        ball = self.ready_ball()
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.fake["mouse"]["right"] = False         # aim let go, the ball still in hand: off, and on again
        self.frames(2)
        self.assertEqual(self.lines(), [])
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.fake["mouse"]["left"] = True           # thrown with left while right aims
        self.frames(2)
        self.fake["mouse"]["left"] = False
        self.frames(1)                              # let go, still in hand
        self.lua.eval("function(b) b.x = b.x + 2 end")(ball)   # then it flies
        self.frames(2)
        self.assertEqual(self.lines(), [])

    def test_no_key_needed(self):
        # whatever key calls stratagems: a ready ball in hand and left held is enough
        self.ready_ball()
        self.fake["mouse"]["left"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_put_away_then_a_shot(self):
        # the ball still in hand when left goes down (a stratagem put away), gone a moment later: the arc goes with it
        self.aim(10)
        self.assertGreater(len(self.lines()), 20)
        self.ball.dead = True
        self.frames(1)
        self.frames(1)
        self.assertEqual(self.lines(), [])
        self.frames(30)
        self.assertEqual(self.lines(), [], "and stays off while the shot goes on")

    def test_left_during_code_entry_draws_nothing(self):
        # the ball in hand, still in front (unlit: its code isn't in): left is no throw
        self.add_unit("16f397ca5f51f271", 0.3, -0.3, 1.2)
        self.frames(20)
        self.fake["mouse"]["left"] = True
        self.frames(20)
        self.assertEqual(self.lines(), [])

    def test_left_held_while_the_code_goes_in(self):
        # left down before the code is in: no pull-back, the ball goes up into the aim once it is lit
        ball = self.add_unit("16f397ca5f51f271", 0.3, -0.45, 1.25)
        self.frames(20)
        self.fake["mouse"]["left"] = True
        self.frames(30)
        self.assertEqual(self.lines(), [], "code still going in")
        self.lua.eval("function(b) b.x, b.z = -0.05, 1.47 end")(ball)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def c4_in_hand(self):
        """C4 is the weapon: its backpack on me, the detonator in my right hand, and C4's hand pose."""
        self.add_unit("2a18f81c44a26771", -0.15, 0.1, 1.3)
        self.hand_pose(42)
        return self.add_unit("51f50d6321f52f3d", -0.05, -0.4, 1.05)

    def test_c4_aimed_with_right(self):
        det = self.c4_in_hand()
        self.fake["mouse"]["right"] = True
        self.frames(5)
        self.assertEqual(self.lines(), [], "not yet: the detonator hasn't gone forward into the aim")
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        lines = self.lines()
        self.assertGreater(len(lines), 20)
        first = [(a + b) / 2 for a, b in zip(lines[0][:3], lines[1][:3])]
        self.assertAlmostEqual(first[0], 0.42, delta=0.02)
        self.assertAlmostEqual(first[1], -0.4, delta=0.02)
        # left throws it: the arc goes at once
        self.fake["mouse"]["left"] = True           # thrown: kept while it leaves the hand (0.15 s)
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.frames(8)
        self.assertEqual([l[2] for l in self.lines()], [-10000])
        self.frames(1)
        self.assertEqual(self.lines(), [])

    # ------------------------------------------------------------------ test.6 lab
    def test_the_one_two_draws_only_with_its_grenade_launcher(self):
        with open(os.path.join(HERE, "..", "src", "weapon_types.lua"), encoding="utf-8") as f:
            third = re.search(r"\[\[\s*(\S+)\s+(\S+)\s+(\S+)", f.read()).group(3)
        self.lua.eval("""function(f, name)
          f.E['Network.game_session'] = function() return {} end   -- (a new value each call, as in the game)
          f.E['Network.peer_id'] = function() return 'me' end
          f.E['GameSession.objects_owned_by'] = function() return { 5, 6 } end
          f.E['GameSession.game_object_exists'] = function() return true end
          f.E['GameSession.game_object_is_type'] = function(gs, g, t) return g == 6 and t == name end
          f.E['GameSession.game_object_field'] = function(gs, g, field)
            if g == 6 and field == 'if5_pz' then return f.fire_mode end
            error('NATIVE CRASH: an undeclared field')
          end
          f.fire_mode = 1
        end""")(self.fake, third)
        self.weapon_in_hand("a955c4ea6f6d4203")
        self.fake["mouse"]["right"] = True
        self.frames(5)
        self.assertEqual(self.lines(), [], "the rifle: no arc")
        self.fake.fire_mode = 9                       # the underbarrel selected (bit 8)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        logs = self.logs()
        self.assertIn("one-two: my object 6 is weapon type " + third, logs)
        self.assertIn("weapon aimed: AR/GL-21 One-Two (its grenade launcher)", logs)
        self.assertNotIn("NATIVE CRASH", logs)
        self.assertEqual(logs.count("one-two: my object 6 is weapon type"), 1, "found once, not every frame")

    def plug_pad(self):
        """a controller on Pad1: buttons a, left_trigger, right_trigger; fake.pad holds each button's value"""
        self.lua.eval("""function(f)
          f.pad = { 0, 0, 0 }
          f.E['Pad1.active'] = function() return true end
          f.E['Pad1.num_buttons'] = function() return 3 end
          f.E['Pad1.button_name'] = function(i) return ({ [0] = 'a', 'left_trigger', 'right_trigger' })[i] end
          f.E['Pad1.button'] = function(i) return f.pad[i + 1] end
        end""")(self.fake)

    def test_c4_aimed_and_thrown_with_a_controller(self):
        # 1.0.4: the left trigger aims, the right trigger throws (the game's default controller layout)
        self.plug_pad()
        det = self.c4_in_hand()
        self.fake["pad"][2] = 1                      # left trigger
        self.frames(5)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.assertIn("controller: Pad1, triggers found", self.logs())
        self.fake["pad"][3] = 1                      # right trigger: thrown, kept while it leaves the hand
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.frames(8)
        self.assertEqual([l[2] for l in self.lines()], [-10000])

    def test_a_pad_without_triggers_is_logged(self):
        self.lua.eval("""function(f)
          f.E['Pad1.connected'] = function() return true end
          f.E['Pad1.num_buttons'] = function() return 1 end
          f.E['Pad1.button_name'] = function(i) return 'a' end
        end""")(self.fake)
        self.frames(2)
        self.assertIn("controller: Pad1, no triggers among: a", self.logs())

    def test_the_arc_colour_is_an_option(self):
        self.aim(10)
        self.assertEqual(list(self.fake.line_color.values()), [0, 255, 0, 255])     # green by default
        self.fake.changes["arc_color"](4)                                        # red
        self.frames(1)
        self.assertEqual(list(self.fake.line_color.values()), [255, 70, 70, 255])

    def c4_object(self, options, owner_host=False):
        """C4's network object (NarrowHUD's names): mine, or the host's with me in its owner field."""
        self.lua.eval("""function(f, options, by_host)
          f.c4_options = options
          f.E['Network.game_session'] = function() return 'gs' end
          f.E['Network.peer_id'] = function() return '00ab12' end
          f.E['GameSession.game_session_host'] = function() return by_host and 'ff01' or '00ab12' end
          f.E['GameSession.objects_owned_by'] = function(gs, peer)
            if peer == '00ab12' then return by_host and { 3 } or { 3, 7 } end
            return { 9 }
          end
          f.E['GameSession.game_object_exists'] = function(gs, id) return true end
          f.E['GameSession.game_object_is_type'] = function(gs, id, t) return t == 'kbv6zx' and id == (by_host and 9 or 7) end
          f.E['GameSession.game_object_field'] = function(gs, id, name)
            if name == 'ozvglfc' then f.options_read = true; return f.c4_options end
            if name == 'g5g7b9d' then return 'AB12' end
            if name == 'n5jmvf' then return f.c4_carry or 0 end
          end
        end""")(self.fake, options, owner_host)

    def c4_aim_try(self):
        det = self.c4_in_hand()
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)

    def test_c4_detonate_mode_draws_nothing(self):
        self.c4_object(336)
        self.c4_aim_try()
        self.assertEqual(self.lines(), [])

    def test_c4_deploy_mode_draws(self):
        self.c4_object(80)
        self.c4_aim_try()
        self.assertGreater(len(self.lines()), 20)
        # switched to the detonator while aiming: the arc goes
        self.fake["c4_options"] = 336
        self.frames(2)
        self.assertEqual(self.lines(), [])

    def test_c4_owned_by_the_host(self):
        self.c4_object(336, owner_host=True)
        self.c4_aim_try()
        self.assertEqual(self.lines(), [])

    def hand_pose(self, grip):
        """my helldiver's animation variable weapon_selected (NarrowHUD's hand pose)"""
        self.lua.eval("""function(f, grip)
          f.grip = grip
          f.E['Unit.has_animation_state_machine'] = function(u) return u.kind == '4d1c334d294dfa97' end
          f.E['Unit.animation_has_variable'] = function(u, name) return name == 'weapon_selected' end
          f.E['Unit.animation_find_variable'] = function(u, name) return 3 end
          f.E['Unit.animation_get_variable'] = function(u, i) return i == 3 and f.grip or nil end
        end""")(self.fake, grip)

    def test_c4_pose_and_aim(self):
        # C4 in hand (42), right held and the detonator gone forward into the aim: the arc, from 1 m above it
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertEqual(self.lines(), [], "not yet in the aim pose (in a driver's seat it never is)")
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        lines = self.lines()
        self.assertGreater(len(lines), 20)
        self.assertAlmostEqual((lines[0][0] + lines[1][0]) / 2, 0.42, delta=0.02)   # from the detonator
        self.assertAlmostEqual((lines[0][2] + lines[1][2]) / 2, 2.05, delta=0.02)   # 1 m above it
        # thrown: it leaves the hand, then no arc for 0.8 s while the arm swings, then again
        self.fake["mouse"]["left"] = True
        self.frames(2)
        self.fake["mouse"]["left"] = False
        self.frames(20)
        self.assertEqual(self.lines(), [])
        self.frames(40)
        self.assertGreater(len(self.lines()), 20)

    def shapes(self):
        return list(self.fake.shapes.values())

    def test_c4_mode_icon_is_the_games(self):
        # the game's icon, shipped in the patch at 4 sizes: one bitmap, of the biggest (the loader picks the size)
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        self.frames(10)
        shapes = self.shapes()
        self.assertEqual(len(shapes), 1)
        deploy = self.lua.eval("function(f) local n = 0; for k, l in pairs(f.sizes) do n = n + 1 end; return n end")(self.fake)
        self.assertEqual(deploy, 2, "a size ladder for each icon")
        self.assertRegex(shapes[0], r"^bitmap [0-9a-f]{16}$")
        self.fake["c4_options"] = 336
        self.frames(10)
        self.assertNotEqual(self.shapes()[0], shapes[0], "DETONATE's own")

    def test_c4_mode_icon(self):
        # without the textures (chef.bitmap false): drawn with shapes
        self.fake["no_bitmap"] = True
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        self.frames(10)
        self.assertEqual(self.shapes().count("rect"), 14, "DEPLOY: the arrow's stem and 2 sticks of 3, and their shadow")
        self.fake["c4_options"] = 336
        self.frames(10)
        self.assertEqual(self.shapes().count("triangle"), 40, "DETONATE: a ring's 20 teeth, and its shadow")
        self.assertEqual(self.shapes().count("ring"), 2)
        self.hand_pose(10)                          # another weapon in hand: no icon
        self.frames(10)
        self.assertEqual(self.shapes(), [])
        self.hand_pose(42)
        self.fake.changes["c4_icon"](False)         # turned off in the menu
        self.frames(10)
        self.assertEqual(self.shapes(), [])

    def test_a_field_the_game_no_longer_declares_is_not_read(self):
        # a patch moved C4's options field: never read (reading it could end the game), no icon
        self.lua.eval("""function(f)
          f.E['Network.object_info'] = function(t)
            return { fields = { { id = '3ccffa7f' }, { id = '788b9753' } } }
          end
        end""")(self.fake)
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        self.frames(10)
        self.assertEqual(self.shapes(), [])
        self.assertIn("network: type kbv6zx no longer declares field ozvglfc (a game patch?): not read", self.logs())
        read = self.lua.eval("function(f) return f.options_read end")(self.fake)
        self.assertFalse(read, "the options field was read")

    def test_no_field_info_reads_nothing(self):
        self.lua.eval("function(f) f.E['Network.object_info'] = nil end")(self.fake)
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        self.frames(10)
        self.assertEqual(self.shapes(), [])
        self.assertIn("network: no field info for type kbv6zx: its fields are not read", self.logs())

    def test_c4_mode_icon_off_from_the_start(self):
        self.fake.opts["c4_icon"] = False
        self.M = self.load()
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        self.frames(10)
        self.assertEqual(self.shapes(), [])

    def test_no_c4_arc_without_the_hand_pose(self):
        # the hand pose unreadable: the detonator going forward into the aim alone is no C4 aim (1.0.3: the Censor)
        self.add_unit("2a18f81c44a26771", -0.15, 0.1, 1.3)
        det = self.add_unit("51f50d6321f52f3d", -0.05, -0.4, 1.05)
        self.c4_object(80)
        self.fake["mouse"]["right"] = True
        self.frames(5)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(5)
        self.assertEqual(self.lines(), [])

    def test_hand_pose_found_later(self):
        self.fake["no_bitmap"] = True
        # the variable not there yet at first: looked for again 5 s later
        self.add_unit("2a18f81c44a26771", -0.15, 0.1, 1.3)
        self.add_unit("51f50d6321f52f3d", -0.05, -0.4, 1.05)
        self.c4_object(80)
        self.frames(30)
        self.assertEqual(self.shapes(), [])
        self.hand_pose(42)
        self.frames(330)
        self.assertGreater(len(self.shapes()), 0)

    def test_c4_put_away_while_aiming(self):
        # the hand pose stays C4 a moment while it is put away; the detonator leaving the aim pose ends the arc
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.lua.eval("function(u) u.x, u.z = -0.1, 0.9 end")(det)
        self.frames(30)                             # (kept 0.25 s, for dives)
        self.assertEqual(self.lines(), [])

    def test_c4_aim_kept_while_turning(self):
        # the camera turns ahead of my helldiver: the detonator, still as far from my feet, keeps the arc
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.lua.eval("function(f) local p = math.rad(10); f.cam.fx, f.cam.fy = 0, 1 end")(self.fake)   # 90 degrees
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_prone(self):
        # lying down the detonator lies low and right doesn't move it: C4 in hand and right is the aim
        self.add_unit("51f50d6321f52f3d", 0.67, -0.18, 0.06)
        self.hand_pose(42)
        self.frames(2)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_passenger_leaning_out(self):
        # seated, leaning out to aim up: the camera far off and the detonator 1.4 m from my feet
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.frames(2)                              # found on foot first
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x, u.y = 0.9, -1.07 end")(det)
        self.lua.eval("function(f) f.cam.x = -9 end")(self.fake)
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)

    def test_thicker_below_native_render_scale(self):
        self.lua.eval("function(f) f.settings['render_settings.render_resolution'] = { 1129, 600 } end")(self.fake)
        self.aim(10)
        lines = self.lines()
        self.assertGreater(len(lines), 30)
        self.assertEqual(len(lines) % 3, 0, "3 lines a segment, not 2")
        # 2 render pixels across between the outer two (render scale 0.5 of 1200: 2 px each)
        a, b = lines[30], lines[32]
        mid = [(a[i] + a[i + 3]) / 2 for i in range(3)]
        width_px = math.dist(a[:3], b[:3]) / (math.dist(mid, (0, 0, 2)) * 0.96 / 1200)
        self.assertAlmostEqual(width_px, 4, delta=0.2)

    def test_c4_prone_looking_behind(self):
        # lying down, looking behind: the detonator 0.4 m up and close to my feet, still the aim
        self.add_unit("51f50d6321f52f3d", -0.12, -0.18, 0.40)
        self.hand_pose(42)
        self.frames(2)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_diving(self):
        # diving: the hand pose reads 40 a moment after C4's 42, the detonator low on my left
        det = self.add_unit("51f50d6321f52f3d", 0.0, -0.4, 1.05)
        self.hand_pose(42)
        self.frames(10)
        self.lua.eval("function(u) u.x, u.y, u.z = 0.1, 0.22, 0.14 end")(det)
        self.fake["grip"] = 40
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.fake["mouse"]["right"] = False
        self.frames(200)                            # a grenade in hand long after: not C4
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertEqual(self.lines(), [])

    def test_c4_knee_slide(self):
        # sliding on my knees: the detonator at crouch height and not moving out, still the aim
        self.add_unit("51f50d6321f52f3d", 0.15, -0.3, 0.57)
        self.hand_pose(42)
        self.frames(2)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_passenger_aiming_behind(self):
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.vehicle_at(0.4, 0.3, -0.6)             # seated
        self.frames(2)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)   # leaning out
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.lua.eval("function(u) u.x, u.y = -0.1, -0.1 end")(det)   # aiming behind: close in
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_tank_seat(self):
        # on a tank's top, 3.1 m off its middle and 2.4 m up: in a vehicle, the aim kept as the detonator comes in
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.add_unit("16474112801385b6", 3.1, 0, -2.4)
        self.frames(2)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.lua.eval("function(u) u.x, u.y = 0.3, -0.3 end")(det)   # back to 0.42 m off: still kept
        self.frames(30)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_tank_seat_raised(self):
        # on a tank's top the detonator sits 0.45 m off already and only rises to aim: from 0.59 to 1.1 m up
        det = self.add_unit("51f50d6321f52f3d", 0.37, -0.24, 0.59)
        self.hand_pose(42)
        self.add_unit("16474112801385b6", 3.1, 0, -2.2)
        self.frames(2)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.assertEqual(self.lines(), [])
        self.lua.eval("function(u) u.z = 1.1 end")(det)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)

    def test_c4_driver_seat(self):
        # seated, right held, the detonator never leans out (and sits low, 0.46 m up): no arc
        self.add_unit("51f50d6321f52f3d", 0.06, -0.25, 0.46)
        self.hand_pose(42)
        self.vehicle_at(0.4, 0.3, -0.6)
        self.fake["mouse"]["right"] = True
        self.frames(30)
        self.assertEqual(self.lines(), [])

    def test_swapped_detonator(self):
        # the C4 dropped (not carried any more) is let go and the one carried is read
        self.fake["no_bitmap"] = True
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        self.frames(10)
        self.assertEqual(self.shapes().count("rect"), 14)
        self.lua.eval("""function(f)
          f.E['GameSession.objects_owned_by'] = function() return { 3, 7, 8 } end
          f.E['GameSession.game_object_is_type'] = function(gs, id, t) return t == 'kbv6zx' and (id == 7 or id == 8) end
          f.E['GameSession.game_object_field'] = function(gs, id, name)
            if name == 'n5jmvf' then return id == 8 and 0 or 2 end
            if name == 'ozvglfc' then return id == 8 and 336 or 80 end
          end
        end""")(self.fake)
        self.frames(150)
        self.assertEqual(self.shapes().count("ring"), 2, "the new detonator's mode")

    def vehicle_at(self, x, y, z):
        return self.add_unit("cc21c7ffd3ebefb9", x, y, z)

    def test_icon_in_a_vehicle_while_aiming(self):
        # seated, the icon only while C4 is aimed (a passenger leaning out), DETONATE too (no arc there)
        det = self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(336)
        self.vehicle_at(0.4, 0.3, -0.6)
        self.frames(40)
        self.assertEqual(self.shapes(), [])
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)   # leaning out
        self.frames(10)
        self.assertEqual(len(self.shapes()), 1, "the icon")
        self.assertEqual(self.lines(), [], "DETONATE: no arc")
        self.fake["mouse"]["right"] = False
        self.frames(10)
        self.assertEqual(self.shapes(), [])

    def test_no_icon_in_a_vehicle(self):
        self.c4_in_hand()
        self.hand_pose(42)
        self.c4_object(80)
        car = self.vehicle_at(2.2, 0, -0.6)        # seated: 2.2 m from its middle, 0.6 m above its base
        self.frames(40)
        self.assertEqual(self.shapes(), [])
        self.lua.eval("function(u) u.z = 0 end")(car)   # standing by it on the ground
        self.frames(40)
        self.assertGreater(len(self.shapes()), 0)

    def test_c4_pose_other_weapon_draws_nothing(self):
        # another weapon in hand (pose 10): the detonator going forward is no aim
        det = self.c4_in_hand()
        self.hand_pose(10)
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.assertEqual(self.lines(), [])

    def test_c4_raised_arm_is_no_aim(self):
        # the throw lifts the detonator about 2.1 m up: no arc from there
        det = self.c4_in_hand()
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x, u.z = 0.3, 2.1 end")(det)
        self.frames(10)
        self.assertEqual(self.lines(), [])

    def test_c4_arc_ends_when_right_is_let_go(self):
        det = self.c4_in_hand()
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.assertGreater(len(self.lines()), 20)
        self.fake["mouse"]["right"] = False
        self.frames(2)
        self.assertEqual(self.lines(), [])

    def test_right_without_c4_in_hand_draws_nothing(self):
        # another weapon aimed: the detonator rides on my back, not in my right hand, even if it moves forward
        self.add_unit("2a18f81c44a26771", -0.15, 0.1, 1.3)
        det = self.add_unit("51f50d6321f52f3d", -0.2, 0.1, 1.2)
        self.fake["mouse"]["right"] = True
        self.frames(5)
        self.lua.eval("function(u) u.x = 0.2 end")(det)
        self.frames(5)
        self.assertEqual(self.lines(), [])

    def test_walking_forward_throws_farther(self):
        # the throw is faster by my speed along the aim (1.4 times it, up to 3 m/s; camera along +x), none across
        def reach():
            ls = self.lines()
            xs = [v for l in ls for v in (l[0], l[3])]
            ys = [v for l in ls for v in (l[1], l[4])]
            return max(xs) - ls[0][0], max(abs(y - ls[0][1]) for y in ys)
        self.aim(10)
        still, _ = reach()
        for _ in range(10):
            self.lua.eval("function(f) f.me.x = f.me.x + 3 / 60 end")(self.fake)
            self.frames(1)
        ahead, _ = reach()
        self.assertGreater(ahead - still, 1.5)
        for _ in range(10):
            self.lua.eval("function(f) f.me.y = f.me.y + 3 / 60 end")(self.fake)
            self.frames(1)
        across, wide = reach()
        self.assertAlmostEqual(across, still, delta=0.3)
        self.assertLess(wide, 0.3)

    def test_shooting_draws_nothing(self):
        self.fake["mouse"]["left"] = True                # no ball in hand: a shot
        self.frames(90)
        self.assertEqual(self.lines(), [])
        self.add_unit("16f397ca5f51f271", 0.4, -0.3, 1.5)
        self.frames(30)
        self.assertEqual(self.lines(), [], "still the same shot: looked for a second only")

    def test_after_a_throw_left_is_a_shot(self):
        f = self.fake
        self.aim(10)
        self.assertIn("armour: none of the table [on me], throw range +0%", self.logs())
        f["mouse"]["left"] = False
        f.throw("16f397ca5f51f271", 22, 19, 9.81, self.ball)
        self.frames(200)
        f["mouse"]["left"] = True
        self.frames(2)
        self.assertEqual(self.lines(), [], "thrown: the ball lies far away, a shot again")
        self.assertNotIn("NATIVE CRASH", self.logs())

    def wear(self, name):
        with open(ta_build.ARMOUR, encoding="utf-8") as f:
            rows = self.lua.execute(f.read())
        kinds = [row[3].split() for row in rows.values() if row[1] == name][0]
        return self.lua.table(*[self.add_unit(k, 0.1 * (i % 3), 0.1, 1.0) for i, k in enumerate(kinds)])   # on me

    def far_end(self):
        return max(l[3] for l in self.lines())

    def test_desert_stormer_throws_20_percent_farther(self):
        self.aim(15)
        plain = self.far_end()
        self.fake["mouse"]["left"] = False
        self.frames(2)
        self.wear("DS-10 Big Game Hunter")
        self.aim(15)
        self.assertIn("armour: DS-10 Big Game Hunter [on me] (100% of its units), throw range +20%", self.logs())
        # flat ground far below: the far end moves out by about the speed ratio (range grows with its square)
        self.assertGreater(self.far_end() / plain, 1.08)

    def drawn_speed(self, pitch):
        """the throw speed the arc was drawn with: the first segment's run along the view (it looks along x), per step
        (the first: past the top, segments are half a step)"""
        l = self.lines()[0]
        return (l[3] - l[0]) / 0.03 / math.cos(math.radians(pitch))

    def test_the_falling_part_is_dashed_finer(self):
        self.aim(30)
        lines = self.lines()
        top = max(lines, key=lambda l: l[2])
        rising = [l[3] - l[0] for l in lines if l[5] > l[2]]
        falling = [l[3] - l[0] for l in lines if l[5] < l[2] and l[0] > top[0] + 2]
        self.assertAlmostEqual(falling[0] / rising[0], 0.5, delta=0.05)

    def test_servo_assisted_speeds(self):
        # as measured in test.26: stratagem balls 1.2x (26.4 m/s), C4 1.3x (29.1 m/s)
        self.hand_pose(41)
        self.wear("SA-25 Steel Trooper")
        self.aim(15)
        self.assertIn("throw range +30%", self.logs())
        self.assertAlmostEqual(self.drawn_speed(15 + 7.8), 26.4, delta=0.1)
        self.fake["mouse"]["left"] = False
        self.ball.dead = True                       # thrown
        self.frames(2)
        det = self.c4_in_hand()
        self.fake["grip"] = 42
        self.fake["mouse"]["right"] = True
        self.frames(2)
        self.lua.eval("function(u) u.x = 0.42 end")(det)
        self.frames(2)
        self.assertAlmostEqual(self.drawn_speed(15 + 4.4), 29.1, delta=0.1)

    def test_armour_told_once(self):
        # the pass over all the world's units: at the first aim only, not at every throw
        self.wear("DS-10 Big Game Hunter")
        self.aim(15)
        first = self.fake.calls["World.units"]
        for _ in range(3):
            self.fake["mouse"]["left"] = False
            self.frames(2)
            self.aim(15)
        self.assertEqual(self.fake.calls["World.units"], first)
        self.assertIn("throw range +20%", self.logs())

    def test_a_lookalike_without_the_perk(self):
        # FS-23 Battle Master shares 20 of TR-62 Knight's 23 units, but throws no farther
        self.wear("FS-23 Battle Master")
        self.aim(15)
        self.assertIn("armour: FS-23 Battle Master [on me] (100% of its units), throw range +0%", self.logs())

    def test_transmog_tells_my_own_armour(self):
        # HD2 Transmog: the look's copies (DS-10) are on me as well as my own armour (SR-24, hidden); its worn('armor')
        # lists my own
        self.wear("DS-10 Big Game Hunter")
        mine = self.wear("SR-24 Street Scout")
        self.lua.eval("function(units) TransmogUI = { worn = function(g) return units end } end")(mine)
        self.aim(15)
        self.assertIn("armour: SR-24 Street Scout [Transmog] (100% of its units), throw range +0%", self.logs())
        self.lua.execute("TransmogUI = nil")

    def test_two_whole_armours_without_transmog(self):
        self.wear("DS-10 Big Game Hunter")
        self.wear("SR-24 Street Scout")
        self.aim(15)
        self.assertRegex(self.logs(), r"armour: .* and .* \(a look mod\? no bonus\) \[on me\].*throw range \+0%")

    def test_looking_down_keeps_the_ball_in_hand(self):
        self.lua.eval("function(f) local look = f.look; f.look = function(p) look(p); f.cam.z = 2 - p / 15 end end")(
            self.fake)
        self.aim(-60)
        self.assertGreater(len(self.lines()), 20)

    # ------------------------------------------------------------------ weapons (1.1.0)
    GL = "02eecd0b1fa49630"

    def weapon_in_hand(self, kind, back=1.5, f=(1, 0, 0)):
        """my helldiver BACK m ahead of the camera (third person), a weapon unit by its right hand pointing F"""
        self.lua.eval("function(f, x) f.me.x = x end")(self.fake, back)
        u = self.add_unit(kind, back + 0.3, -0.2, 1.2)
        self.lua.eval("function(u, x, y, z) u.f = { x, y, z } end")(u, *f)
        return u

    @staticmethod
    def flight(speed, gravity, drag_term, pitch_deg, start):
        """the drawn round's flight in Python, where it comes down to z = 0: x"""
        x, z = start
        p = math.radians(pitch_deg + 0.6)
        vx, vz = speed * math.cos(p), speed * math.sin(p)
        h = 1 / 120
        while z > 0:
            d = 4.7e-4 * drag_term * math.hypot(vx, vz) * h
            vx, vz = vx - d * vx, vz - 9.81 * gravity * h - d * vz
            x, z = x + vx * h, z + vz * h
        return x

    def test_a_grenade_launcher_aimed_draws_its_round(self):
        p, wp = math.radians(10), math.radians(11.5)     # held, a weapon points 1.5 degrees above its round
        self.weapon_in_hand(self.GL, f=(math.cos(wp), 0, math.sin(wp)))
        self.fake.look(10)
        self.fake["mouse"]["right"] = True
        self.frames(3)
        lines = self.lines()
        self.assertGreater(len(lines), 20)
        self.assertIn("weapon aimed: GL-21 Grenade Launcher", self.logs())
        first = min(lines, key=lambda l: l[0])
        # from the muzzle: 0.45 m ahead of the weapon unit (1.8, -0.2, 1.2)
        muzzle = (1.8 + 0.45 * math.cos(wp), -0.2, 1.2 + 0.45 * math.sin(wp))
        for got, want in zip(first[:3], muzzle):
            self.assertAlmostEqual(got, want, delta=0.05)
        # dashed as the stratagem arc: points 0.66 m apart near me
        near = sorted({round(l[0], 2) for l in lines if l[0] < 20})
        self.assertAlmostEqual(math.hypot(near[1] - near[0], (near[1] - near[0]) * math.tan(p)), 0.66, delta=0.05)
        # comes down where the drag law says (the round at 10 degrees), well short of a drag-free flight
        down = [l for l in lines if l[2] >= 0 >= l[5]][0]
        want = self.flight(100, 1, 38.4, 10, (muzzle[0], muzzle[2]))
        self.assertAlmostEqual(down[0], want, delta=3)
        self.assertLess(want, 0.6 * self.flight(100, 1, 0, 10, (muzzle[0], muzzle[2])))

    def arc_end(self):
        return max(self.lines(), key=lambda l: l[3])

    def test_walking_sideways_bends_the_weapon_arc_halfway(self):
        self.weapon_in_hand(self.GL)
        self.fake["mouse"]["right"] = True
        self.frames(10)
        still = self.arc_end()
        walk = self.lua.eval("function(f) f.walk = function() f.me.y = f.me.y + 2.2 / 60 end end")
        walk(self.fake)
        for _ in range(20):
            self.fake.walk()
            self.frames(1)
        moved = self.arc_end()
        # the camera stayed: the arc moves by half my sideways speed over its flight (the far end: 4.2 s at 2.2 m/s)
        self.assertGreater(moved[4] - still[4], 0.5)
        self.assertLess(moved[4] - still[4], 2.2 * 4.2 * 0.5 + 0.5)

    def test_the_weapon_arc_follows_a_lagging_weapon(self):
        # held still, the GL points 1 degree above the camera: learned, and taken off
        up = math.radians(1)
        gl = self.weapon_in_hand(self.GL, f=(math.cos(up), 0, math.sin(up)))
        self.fake["mouse"]["right"] = True
        self.frames(30)
        still = self.arc_end()
        self.assertAlmostEqual(still[4], -0.2, delta=0.3)      # from the muzzle, 0.2 m right of me
        # the camera swings left fast (+y), the weapon still points where it did: the arc stays with the weapon
        turn = self.lua.eval("""function(f) f.turn = function(deg)
          local a = math.rad(deg); f.cam.fx, f.cam.fy = math.cos(a), math.sin(a) end end""")
        turn(self.fake)
        for i in range(1, 6):
            self.fake.turn(i * 2)           # 120 degrees/s
            self.frames(1)
        self.assertGreater(len(self.lines()), 20, "kept while the weapon lags (10 degrees off)")
        lagged = self.arc_end()
        self.assertLess(abs(lagged[4] - still[4]), 1.0)

    def test_no_weapon_arc_in_first_person(self):
        gl = self.weapon_in_hand(self.GL, back=0.1)
        self.lua.eval("function(u) u.z = 1.8 end")(gl)     # in first person, 0.5 m from the camera
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])
        self.assertIn("weapon aimed: GL-21 Grenade Launcher (first person: not drawn)", self.logs())

    def test_weapon_arc_lying_prone_is_not_suppressed_by_height(self):
        gl = self.weapon_in_hand(self.GL)
        self.lua.eval("function(u) u.z = 0.4 end")(gl)     # prone: the weapon low by my feet
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.assertNotIn("weapon aimed lying prone: not drawn", self.logs())

    def test_prone_weapon_diagnostic_is_not_repeated_each_frame(self):
        gun = self.weapon_in_hand(self.GL)
        gun.z = .4
        self.fake['mouse']['right'] = True
        self.frames(120)
        self.assertEqual(self.logs().count('weapon aimed: GL-21 Grenade Launcher'), 1)
        self.assertEqual(self.logs().count('weapon muzzle:'), 1)

    def weapon_nodes(self, gun, muzzle, sight=None, name='attach_muzzle'):
        positions = {11: self.lua.table_from(muzzle)}
        names = {name: 11}
        if sight:
            positions[12] = self.lua.table_from(sight)
            names['sight'] = 12
        gun.nodes, gun.named_nodes = self.lua.table_from(positions), self.lua.table_from(names)

    def direction_flights(self):
        with open(os.path.join(HERE, 'fixtures', 'weapon_direction_test6.json'), encoding='utf-8') as f:
            return json.load(f)['shots']

    def apply_direction_flight(self, gun, row):
        v = row['vectors']
        c = v['camera-position']
        for key, value in zip(('x', 'y', 'z'), c):
            self.fake.cam[key] = value
        for key, value in zip(('fx', 'fy', 'fz'), v['camera-forward']):
            self.fake.cam[key] = value
        for key, value in zip(('x', 'y', 'z'), v['root-position']):
            gun[key] = value
        gun.f = self.lua.table_from(v['root-forward'])
        self.fake.me.x, self.fake.me.y = gun.x, gun.y
        height = float(row['header'].split('root-height=')[1])
        self.fake.me.z = gun.z - height
        self.weapon_nodes(gun, v['muzzle-position'])

    def drawn_yaw(self):
        line = self.lines()[0]
        return math.degrees(math.atan2(line[4] - line[1], line[3] - line[0]))

    @staticmethod
    def yaw_error(a, b):
        return (a - b + 180) % 360 - 180

    def test_recorded_standing_crouched_prone_rounds_use_fixed_profiles_immediately(self):
        gun = self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        flights = self.direction_flights()
        # Actual sequence including returning to standing. Fixed geometry bands have no learned history.
        for n in ('3', '4', '5', '6', '7', '8', '9'):
            with self.subTest(shot=n):
                self.setUp()
                gun = self.weapon_in_hand(self.GL)
                self.fake['mouse']['right'] = True
                row = flights[n]
                self.apply_direction_flight(gun, row)
                self.frames(1)
                a, b = row['samples'][0], row['samples'][-1]
                actual = math.degrees(math.atan2(b[3] - a[3], b[2] - a[2]))
                self.assertLess(abs(self.yaw_error(self.drawn_yaw(), actual)), .4)
                self.assertLess(math.dist(a[2:], row['vectors']['muzzle-position']), .02)

    def test_fixed_profile_preserves_corner_deflection(self):
        row = self.direction_flights()['8']
        gun = self.weapon_in_hand(self.GL)
        self.apply_direction_flight(gun, row)
        self.fake['mouse']['right'] = True
        self.frames(1)
        before = self.drawn_yaw()
        root = row['vectors']['root-forward']
        a = math.radians(-5.3)
        gun.f = self.lua.table_from((root[0] * math.cos(a) - root[1] * math.sin(a),
                                    root[0] * math.sin(a) + root[1] * math.cos(a), root[2]))
        m = row['vectors']['muzzle-position']
        dx, dy = m[0] - gun.x, m[1] - gun.y
        gun.nodes[11] = self.lua.table_from((gun.x + dx * math.cos(a) - dy * math.sin(a),
                                           gun.y + dx * math.sin(a) + dy * math.cos(a), m[2]))
        self.frames(1)
        first = self.drawn_yaw()
        self.frames(180)
        self.assertAlmostEqual(self.yaw_error(first, before), -5.3, delta=.08)
        self.assertAlmostEqual(self.drawn_yaw(), first, delta=.001)

    def test_unmeasured_weapon_has_fixed_fallback_without_camera_learning(self):
        row = self.direction_flights()['1']
        gun = self.weapon_in_hand('9eb160830321bfd6')
        self.apply_direction_flight(gun, row)
        self.fake['mouse']['right'] = True
        self.frames(1)
        first = self.lines()
        self.frames(120)
        self.assertEqual(self.lines(), first)

    def test_fixed_prone_yaw_has_no_settling_at_different_frame_rates(self):
        row = self.direction_flights()['8']
        results = []
        for hz in (30, 60, 120):
            self.setUp()
            gun = self.weapon_in_hand(self.GL)
            self.apply_direction_flight(gun, row)
            self.fake['mouse']['right'] = True
            self.frames(1, dt=1 / hz)
            first = self.drawn_yaw()
            self.frames(round(2 * hz), dt=1 / hz)
            self.assertAlmostEqual(self.drawn_yaw(), first, delta=.001)
            results.append(first)
        self.assertLess(max(results) - min(results), .001)

    def test_getting_out_of_vehicle_restores_the_same_profile_immediately(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(2)
        before = self.lines()
        car = self.vehicle_at(1.9, .3, -.6)
        self.frames(120)
        car.dead = True
        self.frames(1)
        self.assertEqual(self.lines(), before)
        self.frames(120)
        self.assertEqual(self.lines(), before)

    def apply_vehicle_snapshot(self, gun, n):
        with open(os.path.join(HERE, 'fixtures', 'weapon_direction_test8.json'), encoding='utf-8') as f:
            lines = json.load(f)['vehicle_snapshots'][str(n)]
        points = {}
        for line in lines:
            name, _, rest = line.partition(' ')
            if name in ('camera-position', 'camera-forward', 'feet', 'right-hand', 'weapon-root', 'weapon-forward', 'muzzle'):
                points[name] = tuple(map(float, rest.split()))
        for obj, name in ((self.fake.cam, 'camera-position'), (self.fake.me, 'feet'), (gun, 'weapon-root')):
            for key, v in zip(('x', 'y', 'z'), points[name]):
                obj[key] = v
        for key, v in zip(('fx', 'fy', 'fz'), points['camera-forward']):
            self.fake.cam[key] = v
        gun.f = self.lua.table_from(points['weapon-forward'])
        self.fake.me.nodes = self.lua.table_from({7: self.lua.table_from(points['right-hand'])})
        self.weapon_nodes(gun, points['muzzle'])

    def test_recorded_frv_driver_is_hidden_and_passenger_is_preserved(self):
        for n in (2, 4, 6, 9, 10, 11, 12, 13):
            with self.subTest(snapshot=n):
                self.setUp()
                gun = self.weapon_in_hand('fe3b29b2cfa63f9b')
                self.fake.me.named_nodes = self.lua.table_from({'attach_hand_r': 7})
                self.frames(1)  # retain the already identified player when the vehicle camera moves beyond 6m
                self.apply_vehicle_snapshot(gun, n)
                self.vehicle_at(self.fake.me.x + .4, self.fake.me.y + .3, self.fake.me.z - .6)
                self.fake['mouse']['right'] = True
                self.frames(1)
                if n < 9:
                    self.assertGreater(len(self.lines()), 20)
                else:
                    self.assertEqual(self.lines(), [])
                    self.assertIn('FRV weapon not raised for aiming', self.logs())

    def test_supply_frv_driver_and_passenger_use_the_same_eligibility_gate(self):
        for n, expected in ((9, False), (2, True)):
            with self.subTest(snapshot=n):
                self.setUp()
                gun = self.weapon_in_hand('fe3b29b2cfa63f9b')
                self.fake.me.named_nodes = self.lua.table_from({'attach_hand_r': 7})
                self.frames(1)
                self.apply_vehicle_snapshot(gun, n)
                car = self.vehicle_at(self.fake.me.x + .4, self.fake.me.y + .3, self.fake.me.z - .6)
                car.kind = '9b2140378640432e'
                self.fake['mouse']['right'] = True
                self.frames(1)
                self.assertEqual(bool(self.lines()), expected)
                self.assertIn('vehicle-kind=9b2140378640432e', self.logs())
                if not expected:
                    self.assertIn('FRV weapon not raised for aiming', self.logs())

    def test_gr8_prone_estimate_is_fixed_and_does_not_change_other_height_groups(self):
        with open(os.path.join(HERE, 'fixtures', 'weapon_direction_test9.json'), encoding='utf-8') as f:
            row = json.load(f)['shots']['1']
        gun = self.weapon_in_hand('9f80d67a12a7e40f')
        self.apply_direction_flight(gun, row)
        self.weapon_nodes(gun, row['vectors']['muzzle-position'], name='muzzle')
        self.fake['mouse']['right'] = True
        self.frames(1)
        camera = row['vectors']['camera-forward']
        camera_yaw = math.degrees(math.atan2(camera[1], camera[0]))
        # This checks the explicitly estimated camera reference, not measured projectile accuracy.
        self.assertAlmostEqual(self.yaw_error(self.drawn_yaw(), camera_yaw), 0, delta=.35)
        first = self.lines()
        self.frames(120)
        self.assertEqual(self.lines(), first)
        for height in (.9, 1.5):
            gun.z = self.fake.me.z + height
            self.frames(1)
            self.assertAlmostEqual(self.yaw_error(self.drawn_yaw(), camera_yaw), -1.3556, delta=.08)

    def apply_prone_body_flight(self, gun, row):
        self.apply_direction_flight(gun, row)
        v = row['vectors']
        self.fake.me.named_nodes = self.lua.table_from({'hips': 61, 'chest': 62})
        self.fake.me.nodes = self.lua.table_from({
            61: self.lua.table_from(v['avatar-hips-position']),
            62: self.lua.table_from(v['avatar-chest-position'])})
        name = 'muzzle' if 'kind=9f80d67a12a7e40f' in row['header'] else 'attach_muzzle'
        self.weapon_nodes(gun, v['muzzle-position'], name=name)

    def test_recorded_twisted_prone_gl_rounds_improve_without_learning(self):
        with open(os.path.join(HERE, 'fixtures', 'weapon_direction_test11.json'), encoding='utf-8') as f:
            rows = json.load(f)['shots']
        for n in ('3', '4', '5'):
            with self.subTest(shot=n):
                self.setUp()
                gun = self.weapon_in_hand(self.GL)
                row = rows[n]
                self.apply_prone_body_flight(gun, row)
                self.fake['mouse']['right'] = True
                self.frames(1)
                a, b = row['samples'][0], row['samples'][-1]
                actual = math.degrees(math.atan2(b[3] - a[3], b[2] - a[2]))
                before_v = row['vectors']['predicted-velocity']
                before = math.degrees(math.atan2(before_v[1], before_v[0]))
                error = abs(self.yaw_error(self.drawn_yaw(), actual))
                self.assertLess(error, abs(self.yaw_error(before, actual)))
                self.assertLess(error, .7 if n != '5' else .15)
                first = self.lines()
                self.frames(120)
                self.assertEqual(self.lines(), first)

    def test_gr8_frame_preserves_confirmed_flat_reference(self):
        with open(os.path.join(HERE, 'fixtures', 'weapon_direction_test11.json'), encoding='utf-8') as f:
            row = json.load(f)['shots']['1']
        gun = self.weapon_in_hand('9f80d67a12a7e40f')
        self.apply_prone_body_flight(gun, row)
        self.fake['mouse']['right'] = True
        self.frames(1)
        old = row['vectors']['predicted-velocity']
        self.assertAlmostEqual(self.drawn_yaw(), math.degrees(math.atan2(old[1], old[0])), delta=.06)

    def test_local_prone_correction_rotates_with_weapon_roll(self):
        gun = self.weapon_in_hand(self.GL)
        gun.z = .3
        # Actual rigid GL bind locator, rolled 90 degrees about +X. Root height remains prone.
        self.weapon_nodes(gun, (gun.x + .437935799, gun.y - .096126989, gun.z))
        self.fake['mouse']['right'] = True
        self.frames(1)
        self.assertAlmostEqual(self.drawn_yaw(), .7504, delta=.07)

    def test_torso_classification_preserves_crouch_even_with_low_weapon(self):
        gun = self.weapon_in_hand(self.GL)
        gun.z = .4
        self.fake.me.named_nodes = self.lua.table_from({'hips': 61, 'chest': 62})
        self.fake.me.nodes = self.lua.table_from({61: self.lua.table_from((1.5, 0, .7)),
                                                62: self.lua.table_from((1.5, 0, 1.05))})
        self.fake['mouse']['right'] = True
        self.frames(1)
        self.assertAlmostEqual(self.drawn_yaw(), .13, delta=.06)

    def test_prone_soldier_on_ground_beside_frv_is_preserved(self):
        gun = self.weapon_in_hand(self.GL)
        gun.z = .3
        self.vehicle_at(1.9, .3, .4)
        self.fake['mouse']['right'] = True
        self.frames(1)
        self.assertGreater(len(self.lines()), 20)

    def test_fixed_geometry_profiles_switch_without_aiming_delay(self):
        gun = self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        for height, expected in ((.3, 1.84), (.7, .13), (1.2, -.06), (.3, 1.84)):
            gun.z = height
            self.frames(1)
            first = self.drawn_yaw()
            self.assertAlmostEqual(first, expected, delta=.08)
            self.frames(120)
            self.assertAlmostEqual(self.drawn_yaw(), first, delta=.001)

    def test_fixed_profiles_follow_recorded_early_flight_height(self):
        # Uses real positions, not the fitted coefficients, to validate the whole rendered vertical path.
        for filename in ('weapon_direction_test6.json', 'weapon_direction_test8.json'):
            with open(os.path.join(HERE, 'fixtures', filename), encoding='utf-8') as f:
                rows = json.load(f)['shots']
            for n in ('3', '4', '5', '6', '7', '8', '9'):
                with self.subTest(source=filename, shot=n):
                    self.setUp()
                    gun = self.weapon_in_hand(self.GL)
                    row = rows[n]
                    self.apply_direction_flight(gun, row)
                    self.fake['mouse']['right'] = True
                    self.frames(1)
                    samples = row['samples']
                    origin, end = samples[0][2:], samples[-1][2:]
                    length = math.hypot(end[0] - origin[0], end[1] - origin[1])
                    hx, hy = (end[0] - origin[0]) / length, (end[1] - origin[1]) / length
                    vertices = [point for line in self.lines() for point in (line[:3], line[3:])]
                    points = sorted(((p[0] - origin[0]) * hx + (p[1] - origin[1]) * hy, p[2]) for p in vertices)
                    for sample in samples[1:]:
                        s = (sample[2] - origin[0]) * hx + (sample[3] - origin[1]) * hy
                        for (a, z1), (b, z2) in zip(points, points[1:]):
                            if a <= s <= b and b > a:
                                predicted = z1 + (z2 - z1) * (s - a) / (b - a)
                                self.assertLess(abs(predicted - sample[4]), .25)
                                break
                        else:
                            self.fail('rendered arc does not reach the recorded early-flight sample')

    def test_vehicle_aim_diagnostic_is_idle_on_foot(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(120)
        self.assertNotIn('vehicle aim', self.logs())

    def test_vehicle_aim_diagnostic_records_entry_and_settled_once_without_firing(self):
        self.weapon_in_hand(self.GL)
        self.vehicle_at(1.9, .3, -.6)
        self.fake['mouse']['right'] = True
        self.frames(120)
        self.assertEqual(self.logs().count('proximity is not confirmed seat membership'), 2)
        self.assertIn('vehicle aim 1 entry', self.logs())
        self.assertIn('vehicle aim 2 settled', self.logs())
        self.assertIn('animation character_state=', self.logs())
        self.assertIn('weapon-root', self.logs())
        self.assertGreater(len(self.lines()), 20, 'evidence collector does not disable passenger arcs')
        self.assertFalse(self.direction_watch().active, 'no projectile scans without firing')
        self.frames(120)
        self.assertEqual(self.logs().count('proximity is not confirmed seat membership'), 2)

    def test_vehicle_aim_diagnostic_has_a_budget(self):
        self.weapon_in_hand(self.GL)
        self.vehicle_at(1.9, .3, -.6)
        for _ in range(20):
            self.fake['mouse']['right'] = True
            self.frames(50)
            self.fake['mouse']['right'] = False
            self.frames(1)
        self.assertEqual(self.logs().count('proximity is not confirmed seat membership'), 16)

    def direction_watch(self):
        return next(w for w in self.fake.watches.values() if w.kinds['a6cd8a90185b6567'])

    def test_weapon_direction_probe_is_idle_without_a_shot(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(120)
        self.assertFalse(self.direction_watch().active)
        self.assertEqual(self.direction_watch().lists, 0)
        self.assertNotIn('weapon direction', self.logs())

    def test_weapon_direction_probe_records_distinct_muzzle_rotation_without_changing_arc(self):
        gun = self.weapon_in_hand(self.GL)
        self.weapon_nodes(gun, (2.238, -.2, 1.296))
        gun.node_f = self.lua.table_from({11: self.lua.table_from((.99, .1, 0))})
        self.fake['mouse']['right'] = True
        self.frames(2)
        before = self.lines()
        self.fake['mouse']['left'] = True
        self.frames(1)
        self.assertEqual(before, self.lines())
        self.assertIn('muzzle-forward 0.990000 0.100000 0.000000', self.logs())
        self.assertIn('root-forward 1.000000 0.000000 0.000000', self.logs())
        self.assertIn('predicted-velocity', self.logs())
        self.assertTrue(self.direction_watch().active)
        self.frames(25)
        self.assertFalse(self.direction_watch().active)
        self.assertEqual(self.logs().count(' shot t='), 1, 'holding the trigger is one bounded window')

    def test_weapon_direction_probe_tracks_candidate_then_stops(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(2)
        self.fake['mouse']['left'] = True
        self.frames(1)
        bullet = self.add_unit('a6cd8a90185b6567', 3, -.2, 1.3)
        self.frames(1)
        bullet.x = 6
        self.frames(3)
        self.assertIn('association unverified', self.logs())
        self.assertIn('track=1', self.logs())
        self.frames(30)
        scans = self.direction_watch().lists
        self.frames(30)
        self.assertEqual(self.direction_watch().lists, scans)
        self.M.shutdown()
        self.assertTrue(self.fake.watch_stopped)

    def test_weapon_direction_probe_has_a_session_budget(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(2)
        for _ in range(12):
            self.fake['mouse']['left'] = True
            self.frames(25)
            self.fake['mouse']['left'] = False
            self.frames(1)
        self.assertEqual(self.logs().count(' shot t='), 3)
        self.assertFalse(self.direction_watch().active)

    def test_probe_keeps_a_separate_vehicle_context_budget(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(2)
        for _ in range(4):
            self.fake['mouse']['left'] = True
            self.frames(25)
            self.fake['mouse']['left'] = False
            self.frames(1)
        self.assertEqual(self.logs().count(' shot t='), 3)
        self.vehicle_at(1.9, .3, -.6)
        self.frames(2)
        self.fake['mouse']['left'] = True
        self.frames(25)
        self.assertEqual(self.logs().count(' shot t='), 4)
        self.assertIn('profile=vehicle/unmeasured fixed=true', self.logs())

    def test_direction_recording_is_globally_bounded_across_profiles(self):
        gun = self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(2)
        def burst():
            for _ in range(3):
                self.fake['mouse']['left'] = True
                self.frames(25)
                self.fake['mouse']['left'] = False
                self.frames(1)
        for height in (.3, .7, 1.2):
            gun.z = height
            burst()
        gun.dead = True
        gun = self.weapon_in_hand('9eb160830321bfd6')
        burst()
        self.vehicle_at(1.9, .3, -.6)
        burst()
        gun.dead = True
        self.weapon_in_hand('f49227a0630a3f7f')
        burst()
        self.assertEqual(self.logs().count(' shot t='), 16)
        self.assertFalse(self.direction_watch().active)

    def test_body_aim_nodes_are_recorded_only_on_bounded_shots(self):
        gun = self.weapon_in_hand(self.GL)
        self.fake.me.named_nodes = self.lua.table_from({'weapon_aim': 21, 'aim_weapon': 22, 'l_clavicle': 23, 'r_clavicle': 24})
        self.fake.me.nodes = self.lua.table_from({21: self.lua.table_from((1.5, 0, .4)),
            22: self.lua.table_from((1.6, 0, .4)), 23: self.lua.table_from((1.5, -.2, .5)),
            24: self.lua.table_from((1.5, .2, .6))})
        self.fake.me.node_f = self.lua.table_from({21: self.lua.table_from((.99, .1, 0)),
                                                22: self.lua.table_from((1, 0, 0))})
        self.fake['mouse']['right'] = True
        self.frames(60)
        self.assertNotIn('avatar-weapon_aim', self.logs())
        before = self.lines()
        self.fake['mouse']['left'] = True
        self.frames(1)
        self.assertEqual(self.lines(), before)
        self.assertIn('avatar-weapon_aim-forward 0.990000 0.100000 0.000000', self.logs())
        self.assertIn('avatar-r_clavicle-position 1.500000 0.200000 0.600000', self.logs())
        self.assertIn('avatar-chest unavailable', self.logs())
        entries = self.logs().count('avatar-weapon_aim-forward')
        self.frames(60)
        self.assertEqual(self.logs().count('avatar-weapon_aim-forward'), entries)

    def test_weapon_direction_probe_cancels_on_world_change(self):
        self.weapon_in_hand(self.GL)
        self.fake['mouse']['right'] = True
        self.frames(2)
        self.fake['mouse']['left'] = True
        self.frames(1)
        self.lua.execute('chef.world_id = function() return 99 end')
        self.frames(1)
        self.assertFalse(self.direction_watch().active)

    def test_weapon_arc_starts_at_the_animated_muzzle_node_instead_of_fixed_offset(self):
        gun = self.weapon_in_hand(self.GL)
        self.weapon_nodes(gun, (2.238, -.2, 1.296), (1.645, -.2, 1.46))
        self.fake['mouse']['right'] = True
        self.frames(3)
        for got, want in zip(self.lines()[1][:3], (2.238, -.2, 1.296)):
            self.assertAlmostEqual(got, want, delta=.0001)
        self.assertIn('weapon muzzle: GL-21 Grenade Launcher (attach_muzzle)', self.logs())
        gun.nodes[11][3] = 1.5
        self.frames(1)
        self.assertAlmostEqual(self.lines()[1][2], 1.5, delta=.0001)

    def test_close_prone_third_person_camera_is_not_the_sight_camera(self):
        gun = self.weapon_in_hand(self.GL)
        gun.z = .3
        self.weapon_nodes(gun, (2.238, -.2, .396), (1.645, -.2, .56))
        self.fake.cam.x, self.fake.cam.y, self.fake.cam.z = 1.15, -.2, .6
        self.fake['mouse']['right'] = True
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)
        self.assertAlmostEqual(self.lines()[1][2], .396, delta=.0001)

    def test_camera_at_sight_still_hides_first_person_weapon_arc(self):
        gun = self.weapon_in_hand(self.GL)
        self.weapon_nodes(gun, (2.238, -.2, 1.296), (1.645, -.2, 1.46))
        self.fake.cam.x, self.fake.cam.y, self.fake.cam.z = 1.645, -.2, 1.46
        self.fake['mouse']['right'] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])
        self.assertIn('(first person: not drawn)', self.logs())

    def test_prone_weapon_at_my_hand_can_be_acquired_while_aim_lags_camera(self):
        p = math.radians(25)
        gun = self.weapon_in_hand(self.GL, f=(math.cos(p), 0, math.sin(p)))
        gun.z = .35
        self.right_hand_at(gun.x, gun.y, gun.z)
        self.weapon_nodes(gun, (2.2, -.2, .63), (1.65, -.2, .55))
        self.fake.look(75)
        self.fake['mouse']['right'] = True
        self.frames(3)
        self.assertGreater(len(self.lines()), 20)

    def test_weapon_node_lookup_is_cached_while_positions_remain_live(self):
        gun = self.weapon_in_hand(self.GL)
        self.weapon_nodes(gun, (2.238, -.2, 1.296), (1.645, -.2, 1.46))
        self.fake['mouse']['right'] = True
        self.frames(3)
        count = self.fake.node_lookups
        self.frames(120)
        self.assertEqual(self.fake.node_lookups, count)

    def test_weapon_node_indices_are_resolved_again_when_the_world_changes(self):
        gun = self.weapon_in_hand(self.GL)
        self.weapon_nodes(gun, (2.238, -.2, 1.296), (1.645, -.2, 1.46))
        self.fake['mouse']['right'] = True
        self.frames(3)
        gun.named_nodes['attach_muzzle'] = 13
        gun.nodes[13] = self.lua.table_from((2.3, -.2, 1.4))
        self.lua.execute('chef.world_id = function() return 5 end')
        self.frames(1)
        self.assertAlmostEqual(self.lines()[1][2], 1.4, delta=.0001)

    def test_bad_muzzle_position_uses_the_existing_fallback(self):
        gun = self.weapon_in_hand(self.GL)
        self.weapon_nodes(gun, (10000, 0, 0))
        self.fake['mouse']['right'] = True
        self.frames(3)
        self.assertAlmostEqual(self.lines()[1][0], gun.x + .45, delta=.0001)
        self.assertIn('legacy fallback; node unavailable', self.logs())

    def test_rocket_uses_its_muzzle_node_name(self):
        gun = self.weapon_in_hand('9f80d67a12a7e40f')
        self.weapon_nodes(gun, (2.189, -.232, 1.365), (1.7, -.3, 1.38), name='muzzle')
        self.fake['mouse']['right'] = True
        self.frames(3)
        self.assertAlmostEqual(self.lines()[1][0], 2.189, delta=.0001)
        self.assertIn('weapon muzzle: GR-8 Recoilless Rifle (muzzle)', self.logs())

    def test_all_supported_weapons_use_their_asset_verified_muzzle_names_and_positions(self):
        with open(os.path.join(HERE, 'fixtures', 'weapon_muzzle_nodes.json'), encoding='utf-8') as f:
            rows = json.load(f)['rows']
        self.assertEqual(len(rows), 16)
        for row in rows:
            with self.subTest(kind=row['kind']):
                self.setUp()
                gun = self.weapon_in_hand(row['kind'])
                def world_point(local):
                    return gun.x + local[1], gun.y - local[0], gun.z + local[2]
                muzzle, sight = world_point(row['muzzle']['position']), world_point(row['sight']['position'])
                self.weapon_nodes(gun, muzzle, sight, row['node'])
                if row['kind'] == 'a955c4ea6f6d4203':
                    self.lua.eval("""function(f)
                      f.E['Network.game_session'] = function() return {} end
                      f.E['Network.peer_id'] = function() return 'me' end
                      f.E['GameSession.objects_owned_by'] = function() return {6} end
                      f.E['GameSession.game_object_exists'] = function() return true end
                      f.E['GameSession.game_object_is_type'] = function() return true end
                      f.E['GameSession.game_object_field'] = function() return 8 end
                    end""")(self.fake)
                self.fake['mouse']['right'] = True
                self.frames(3)
                self.assertGreater(len(self.lines()), 20)
                for got, want in zip(self.lines()[1][:3], muzzle):
                    self.assertAlmostEqual(got, want, delta=.0001)

    def test_varying_weapon_alignment_diagnostics_are_rate_limited(self):
        gun = self.weapon_in_hand(self.GL, f=(.1, .99, 0))
        self.fake['mouse']['right'] = True
        for i in range(120):
            gun.f[1] = .1 + i * .001
            self.frames(1)
        self.assertLessEqual(self.logs().count('weapon aimed: none'), 5)

    def test_a_worn_weapon_draws_nothing(self):
        self.weapon_in_hand(self.GL, f=(0, 0, -1))      # on my back, pointing down
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])
        self.assertIn("weapon aimed: none", self.logs())

    def test_no_weapon_arc_without_aiming(self):
        self.weapon_in_hand(self.GL)
        self.frames(3)
        self.assertEqual(self.lines(), [])

    def test_the_airburst_rocket_ends_at_its_burst(self):
        self.weapon_in_hand("26e40437ea275296")
        self.fake["mouse"]["right"] = True
        self.frames(3)
        far = max(max(l[0], l[3]) for l in self.lines())
        self.assertGreater(far, 340)          # about 1.5 s at 250 m/s, a little slowed
        self.assertLess(far, 380)

    def test_weapon_arcs_can_be_turned_off(self):
        self.weapon_in_hand(self.GL)
        self.fake.changes["weapon_arcs"](False)
        self.fake["mouse"]["right"] = True
        self.frames(3)
        self.assertEqual(self.lines(), [])


if __name__ == "__main__":
    unittest.main()
