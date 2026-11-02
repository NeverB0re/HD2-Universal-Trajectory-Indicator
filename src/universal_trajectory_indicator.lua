-- HD2-Addon: mods/codex/throwable_arcs
-- Universal Trajectory Indicator: while a stratagem ball is in my hand and left mouse is held, or C4 is aimed with right mouse, draws
-- where it will fly. The arc is a world line: the game hides it behind walls and ground, so where it goes into the
-- ground is where it lands (the terrain can't be asked). Below native Render Scale the game clips the 3D scene's drawing
-- to a corner of the screen when the game's anti-aliasing is off (with it on, it shows whole). The numbers are measured
-- from real throws (mods/universal-trajectory-indicator/PLAN.md, section 6-1). 1.1.0: also weapons whose round falls, while aimed
-- (WEAPON_ARCS_PLAN.md), and grenades, while G is held or one in hand is aimed or cooked.
-- C4's hand pose and mode are read as NarrowHUD by luka189 reads them (Nexus 17882); the armour table comes from HD2
-- Transmog's catalog (Nexus 16633).
local chef = ...
local M = {}
local VERSION = '1.2.1'

if chef.has and chef.has('own_log') then chef.own_log('universal_trajectory_indicator') end
local function log(fmt, ...) chef.log(fmt, ...) end

local STRATAGEM_BALL = '16f397ca5f51f271'
-- A ball is let go RELEASE_UP m above where it is held in the aim (the arm swings up), heading as the camera looks,
-- LIFT above its pitch, at SPEED: fitted on 24 measured throws along 1-40 m of their flight (test.18-30; prone ones fit
-- within 0.3 m). Until 1.0.0 the arc started at the ball and eased into a path from the camera (9 degrees up), which
-- fit far throws but was off near ones.
local SPEED, LIFT, RELEASE_UP, GRAVITY = 22, math.rad(7.8), 0.4, 9.81
local STEP = 0.03                -- seconds per arc segment
local MOST_T = 6                 -- seconds of flight drawn at most
local DEEPEST = 15               -- m under my feet the arc goes at most (it is hidden under the ground anyway)
-- a stratagem ball in my hand: within HAND m of my helldiver across, HAND_LOW to HAND_HIGH m above its feet (held balls
-- in test.10-12, standing: 0.36-0.54 m across, 0.74-1.30 m up; crouched or prone it is lower, down to the ground).
-- Without my helldiver: within 6 m of the camera, at most 1.5 m under it.
local HAND, HAND_LOW, HAND_HIGH = 1.2, -0.3, 2.2
-- while aiming, the ball must stay this close (the swing moves it): gone, the arc goes at once. test.18 kept the arc
-- up until left was let go, so a stratagem put away and a shot straight after drew it for a moment
local KEEP, KEEP_LOW, KEEP_HIGH = 2, -0.5, 2.8

local PLAYER = '4d1c334d294dfa97'

local now = function() return chef.time() end
local function camera_pitch(c) return math.atan2(c.fz, math.sqrt(c.fx * c.fx + c.fy * c.fy)) end

-- ------------------------------------------------------------------ my feet
local players = chef.watch and chef.watch({ [PLAYER] = true }, 2)
local feet_z, me = nil, nil      -- me: { x, y, z } of my helldiver (its feet)
local me_unit = nil              -- my helldiver's unit
-- Mine is the helldiver nearest the camera within 6 m across; once found it is kept while it is within KEEP_ME m: a
-- vehicle's camera is farther off (1.0.1-test.2 lost me in a passenger seat, aiming up), and others sit nearer to it.
local KEEP_ME = 15
local mine = nil

local function update_feet(c)
  feet_z, me, me_unit = nil, nil, nil
  if not players then return end
  if mine and chef.unit_alive(mine) then
    local x, y, z = chef.unit_position(mine)
    if x and (x - c.x) ^ 2 + (y - c.y) ^ 2 < KEEP_ME * KEEP_ME then
      feet_z, me, me_unit = z, { x, y, z }, mine
      return
    end
  end
  mine = nil
  local best
  for _, it in ipairs(players.items) do
    if chef.unit_alive(it.unit) then
      local x, y, z = chef.unit_position(it.unit)
      if x then
        local d = (x - c.x) ^ 2 + (y - c.y) ^ 2
        if d < 36 and (not best or d < best) then best, feet_z, me, me_unit = d, z, { x, y, z }, it.unit end
      end
    end
  end
  mine = me_unit
end

-- My velocity, from my feet over the last MOVE_OVER s. A throw is faster by CARRY times my speed along where I aim, up
-- to CARRY_MOST m/s either way, and gets none of it across (1.0.3-test.1 to 6, 36 throws: walking forward throws
-- farther and higher, running no farther than walking, strafing no wider; 8 C4 throws walking at 2.2 m/s carried
-- 1.30-1.47 times it).
local MOVE_OVER, CARRY, CARRY_MOST = 0.15, 1.4, 3
local trail = {}                 -- my feet: { t, x, y, z }, the last MOVE_OVER s and a bit

local function update_trail()
  if not me then trail = {} return end
  if trail.unit ~= me_unit then trail = { unit = me_unit } end
  local t = now()
  trail[#trail + 1] = { t, me[1], me[2], me[3] }
  while #trail > 2 and t - trail[2][1] >= MOVE_OVER do table.remove(trail, 1) end
end

local function my_move()
  local a, b = trail[1], trail[#trail]
  if not (a and b and b[1] - a[1] > 0.02) then return 0, 0, 0 end
  local dt = b[1] - a[1]
  return (b[2] - a[2]) / dt, (b[3] - a[3]) / dt, (b[4] - a[4]) / dt
end

-- ------------------------------------------------------------------ my armour (the throw-range perks)
-- Servo-Assisted armours throw 30% farther, Desert Stormer ones 20%. The armour is told from the units on my helldiver
-- when aiming begins: the armour in the table (src/armour_table.lua, from HD2 Transmog's catalog) with the largest
-- share of its units there, at least ARMOUR_SHARE. It takes one pass over all the world's units (about 3 ms), so it is
-- done once for my helldiver (a mission's armour doesn't change; a new helldiver after a respawn is looked at again),
-- or again at the next aim while none was found.
-- The throw speed, as measured (not the square root of the range bonus: test.26 drew Servo-Assisted throws at 25.1 m/s,
-- they flew 25.5-26.8): stratagem balls 1.1x with Desert Stormer (test.17: 24.0-24.2 m/s of 22), 1.2x with
-- Servo-Assisted (test.26: 25.5-26.8, about 26.5); C4 1.3x with Servo-Assisted (test.26: about 29 of 22.4), and 1.2x with
-- Desert Stormer (test.28: 26.8).
local SPEED_UP = { [20] = { 1.1, 1.2 }, [30] = { 1.2, 1.3 } }   -- range bonus in % -> { stratagem, C4 }
-- A look mod can put another armour's units on me. HD2 Transmog spawns copies of the look and hides my own armour's
-- units (they stay on me): its TransmogUI.worn('armor') lists my own, so with it running those are used. Another
-- such mod leaves two whole armours on me: when they differ in range, it can't be told which is mine (no bonus then).
local ARMOUR = "@ARMOUR@"
local ARMOUR_SHARE = 0.6
local armour_rows, armour_kinds = {}, {}   -- rows: { name, bonus, size }; kinds: kind -> row indices
for i, row in ipairs(type(ARMOUR) == 'table' and ARMOUR or {}) do
  local n = 0
  for kind in row[3]:gmatch('%x+') do
    n = n + 1
    armour_kinds[kind] = armour_kinds[kind] or {}
    table.insert(armour_kinds[kind], i)
  end
  armour_rows[i] = { name = row[1], bonus = row[2], size = n }
end
local throw_bonus, said_armour = 0, nil
local armour_of = nil            -- the helldiver the armour was told for

local function speed_up(c4)
  local f = SPEED_UP[math.floor(throw_bonus * 100 + 0.5)]
  return f and f[c4 and 2 or 1] or 1
end

-- my own armour's unit kinds from HD2 Transmog, or nil without it (or when it has no avatar of mine)
local function transmog_kinds()
  local ok, T = pcall(function() return TransmogUI end)
  if not ok or type(T) ~= 'table' or type(T.worn) ~= 'function' then return nil end
  local done, units = pcall(T.worn, 'armor')
  if not done or type(units) ~= 'table' or #units == 0 then return nil end
  local kinds = {}
  for _, u in ipairs(units) do
    local k = chef.unit_kind(u)
    if k then kinds[k] = true end
  end
  return next(kinds) and kinds or nil
end

-- the armour units on my helldiver: kind -> true
local function kinds_on_me()
  local w = chef.world()
  local units = w and chef.call('World.units', w)
  if type(units) ~= 'table' then return nil end
  local kinds = {}
  for _, u in ipairs(units) do
    local kind = chef.unit_alive(u) and chef.unit_kind(u)
    if kind and not kinds[kind] and armour_kinds[kind] then
      local x, y, z = chef.unit_position(u)
      if x and (x - me[1]) ^ 2 + (y - me[2]) ^ 2 < 2.25 and z > me[3] - 0.5 and z < me[3] + 2.5 then kinds[kind] = true end
    end
  end
  return kinds
end

local function find_armour()
  if not me or (me_unit and me_unit == armour_of) then return end
  local from = 'Transmog'
  local kinds = transmog_kinds()
  if not kinds then kinds, from = kinds_on_me(), 'on me' end
  if not kinds then return end
  local hits = {}
  for kind in pairs(kinds) do
    for _, i in ipairs(armour_kinds[kind] or {}) do hits[i] = (hits[i] or 0) + 1 end
  end
  local best, bi, whole = ARMOUR_SHARE, nil, {}   -- whole: the bonuses of armours all of whose units are there
  for i, row in ipairs(armour_rows) do
    local share = (hits[i] or 0) / row.size
    if share > best or (share == best and not bi) then best, bi = share, i end
    if share >= 0.95 then whole[row.bonus] = row.name end
  end
  local two = nil
  for b, n in pairs(whole) do if bi and b ~= armour_rows[bi].bonus then two = n end end
  throw_bonus = bi and not two and armour_rows[bi].bonus or 0
  if bi then armour_of = me_unit end
  local name = bi and armour_rows[bi].name or 'none of the table'
  if two then name = name .. ' and ' .. two .. ' (a look mod? no bonus)' end
  name = name .. ' [' .. from .. ']'
  if name ~= said_armour then
    said_armour = name
    log('armour: %s%s, throw range +%d%%', name, bi and string.format(' (%d%% of its units)', best * 100 + 0.5) or '',
        throw_bonus * 100 + 0.5)
  end
end

-- ------------------------------------------------------------------ the buttons
-- The throw and the aim are the mouse's left and right buttons, and (1.0.4) a controller's right and left triggers: the
-- game's default layouts. Buttons rebound in the game aren't followed (they are buttons to the mod, not the game's
-- actions). The controller: the first of the engine's Pad1 to Pad8 that is active or connected, as Chef Shared Loader
-- finds its menu's, looked at again every PAD_LOOK s; its triggers by the names it lists itself. Only its number and
-- button indexes are kept between frames. Not tried on a real controller before 1.0.4's release.
local PAD_LOOK = 1
local PAD_THROW, PAD_AIM = { 'right_trigger', 'r2' }, { 'left_trigger', 'l2' }
local pad = { n = nil, button = nil, throw = nil, aim = nil, next = 0, said = nil }
local throw_down, aim_down = false, false      -- this frame's

local function find_pad()
  if pad.n then
    local p = 'Pad' .. pad.n
    if chef.call(p .. '.active') == true or chef.call(p .. '.connected') == true then return end
    pad.n, pad.button, pad.throw, pad.aim = nil, nil, nil, nil
  end
  for n = 1, 8 do
    local p = 'Pad' .. n
    if chef.call(p .. '.active') == true or chef.call(p .. '.connected') == true then
      local count, by, names = chef.call(p .. '.num_buttons'), {}, {}
      if type(count) == 'number' and count > 0 and count <= 64 then
        for i = 0, count - 1 do
          local nm = chef.call(p .. '.button_name', i)
          if type(nm) == 'string' and nm ~= '' then by[nm:lower()] = i; names[#names + 1] = nm:lower() end
        end
      end
      local function first(list) for _, nm in ipairs(list) do if by[nm] then return by[nm] end end end
      pad.n, pad.button, pad.throw, pad.aim = n, p .. '.button', first(PAD_THROW), first(PAD_AIM)
      local said = p .. (pad.throw and pad.aim and ', triggers found'
                         or ', no triggers among: ' .. table.concat(names, ' '))
      if said ~= pad.said then pad.said = said; log('controller: %s', said) end
      return
    end
  end
end

local function pad_down(i)
  if not (pad.button and i) then return false end
  local v = chef.call(pad.button, i)
  return type(v) == 'number' and v > 0.5
end

local function read_buttons()
  if now() >= pad.next then
    pad.next = now() + PAD_LOOK
    find_pad()
  end
  throw_down = chef.mouse_down('left') == true or pad_down(pad.throw)
  aim_down = chef.mouse_down('right') == true or pad_down(pad.aim)
end

-- ------------------------------------------------------------------ aiming
-- The balls come from a watch on their kind, always on: the loader asks the engine for that kind only, about 0.1 ms
-- every 0.5 s (test.13-17 ran it only after the stratagem key, which players who moved that key had to set in the
-- options; test.12 and before passed over every unit, 2.6-3.4 ms). A left click asks for a fresh list and looks for a
-- ball in hand for BALL_SCAN_FOR s; none, it is a shot.
local BALL_SCAN_FOR = 1
local ball_watch = chef.watch and chef.watch({ [STRATAGEM_BALL] = true }, 0.5)
local held_since = 0
local was_left, aiming, ball = false, false, nil
local looking = false

-- the nearest stratagem ball in my hand, or nil
local function ball_in_hand(c)
  if not ball_watch then return nil end
  local best, bu
  for _, it in ipairs(ball_watch.items) do
    local u = it.unit
    if chef.unit_alive(u) then
      local x, y, z = chef.unit_position(u)
      if x then
        local d
        if me then
          local across, up = math.sqrt((x - me[1]) ^ 2 + (y - me[2]) ^ 2), z - me[3]
          if across <= HAND and up >= HAND_LOW and up <= HAND_HIGH then d = across end
        elseif z >= c.z - 1.5 then
          d = math.sqrt((x - c.x) ^ 2 + (y - c.y) ^ 2 + (z - c.z) ^ 2)
          if d > 6 then d = nil end
        end
        if d and (not best or d < best) then best, bu = d, u end
      end
    end
  end
  return bu
end

-- is the ball still in my hand (loosely)?
local function still_in_hand(u)
  if not (u and chef.unit_alive(u)) then return false end
  local x, y, z = chef.unit_position(u)
  if not x then return false end
  if not me then return true end
  local up = z - me[3]
  return (x - me[1]) ^ 2 + (y - me[2]) ^ 2 <= KEEP * KEEP and up >= KEEP_LOW and up <= KEEP_HIGH
end

-- A ball in hand while its code is still going in (unlit) is held in front of me; once the code is in (lit), standing
-- or crouched, it is pulled back for the throw (test.21: from 0.2-0.4 m ahead of my feet to 0 to -0.3 m, within 0.3 s;
-- a put-away ball isn't). So a ball counts as ready once it was seen pulled back READY_PULL m or more, within
-- READY_WINDOW s, to under READY_AHEAD m ahead, while left was up: test.18-20 drew the arc for a ball still waiting for
-- its code (left during code entry, or a shot right after putting it away).
-- With left already held when the code goes in, there is no pull-back: the ball goes straight up into the aim, about
-- 0.2 m above where it was (test.22, standing: 1.25 -> 1.47 m above my feet; test.21, crouched +0.15-0.3, prone
-- +0.2-0.5). So while left is held with a ball in hand that isn't ready, it becomes the aim once it rose RAISE m above
-- its height when left went down; it is watched as long as left is held and it stays in hand.
-- Right mouse aims a ball too (1.0.1): held like left, the throw still being left's release.
local READY_PULL, READY_AHEAD, READY_WINDOW, RAISE = 0.15, 0.05, 0.5, 0.15
local pending, pending_up = nil, nil   -- a ball in hand with left held, not ready yet, and its height then
local ready_ball, pose = nil, { list = {} }   -- pose: the ball in hand while left is up, and where it was ({ t, ahead })

local function ball_ahead(c, u)
  local x, y, z = chef.unit_position(u)
  if not (x and me) then return nil end
  local fh = math.sqrt(c.fx * c.fx + c.fy * c.fy)
  if fh < 1e-6 then return nil end
  return ((x - me[1]) * c.fx + (y - me[2]) * c.fy) / fh, z - me[3]
end

local function watch_pose(c)
  local u = ball_in_hand(c)
  if u ~= pose.u then pose, ready_ball = { u = u, list = {} }, nil end
  if not u then return end
  local ahead = ball_ahead(c, u)
  if not ahead then return end
  local t, list = now(), pose.list
  list[#list + 1] = { t, ahead }
  while #list > 1 and t - list[1][1] > READY_WINDOW do table.remove(list, 1) end
  local most = ahead
  for _, e in ipairs(list) do if e[2] > most then most = e[2] end end
  if ahead < READY_AHEAD and most - ahead >= READY_PULL and ready_ball ~= u then
    ready_ball = u
  end
end


local was_hold = false

-- After the throw is let go (left released with a ball, left pressed with C4 aimed) the arc stays up until it leaves my
-- hand (1.0.3; the swing takes a moment): it keeps following the camera, from where the hand was then, kept by my feet.
-- It ends when the ball is HOLD_GONE m or more from there, or after HOLD_MOST s. C4's hold just lasts C4_HOLD s: the
-- charge leaves the hand about then (1.0.3-test.2, fitted back from its flight), but the game lists a new charge only
-- every half second or so, too late to end the arc on.
local HOLD_MOST, HOLD_GONE, C4_HOLD = 0.6, 1.5, 0.15
local hold = nil                 -- { c4, unit, off = { from my feet }, at, pos }

local function start_hold(unit, c4)
  local x, y, z
  if unit and chef.unit_alive(unit) then x, y, z = chef.unit_position(unit) end
  if not x then hold = nil return end
  hold = { c4 = c4, unit = unit, at = now(), pos = { x, y, z },
           off = me and { x - me[1], y - me[2], z - me[3] } or nil }
end

local function read_input(c)
  local t = now()
  local left = throw_down
  local down = left or aim_down
  if not left then watch_pose(c) end
  if down and not was_hold then
    held_since, looking = t, true
    if ball_watch then ball_watch.refresh() end
  end
  local held = false
  if was_left and not left and aiming then
    start_hold(ball, false)
    ball, ready_ball, looking = nil, nil, false   -- thrown
  elseif down then
    if aiming then
      held = still_in_hand(ball)
      if not held then ball, looking = nil, false end
    elseif pending then
      if not still_in_hand(pending) then
        pending, looking = nil, false        -- put away: a shot
      else
        local _, up = ball_ahead(c, pending)
        if pending == ready_ball or (up and up - pending_up >= RAISE) then
          ball, pending, held = pending, nil, true
          find_armour()
        end
      end
    elseif looking then
      local u = ball_in_hand(c)
      if u and u == ready_ball then
        ball, held = u, true
        find_armour()
      elseif u then
        local _, up = ball_ahead(c, u)
        pending, pending_up = u, up or 0     -- not ready (code still going in?): watched for the raise into the aim
      elseif t - held_since > BALL_SCAN_FOR then
        looking = false                      -- no ball in hand: a shot
      end
    end
  end
  if not down then pending = nil end
  was_left, was_hold = left, down
  aiming = held
end

-- ------------------------------------------------------------------ C4
-- C4 is aimed with right mouse (left alone throws it at once): right held with C4 in my hand is the aim; it ends at
-- left (the throw) or when right is let go. Which weapon is in my hand: my helldiver's hand pose, the animation
-- variable weapon_selected, as NarrowHUD (luka189, Nexus 17882) reads it: C4_GRIP for C4 (its learned table: 42).
-- Without that variable, no C4 arc (until 1.0.2 the detonator's place alone told it then; 1.0.3 after a report of an
-- arc while aiming the Censor rifle). The aim pose is told by the detonator's unit (filediver: equipment/backpacks/
-- c4_charge_backpack/c4_charge_detonator; its charge is no unit until it flies, and my helldiver's 1 mesh never
-- changes, test.24-25), held in my right hand (test.25, standing: about 0 ahead, 0.4 right, 1.05 up from my feet):
-- right held it goes forward into the aim within 0.3 s, from about 0.40 m from my feet across to 0.53-0.55 m, not above
-- C4_HIGH m (the throw raises it to 2.05-2.11 m). The hand pose alone isn't the aim (1.0.1): putting C4 away while
-- aiming kept the pose a moment and drew the arc, and right in a vehicle's driver seat (no aiming there) drew it as
-- well. The aim pose: the detonator C4_PUSH m or more farther from
-- my feet (across) than it was nearest since right went down; kept while it stays C4_KEEP m or more farther. Its
-- distance, not how far ahead along the camera's heading (1.0.1-test.1): turning fast, my helldiver turns after the
-- camera, and seated in a vehicle it faces the vehicle's way, and the arc came and went with the heading.
-- After a throw, no arc for C4_REARM s: test.28 drew it again 0.2-0.3 s after each throw, from the arm still swinging
-- (0.8 ahead, 1.3-1.6 m up).
-- The charge is let go C4_RELEASE_UP m above the detonator in the aim pose (the arm swings up and throws from higher),
-- at about 22.4 m/s, C4_LIFT above the camera's pitch: fitted on 5 measured throws (test.26-30), 0.1 m off along 1-40 m.
local C4_DET = '51f50d6321f52f3d'
local C4_SPEED, C4_LIFT, C4_RELEASE_UP = 22.4, math.rad(4.4), 1.0
local C4_PUSH, C4_KEEP, C4_HIGH = 0.1, 0.05, 1.6
-- Leaning out of a vehicle's window to aim, the detonator gets 1.15-1.2 m from my feet across (1.0.1-test.2): its hand
-- reaches C4_HAND m. Prone (0.06-0.46 m above my feet), crouched (0.56-0.69 m) and sliding on my knees (0.55-0.58 m)
-- it is under C4_LOW_UP m and right moves it little or not at all (1.0.1-test.2-4; standing it is 0.82 m up or more):
-- there, C4 in hand (the hand pose) and right held is the aim. Not in a vehicle: in the driver's seat it is 0.46 m up
-- (test.4 drew the arc there).
-- Diving, the hand pose reads 40 (as with a grenade) while the detonator lies low on my left (1.0.1-test.3): within
-- C4_DIVE s of C4's pose, 40 counts as C4 with the detonator under C4_PRONE_UP m, or while an aim goes on (in the air
-- it flickers, test.4). An aim that stops being one is kept C4_GRACE s, for such moments.
-- Seated in a vehicle, aiming behind brings the detonator in to 0.1-0.2 m from my feet (1.0.1-test.3): there an aim
-- once begun (leaning out moves it outward; in the driver's seat it never begins) is kept while right is held and C4 is
-- in hand.
-- On a tank's top seat it already sits 0.45 m off my feet and stays there; aiming raises it instead, from 0.59 to
-- 1.08-1.21 m (1.0.1-test.9): risen C4_RAISE m or more above its lowest since right went down is the aim pose too.
local C4_HAND, C4_LOW_UP, C4_PRONE_UP, C4_DIVE, DIVE_GRIP, C4_GRACE, C4_RAISE = 1.6, 0.75, 0.5, 2, 40, 0.25, 0.3
local c4_ready_at = -100
local c4_grip_at, grip_next = -100, 0   -- when C4's hand pose was last seen, and is next looked at with right up
local in_vehicle                 -- function() below (the icon's)
local C4_GRIP, C4_REARM = 42, 0.8
local c4_rearm = 0
local det_watch = chef.watch and chef.watch({ [C4_DET] = true }, 0.5)
local was_right, c4_aim, c4_det, c4_least, c4_low = false, false, nil, nil, nil
local c4_posed = false           -- in C4's aim pose (DEPLOY or DETONATE alike; c4_aim: and the arc drawn)

-- C4's mode: DEPLOY (a charge in hand, thrown) or DETONATE (the detonator in hand; right drew the arc there too in
-- test.27). Read as NarrowHUD (luka189, Nexus 17882) reads it: the C4 is a network game object of mine, of the type
-- C4_TYPE (a stand-in name with the same 32-bit hash as the real one, type 6b2c3bed, from the game's network config),
-- and its options field (C4_OPTIONS) holds the mode in the bits at 256 (80 deploy, 336 detonate). In someone else's
-- game the host may own it: the host's C4 objects whose owner field (C4_OWNER) is me count too. Only the one I carry
-- (its carry field, C4_CARRY, a multiple of 4: NarrowHUD's rule): a detonator swapped for another one stays mine where
-- it was dropped, and 1.0.0 kept reading it. The object is looked for when right goes down or for the icon (at most
-- every C4_SCAN s while none is found) and kept while I carry it; before each read it must still exist and be that
-- type (reading a gone object's field can end the game, NarrowHUD's notes). Not readable (a game patch, a Chef that
-- refuses the calls): the arc shows in either mode, and no icon.
local C4_TYPE, C4_OPTIONS, C4_OWNER, C4_CARRY = 'kbv6zx', 'ozvglfc', 'g5g7b9d', 'n5jmvf'
local C4_SCAN = 2
local c4_obj = { goid = nil, world = nil, next = 0 }

-- 1.1.0: a network field is read only when the game declares it for that type now (Network.object_info, as NarrowHUD
-- checks on a game version it wasn't made for): the names above are from one game build's network config, and reading
-- a field a type doesn't declare can end the game, so a patch that moved one turned C4's icon off instead. Field ids
-- (the 32-bit hashes the info lists, lower-case hex without leading zeros) from NarrowHUD's data. Info not given (a
-- Chef that refuses it): nothing is read.
-- (in a function of its own: the file is near Lua 5.1's 200 locals)
local read_field = (function()
local FIELD_ID = { [C4_OPTIONS] = '31f86165', [C4_OWNER] = '3ccffa7f', [C4_CARRY] = '788b9753', if5_pz = '49c250a6',
                   u4d1h9a = 'f27c68e', rm_qp0d = 'bdc1cb8a', x4joxek = 'af97ede7' }
local declared = {}              -- type name -> { [field id] = true }, or false when the info isn't given
return function(gs, goid, type_name, field, tag)
  local set = declared[type_name]
  if set == nil then
    local ok, info = pcall(chef.call_kind, 'Network.object_info', 'objinfo ' .. type_name, type_name)
    set = false
    if ok and type(info) == 'table' and type(info.fields) == 'table' then
      set = {}
      for _, f in ipairs(info.fields) do
        local id = type(f) == 'table' and f.id
        if type(id) == 'number' then id = string.format('%x', id) end
        if type(id) == 'string' then set[(string.gsub(string.lower(id), '^0+', ''))] = true end
      end
    end
    declared[type_name] = set
    if not set then log('network: no field info for type %s: its fields are not read', type_name) end
  end
  if not set then return nil end
  if not set[FIELD_ID[field]] then
    if set[field] ~= 'said' then
      set[field] = 'said'
      log('network: type %s no longer declares field %s (a game patch?): not read', type_name, field)
    end
    return nil
  end
  return chef.call_kind('GameSession.game_object_field', tag, gs, goid, field)
end
end)()

local function peer_text(v)
  if type(v) == 'string' then return (string.gsub(string.lower(v), '^0+', '')) end
  return nil
end

local function is_c4(gs, goid)
  return chef.call_kind('GameSession.game_object_exists', 'c4 exists', gs, goid) == true
     and chef.call_kind('GameSession.game_object_is_type', 'c4 type', gs, goid, C4_TYPE) == true
end

-- (a C4 that I carry: one that is still there and is C4 first)
local function carried(gs, goid)
  local v = read_field(gs, goid, C4_TYPE, C4_CARRY, 'c4 carry')
  return type(v) == 'number' and v % 4 == 0
end

local function find_c4_object(gs, peer)
  local mine = chef.call_kind('GameSession.objects_owned_by', 'c4 owned', gs, peer)
  if type(mine) ~= 'table' then return nil end
  for _, goid in pairs(mine) do if is_c4(gs, goid) and carried(gs, goid) then return goid end end
  local host = chef.call_kind('GameSession.game_session_host', 'c4 host', gs)
  if host == nil or host == peer then return nil end
  local theirs = chef.call_kind('GameSession.objects_owned_by', 'c4 owned', gs, host)
  for _, goid in pairs(type(theirs) == 'table' and theirs or {}) do
    if is_c4(gs, goid) and carried(gs, goid)
       and peer_text(read_field(gs, goid, C4_TYPE, C4_OWNER, 'c4 owner')) == peer_text(peer) then
      return goid
    end
  end
  return nil
end

-- 'deploy', 'detonate', or nil when it can't be told; and the options value. look: may look for the object
local function c4_mode(look)
  local gs = chef.call_kind('Network.game_session', 'c4 session')
  local peer = chef.call_kind('Network.peer_id', 'c4 peer')
  if gs == nil or peer == nil then return nil end
  local w = chef.world_id()
  if c4_obj.world ~= w then c4_obj.goid, c4_obj.world, c4_obj.next = nil, w, 0 end
  if c4_obj.goid and not (is_c4(gs, c4_obj.goid) and carried(gs, c4_obj.goid)) then c4_obj.goid = nil end
  if not c4_obj.goid then
    if not look or now() < c4_obj.next then return nil end
    c4_obj.next = now() + C4_SCAN
    c4_obj.goid = find_c4_object(gs, peer)
    if not c4_obj.goid then return nil end
  end
  local v = tonumber(read_field(gs, c4_obj.goid, C4_TYPE, C4_OPTIONS, 'c4 options'))
  if not v then return nil end
  local m = math.floor(v / 256) % 4
  return (m == 0 and 'deploy') or (m == 1 and 'detonate') or nil, v
end

-- the nearest detonator in my hand, and how far it is from my feet across and above them, or nil
local function det_in_hand()
  if not (det_watch and me) then return nil end
  local best, bu, high
  for _, it in ipairs(det_watch.items) do
    local u = it.unit
    if chef.unit_alive(u) then
      local x, y, z = chef.unit_position(u)
      if x then
        local dx, dy, up = x - me[1], y - me[2], z - me[3]
        local across = math.sqrt(dx * dx + dy * dy)
        if across <= C4_HAND and up >= HAND_LOW and up <= HAND_HIGH and (not best or across < best) then
          best, bu, high = across, u, up
        end
      end
    end
  end
  return bu, best, high
end

-- my helldiver's hand pose (NarrowHUD's weapon_selected: 0 nothing in hand, 40 and 41 grenades and stratagem balls),
-- or nil when it can't be read
local GRIP_VARIABLE = 'weapon_selected'
-- (the variable's index per unit; not found, it is looked for again after GRIP_RETRY s)
local GRIP_RETRY = 5
local grip_index = setmetatable({}, { __mode = 'k' })
local grip_frame = {}
local function hand_pose()
  local u = me_unit
  if not (u and chef.unit_alive(u)) then return nil end
  local t = now()
  if grip_frame.u == u and grip_frame.t == t then return grip_frame.v end
  grip_frame.u, grip_frame.t, grip_frame.v = u, t, nil
  local idx = grip_index[u]
  if idx == nil or (type(idx) == 'table' and now() >= idx.retry) then
    idx = { retry = now() + GRIP_RETRY }
    if chef.call_kind('Unit.has_animation_state_machine', PLAYER, u) == true
       and chef.call_kind('Unit.animation_has_variable', PLAYER, u, GRIP_VARIABLE) == true then
      local i = chef.call_kind('Unit.animation_find_variable', PLAYER, u, GRIP_VARIABLE)
      if type(i) == 'number' then idx = i end
    end
    grip_index[u] = idx
  end
  if type(idx) ~= 'number' then return nil end
  local v = chef.call_kind('Unit.animation_get_variable', PLAYER, u, idx)
  v = type(v) == 'number' and math.floor(v + 0.5) or nil
  grip_frame.v = v
  if v == C4_GRIP then c4_grip_at = now() end
  return v
end

-- Based on NarrowHUD 2.0.0's hand-relative grenade detection (12_throw.lua, attach_hand_r). The node is resolved
-- once per Helldiver; a missing node is retried slowly. Position is current, cached only for this frame.
local right_hand = (function()
  local state = {}
  return function()
    if not (me_unit and chef.unit_node) then return nil end
    local t = now()
    if state.u ~= me_unit then state = { u = me_unit, next = 0 } end
    if state.t == t then return state.p end
    state.t, state.p = t, nil
    if not state.node and t >= state.next then
      state.node, state.next = chef.unit_node(me_unit, 'attach_hand_r'), t + GRIP_RETRY
    end
    if state.node then
      local x, y, z = chef.unit_position(me_unit, state.node)
      if x then state.p = { x, y, z } end
    end
    return state.p
  end
end)()

local function read_c4(c)
  local right, left = aim_down, throw_down
  if right and not was_right then
    c4_least, c4_low = nil, nil
    if det_watch then det_watch.refresh() end
  end
  local held, posed = false, false
  if not right and now() >= grip_next then
    grip_next = now() + 0.2
    hand_pose()
  end
  if right and not aiming and det_watch then
    local u, across, high = det_in_hand()
    local grip = hand_pose()
    if grip == DIVE_GRIP and u and (c4_posed or high < C4_PRONE_UP) and now() - c4_grip_at <= C4_DIVE then grip = C4_GRIP end
    local ready = false
    if u and grip == C4_GRIP then
      c4_least, c4_low = math.min(c4_least or across, across), math.min(c4_low or high, high)
      ready = high <= C4_HIGH
              and (across - c4_least >= (c4_posed and C4_KEEP or C4_PUSH) or high - c4_low >= C4_RAISE)
      if in_vehicle() then
        if c4_posed then ready = true end
      elseif high < C4_LOW_UP then
        ready = true
      end
      if ready then c4_ready_at = now() end
      if c4_posed and not ready and now() - c4_ready_at < C4_GRACE then ready = true end
    end
    if c4_aim and left then
      c4_rearm = now() + C4_REARM
      start_hold(c4_det, true)
    end
    posed = ready == true and not left and now() >= c4_rearm
    held = posed and c4_mode(not c4_posed) ~= 'detonate'
    if held and not c4_aim then find_armour() end
    if held then c4_det = u or c4_det end
  end
  was_right = right
  c4_aim, c4_posed = held, posed
  if not held then c4_det = nil end
end

-- ------------------------------------------------------------------ drawing
-- The arc's colour, an option: green (the default from 1.0.4; 1.0.4-test.1 saw it keep its colour where white turned
-- faint blue, red or green), white (until 1.0.3), blue or red.
local COLORS = { { 0, 255, 0 }, { 255, 255, 255 }, { 80, 160, 255 }, { 255, 70, 70 } }
local arc_color = 1
local arc_width, arc_solid = 3, false   -- render pixels wide; solid: no dashes
-- The engine's lines are one render pixel wide whatever is asked. An arc arc_width render pixels wide is lines half a
-- render pixel apart (a whole pixel apart they show as a bundle of strands), at any render scale. The render scale: the game's
-- settings file's render resolution over the screen's height, read every SCALE_EVERY s. A white arc came out faint
-- blue, red or green in parts, at some places and headings only, on any map, at native scale and with anti-aliasing
-- off alike (1.0.3-test.3 and after); the cause is unknown.
local SCALE_EVERY = 2
local render_scale, scale_next = 1, 0
-- the arc is dashed by flight time: DASH segments drawn, GAP left out (about 1.3 m and 0.7 m). test.10-11 measured
-- dashes in px from the camera, so they slid along the arc whenever the camera moved: it rippled as you turned
local DASH, GAP = 2, 1
-- 1.1.0-test.7: past the top of the arc, where it lands, the dashes are DOWN as long (and as far apart): where the arc
-- goes into the ground shows finer (a dash cut short there is easier to see than in long ones)
local DOWN = 0.5
-- test.15: only within DOWN_NEAR m of where the arc starts: farther, the finer dashes ran together into a line (from the
-- start, not the camera: by the camera, the dashes past that line slid as the camera moved)
local function finer(start, p)
  local DOWN_NEAR = 40
  return (p[1] - start[1]) ^ 2 + (p[2] - start[2]) ^ 2 + (p[3] - start[3]) ^ 2 < DOWN_NEAR * DOWN_NEAR
end
-- where a throw is let go: above the ball (or the C4) in my hand, standing, crouched or prone alike (during the hold,
-- where it was then, from my feet); else right of my chest, or under the camera
local function release_point(c, held, c4, from_feet)
  local ox, oy, oz
  if from_feet and me then
    ox, oy, oz = me[1] + from_feet[1], me[2] + from_feet[2], me[3] + from_feet[3]
  elseif held and chef.unit_alive(held) then
    ox, oy, oz = chef.unit_position(held)
  end
  if not ox then
    local fh = math.sqrt(c.fx * c.fx + c.fy * c.fy)
    local hx, hy = 0, 1
    if fh > 1e-6 then hx, hy = c.fx / fh, c.fy / fh end
    if me then
      ox, oy, oz = me[1] + hy * 0.3 + hx * 0.3, me[2] - hx * 0.3 + hy * 0.3, me[3] + 1.35
    else
      ox, oy, oz = c.x + hy * 0.3 + hx * 1.5, c.y - hx * 0.3 + hy * 1.5, c.z - 0.6
    end
  end
  return ox, oy, oz + (c4 and C4_RELEASE_UP or RELEASE_UP)
end

-- the throw's velocity as drawn: x, y, z
local function throw_velocity(c, c4)
  local fh = math.sqrt(c.fx * c.fx + c.fy * c.fy)
  local pitch = camera_pitch(c) + (c4 and C4_LIFT or LIFT)
  local hx, hy = 0, 1
  if fh > 1e-6 then hx, hy = c.fx / fh, c.fy / fh end
  local mx, my = my_move()
  local carried = math.max(-CARRY_MOST, math.min(CARRY_MOST, CARRY * (mx * hx + my * hy)))
  local speed = (c4 and C4_SPEED or SPEED) * speed_up(c4) + carried
  return hx * speed * math.cos(pitch), hy * speed * math.cos(pitch), speed * math.sin(pitch)
end

-- the throw's path, from where the ball or charge is let go, until DEEPEST under my feet or MOST_T: a list of points
local function path(c, c4, ox, oy, oz)
  local vx, vy, vz = throw_velocity(c, c4)
  local deepest = (feet_z or (c.z - 2)) - DEEPEST
  local function at(t)
    return ox + vx * t, oy + vy * t, oz + vz * t - 0.5 * GRAVITY * t * t
  end
  local pts = { { at(0) } }
  local t = 0
  while t < MOST_T do
    t = t + ((vz - GRAVITY * t < 0 and finer(pts[1], pts[#pts])) and STEP * DOWN or STEP)
    local x, y, z = at(t)
    pts[#pts + 1] = { x, y, z }
    if z < deepest then break end
  end
  return pts
end

-- the arc dashed (DASH segments drawn, GAP left out), each dash as lines side by side (offsets: px off its middle), across
-- the view. A dash is one straight line, not one per segment: half the engine's line calls (a GR-8's arc at the default
-- width: 785 a frame, now 395), and the path strays well under a centimetre from a line over DASH segments.
local function world_strip(c, pts, col, px_angle, offsets)
  local n = #pts
  local along, every = arc_solid and 1 or DASH, arc_solid and 1 or DASH + GAP
  for i = 1, n - 1, every do
    local p, q = pts[i], pts[math.min(i + along, n)]
    local dx, dy, dz = q[1] - p[1], q[2] - p[2], q[3] - p[3]
    local mx, my, mz = (p[1] + q[1]) / 2 - c.x, (p[2] + q[2]) / 2 - c.y, (p[3] + q[3]) / 2 - c.z
    local nx, ny, nz = dy * mz - dz * my, dz * mx - dx * mz, dx * my - dy * mx
    local nl = math.sqrt(nx * nx + ny * ny + nz * nz)
    if nl > 1e-9 then
      -- each end set off by its own distance (1.1.0-test.3: one offset from the middle made a segment going away
      -- from the camera, as a weapon's does, fan out into loose strands)
      local kp = math.sqrt((p[1] - c.x) ^ 2 + (p[2] - c.y) ^ 2 + (p[3] - c.z) ^ 2) * px_angle / nl
      local kq = math.sqrt((q[1] - c.x) ^ 2 + (q[2] - c.y) ^ 2 + (q[3] - c.z) ^ 2) * px_angle / nl
      for _, o in ipairs(offsets) do
        chef.line(p[1] + nx * kp * o, p[2] + ny * kp * o, p[3] + nz * kp * o,
                  q[1] + nx * kq * o, q[2] + ny * kq * o, q[3] + nz * kq * o, col)
      end
    end
  end
end

local drew = false

local function draw_points(c, pts)
  local _, sh = chef.screen()
  if now() >= scale_next and chef.setting then
    scale_next = now() + SCALE_EVERY
    local r = chef.setting('render_settings.render_resolution')
    local rh = type(r) == 'table' and tonumber(r[2])
    render_scale = (rh and rh > 0 and sh and sh > 0) and math.min(1, rh / sh) or 1
  end
  local px_angle = (tonumber(c.fov) or 0.96) / math.max(1, sh or 1080)
  local offsets = {}
  for i = 1, 2 * arc_width - 1 do offsets[i] = (i - arc_width) / 2 / render_scale end
  local col = COLORS[arc_color] or COLORS[1]
  world_strip(c, pts, chef.color(col[1], col[2], col[3], 255), px_angle, offsets)
  drew = true
end

local function draw_arc(c, c4, ox, oy, oz) draw_points(c, path(c, c4, ox, oy, oz)) end

-- a line object keeps what it was last given until it is reset, and the loader resets it only when a line is drawn:
-- after the arc, one empty line far below the map clears it
local function clear_arc()
  if not drew then return end
  drew = false
  chef.line(0, 0, -10000, 0, 0, -10000, chef.color(0, 0, 0, 0))
end

-- ------------------------------------------------------------------ weapons
-- While a weapon whose round falls is aimed, the round's path. Its flight, from Weapon Probe 0.1.0 (27 tracked rounds of
-- five weapons, WEAPON_ARCS_PLAN.md): the weapon's speed plus my velocity; gravity times the weapon's factor, and drag
-- a = -WEAPON_K * drag * caliber^2 / mass * |v| * v, one K for every weapon (fitted per weapon 4.6-4.8e-4; air's
-- 1/2 rho pi/4 in the wiki's units is 4.81e-4). Its start and direction: see weapon_aim.
-- The weapon in hand: while aiming, the one weapon unit near me that points the way the camera looks (held ones
-- 0.998 and more, worn ones 0.8 and less; hand poses don't tell, the CB-9 and the Ultimatum share one).
-- In first person: only with its option.
-- Dashed by distance as the stratagem arc is (a point every SEG m, farther apart far off: SEG_FAR of the distance from
-- the camera), not by flight time (a 100 m/s round's dashes were 6 m long).
local WEAPON_K, WEAPON_LIFT, WEAPON_FROM = 4.7e-4, math.rad(0.6), { 1.3, -0.18, -0.35 }
local WEAPON_STEP = 1 / 120      -- s per step of the flight
local MUZZLE, SEG, SEG_FAR, MOST_POINTS = 0.45, 0.66, 0.015, 800   -- MUZZLE is only the unavailable-node fallback now
local AIMING = { HELD_KEEP = 0.8, circle_on = true, circle_idle = false, first_person = false, stratagem_on = true, c4_on = true }
local SIDE_CARRY = 0.5
-- First person: a nearby camera at the weapon's sight; root distance is only a compatibility fallback. Actual hand
-- proximity can identify a held weapon despite a lagging barrel while prone; without the hand, retain HELD_ALONG.
local FIRST_PERSON = 0.9          -- compatibility fallback if the sight node cannot be read
local HELD_ALONG, HELD_NEAR = 0.95, 2.5
local held_miss = nil            -- why no weapon was found in hand, for the log
-- weapon unit kind -> { speed m/s, gravity factor, drag * caliber^2 / mass, lifetime s or false, name }. From the
-- Helldivers wiki's data (game 1.007.201); measured ones say so. Kinds named from filediver's hash list.
local WEAPONS = {
  ['02eecd0b1fa49630'] = { 100, 1, 38.4, false, 'GL-21 Grenade Launcher' },             -- measured
  ['fe3b29b2cfa63f9b'] = { 100, 1, 38.4, false, 'GL-52 De-Escalator' },                 -- measured (the GL-21's round)
  ['88c2d09ad85a7c9f'] = { 100, 1, 38.4, false, 'GL-28 Belt-Fed Grenade Launcher' },
  ['006e44327bb953fe'] = { 100, 1, 38.4, false, 'GL-15 Evictor' },          -- (the wiki: a pump-action launcher)
  ['52e4334e6a128caf'] = { 100, 1, 38.4, false, 'GP-31 Grenade Pistol' },
  ['9eb160830321bfd6'] = { 20, 1, 6.4, false, 'GP-20 Ultimatum' },                      -- measured
  ['e91f569c2ad8af01'] = { 100, 1, 0, false, 'P-34 Breacher' },   -- measured: 100 m/s, flies 7 s+ (wiki: 150, 1.7 s)
  ['f49227a0630a3f7f'] = { 100, 0.5, 2.25, false, 'CB-9 Exploding Crossbow' },           -- measured
  ['05d8d8c073b9d502'] = { 90, 3, 16, false, 'SG-8P Punisher Plasma' },
  ['26e40437ea275296'] = { 250, 1, 0.657, 1.5, 'RL-77 Airburst Rocket Launcher', node = 'muzzle' },
  ['9f80d67a12a7e40f'] = { 250, 1, 0.657, false, 'GR-8 Recoilless Rifle', node = 'muzzle' },
  ['80932fa0ed6901d3'] = { 200, 1, 0, false, 'EAT-17 Expendable Anti-Tank', node = 'muzzle' },
  ['b2b5e0d185605f9e'] = { 200, 1, 0, false, 'EAT-700 Expendable Napalm', node = 'muzzle' },
  ['7617642765ac38c7'] = { 50, 1, 6.4, false, 'EAT-411 Leveller', node = 'muzzle' },
  -- (its unit: plasma_blaster, test.11; its round isn't a unit, so only seen by eye: test.12's arc began below the
  -- muzzle, which sits farther along and higher than the unit's grip: a guess, to be seen in test.13)
  ['e8d5f49ad7780e54'] = { 250, 2, 0.4, 0.6, 'PLAS-45 Epoch', muzzle = { 0.8, 0.12 } },
  -- the One-Two's underbarrel launcher fires the GP-31's round; drawn only while its fire mode selects it (ub)
  ['a955c4ea6f6d4203'] = { 100, 1, 38.4, false, 'AR/GL-21 One-Two (its grenade launcher)', ub = true },
  -- The game gives these no crosshair in third person (the wiki; the two reticle mods on Nexus list these three), and they
  -- hardly drop: its aim circle where the round is going, no arc. The APW-1's kind is sure (HD2Runtime); filediver's
  -- sniper_rifle_duo (it has a backpack, as the Apex) and sniper_rifle_simo (a bolt-action) are taken to be the other two.
  ['89c5493e08ca4207'] = { 0, 0, 0, false, 'APW-1 Anti-Materiel Rifle', circle = true },
  ['b814eece17533bc4'] = { 0, 0, 0, false, 'AMW-20 Apex', circle = true },
  ['41f2def484634b59'] = { 0, 0, 0, false, 'R-40 Sightliner', circle = true },
}
local weapon_units = {}
for kind, name in ("@WEAPON_UNITS@"):gmatch('(%x+) (%S+)') do weapon_units[kind] = name end
local weapon_watch
do
  local kinds = {}
  for kind in pairs(weapon_units) do kinds[kind] = true end
  for kind in pairs(WEAPONS) do kinds[kind] = true end
  weapon_watch = chef.watch and chef.watch(kinds, 0.5)
end
local weapon_arcs = true         -- the option
local said_weapon = nil
local weapon_log_at = 0

-- the weapon in my hand, while aiming: its kind and unit, or nil when it isn't one of WEAPONS
local held = nil                 -- { kind, unit }: kept while aiming lasts
local function held_weapon(c)
  if not (weapon_watch and me) then return nil end
  local grip, hand = hand_pose(), right_hand()
  if grip == 0 or grip == 40 or grip == 41 or grip == 42 then
    held, held_miss = nil, grip == 0 and 'empty hand pose' or 'throwable hand pose'
    return nil
  end
  local function near(u)
    local x, y, z = chef.unit_position(u)
    if not x or (x - me[1]) ^ 2 + (y - me[2]) ^ 2 >= HELD_NEAR * HELD_NEAR then return false end
    -- Weapon roots are at the grip. Reject a slung/dropped/other player's weapon when the hand node is available.
    local d = hand and ((x - hand[1]) ^ 2 + (y - hand[2]) ^ 2 + (z - hand[3]) ^ 2)
    -- Camera alignment cannot establish possession: a slung launcher can align during a dive or high aim.
    -- Use the same hand/root tolerance already used for positive held-weapon and idle-circle identification.
    return not hand or d <= 0.35 * 0.35, d
  end
  local previous = held
  held, held_miss = nil, nil
  local best, best_a, ambiguous
  for _, it in ipairs(weapon_watch.items) do
    if chef.unit_alive(it.unit) then
      local nearby, hand_d = near(it.unit)
      if nearby then
        local fx, fy, fz = chef.unit_rotation(it.unit)
        local a = type(fx) == 'number' and fx * c.fx + fy * c.fy + fz * c.fz
        -- A prone weapon can point off the camera while tracking the game's aim circle. A root actually at my
        -- hand is stronger evidence than camera alignment; prefer the nearest such root to a slung weapon.
        local strong = hand_d and hand_d <= 0.35 * 0.35 and a and a >= 0
        local score = strong and (2 - hand_d) or a
        if score and (not best_a or score > best_a) then
          best, best_a, ambiguous = it, score, false
        elseif score and score == best_a and it.unit ~= best.unit then
          ambiguous = true
        end
      end
    end
  end
  local threshold = best and previous and best.unit == previous.unit and AIMING.HELD_KEEP or HELD_ALONG
  if best and not ambiguous and best_a >= threshold then
    if not WEAPONS[best.kind] then
      held_miss = 'unsupported weapon: ' .. tostring(weapon_units[best.kind])
      return nil
    end
    held = { kind = best.kind, unit = best.unit }
    return best.kind, best.unit
  end
  if best then
    local name = WEAPONS[best.kind] and WEAPONS[best.kind][5] or weapon_units[best.kind]
    held_miss = ambiguous and 'ambiguous weapon at hand' or string.format('%s points %.3f along the camera', name, best_a)
  end
  return nil
end

-- All 16 supported units have the named muzzle and a sight node in the installed build's joint list. Resolve names
-- through the loader, never hardcode asset indices. Cache per unit/world; a missing node retries after five seconds.
local weapon_nodes = (function()
  local cache, world = setmetatable({}, { __mode = 'k' }), nil
  return function(u, w)
    local wid, t = chef.world_id(), now()
    if wid ~= world then cache, world = setmetatable({}, { __mode = 'k' }), wid end
    local row = cache[u]
    if not row then row = { next = 0 }; cache[u] = row end
    if chef.unit_node and t >= row.next and (not row.muzzle or not row.sight) then
      row.next = t + GRIP_RETRY
      row.muzzle = row.muzzle or chef.unit_node(u, w.node or 'attach_muzzle')
      row.sight = row.sight or chef.unit_node(u, 'sight')
    end
    return row
  end
end)()

-- Actual animated muzzle, in any pose. Legacy offsets remain only for unavailable/invalid node reads.
local function muzzle_of(u, w)
  local x, y, z = chef.unit_position(u)
  if not x then return nil end
  local nodes = weapon_nodes(u, w)
  if nodes.muzzle then
    local mx, my, mz = chef.unit_position(u, nodes.muzzle)
    if mx and mx == mx and my == my and mz == mz
       and (mx - x) ^ 2 + (my - y) ^ 2 + (mz - z) ^ 2 <= 9 then
      if nodes.said ~= 'node' then
        nodes.said = 'node'
        log('weapon muzzle: %s (%s)', w[5], w.node or 'attach_muzzle')
      end
      return { mx, my, mz }
    end
  end
  if nodes.said ~= 'fallback' then
    nodes.said = 'fallback'
    log('weapon muzzle: %s (legacy fallback; node unavailable)', w[5])
  end
  local fx, fy, fz = chef.unit_rotation(u)
  if not (x and type(fx) == 'number') then return nil end
  local ahead, up = MUZZLE, 0
  if w.muzzle then ahead, up = w.muzzle[1], w.muzzle[2] end
  return { x + fx * ahead, y + fy * ahead, z + fz * ahead + up }
end

local function first_person(c, u, w)
  local x, y, z = chef.unit_position(u)
  if not x then return false end
  local near = (x - c.x) ^ 2 + (y - c.y) ^ 2 + (z - c.z) ^ 2 < FIRST_PERSON * FIRST_PERSON
  if not near then return false end
  local nodes = weapon_nodes(u, w)
  if nodes.sight then
    local sx, sy, sz = chef.unit_position(u, nodes.sight)
    if sx and (sx - x) ^ 2 + (sy - y) ^ 2 + (sz - z) ^ 2 <= 9 then
      -- A close prone third-person camera need not be at the weapon's eye/sight point. This geometric threshold
      -- still needs the targeted live first-/third-person check; fallback preserves older-loader behavior.
      return (sx - c.x) ^ 2 + (sy - c.y) ^ 2 + (sz - c.z) ^ 2 < 0.35 * 0.35
    end
  end
  return near
end

-- the round as it is fired: where it starts and its velocity (mx, my: my velocity on the ground; aim: { yaw, pitch }
-- in radians the round goes, or nil for the camera's; from: the muzzle, or nil for WEAPON_FROM off the camera)
local function launch(c, w, mx, my, aim, from)
  local fh = math.sqrt(c.fx * c.fx + c.fy * c.fy)
  local hx, hy = 0, 1
  if fh > 1e-6 then hx, hy = c.fx / fh, c.fy / fh end
  local ux, uy, uz = -c.fz * hx, -c.fz * hy, fh     -- up, across the view
  local f = WEAPON_FROM
  local px, py, pz = c.x + c.fx * f[1] + hy * f[2] + ux * f[3], c.y + c.fy * f[1] - hx * f[2] + uy * f[3],
                     c.z + c.fz * f[1] + uz * f[3]
  if from then px, py, pz = from[1], from[2], from[3] end
  local pitch = aim and aim[2] or camera_pitch(c) + WEAPON_LIFT
  if aim then hx, hy = math.cos(aim[1]), math.sin(aim[1]) end
  local along, across = mx * hx + my * hy, (mx * hy - my * hx) * SIDE_CARRY
  local s = w[1] * math.cos(pitch) + along
  return px, py, pz, hx * s + hy * across, hy * s - hx * across, w[1] * math.sin(pitch)
end

-- My helldiver's network object: my player's object says which it is. Looked for every LOOK s until found, BATCH of my
-- objects a frame (as host I own thousands), and again with a new helldiver or world. Read only.
AIMING.avatar = (function()
  local PLAYER, AVATAR, AVATAR_OF, LOOK, BATCH = 'un6y1d', 'vvhx8ga', 'u4d1h9a', 2, 200
  local unit, world, avatar, scan, next_look
  local function call(name, tag, ...) return chef.call_kind(name, 'aim avatar ' .. tag, ...) end
  local function is_a(gs, g, type_name)
    return call('GameSession.game_object_exists', 'exists', gs, g) == true
       and call('GameSession.game_object_is_type', 'type', gs, g, type_name) == true
  end
  return function(gs)
    local w = chef.world_id()
    if unit ~= me_unit or world ~= w then unit, world, avatar, scan, next_look = me_unit, w, nil, nil, 0 end
    if avatar then
      if is_a(gs, avatar, AVATAR) then return avatar end
      avatar = nil
    end
    local peer = call('Network.peer_id', 'peer')
    if not peer then return nil end
    if not scan then
      if now() < next_look then return nil end
      next_look = now() + LOOK
      local mine = call('GameSession.objects_owned_by', 'owned', gs, peer)
      if type(mine) ~= 'table' then return nil end
      scan = { at = 1 }
      for _, g in pairs(mine) do scan[#scan + 1] = g end
    end
    for i = scan.at, math.min(scan.at + BATCH - 1, #scan) do
      local g = scan[i]
      if is_a(gs, g, PLAYER) and call('GameSession.game_object_owner', 'owner', gs, g) == peer then
        local a = read_field(gs, g, PLAYER, AVATAR_OF, 'aim avatar field')
        if type(a) == 'number' and is_a(gs, a, AVATAR) then
          avatar, scan = a, nil
          log('aim: my helldiver is object %s', tostring(a))
          return a
        end
      end
    end
    scan.at = scan.at + BATCH
    if scan.at > #scan then scan = nil end
    return nil
  end
end)()

-- Where the round is going: the point my weapon's aim is on, as my helldiver's network field gives it to the others (the
-- field's id is the hash of a name we don't know; rm_qp0d hashes to it). test.c3, 12 tracked shots: at the frame a round
-- leaves (0.04-0.05 s after the click) the line from the muzzle to this point is within 0.05-0.49 degrees of its flight,
-- turning fast too, where the camera was 4.5 off. Nothing here is worked out per weapon, pose, distance or turn.
-- x4joxek is the other such field: the point on the camera's own line that the crosshair is on.
AIMING.field_point = (function()
  local checked = {}
  return function(field)
    local gs = chef.call_kind('Network.game_session', 'aim field')
    local avatar = gs and AIMING.avatar(gs)
    if not avatar then return nil end
    local v = read_field(gs, avatar, 'vvhx8ga', field, 'aim field ' .. field)
    local kind = type(v)
    if v == nil or kind == 'table' or kind == 'string' or kind == 'number' or kind == 'boolean' then return nil end
    if checked[field] ~= avatar then
      if chef.call_kind('Script.type_name', 'aim field', v) ~= 'Vector3' then return nil end
      checked[field] = avatar
    end
    local x, y, z = chef.call_kind('Vector3.to_elements', 'aim field', v)
    if type(x) == 'number' and type(y) == 'number' and type(z) == 'number' and x == x and y == y and z == z then
      return x, y, z
    end
    return nil
  end
end)()

-- If the field can't be read: the animation's target 'aim_constraint_target', about 100 m out and with the same turn lag
-- (test.c3: as good as the field far off, up to 4.6 degrees off it within 20 m, where it doesn't run through the muzzle).
-- Found once per helldiver and world, read once a frame. Nil while it can't be read.
AIMING.target = (function()
  local NAME, RETRY = 'aim_constraint_target', 5
  local unit, world, index, retry, checked
  local function call(name, ...) return chef.call_kind(name, 'aim target', ...) end
  return function()
    if not (me_unit and chef.unit_alive(me_unit)) then return nil end
    local w, t = chef.world_id(), now()
    if unit ~= me_unit or world ~= w then unit, world, index, retry, checked = me_unit, w, nil, 0, false end
    if not index then
      if t < retry then return nil end
      retry = t + RETRY
      if call('Unit.animation_has_constraint_target', me_unit, NAME) ~= true then return nil end
      local i = call('Unit.animation_find_constraint_target', me_unit, NAME)
      if type(i) ~= 'number' then return nil end
      index = i
      log('aim target: %s is target %d of my helldiver', NAME, i)
    end
    local m = call('Unit.animation_get_constraint_target', me_unit, index)
    if not m then return nil end
    if not checked then
      if call('Script.type_name', m) ~= 'Matrix4x4' then index, retry = nil, t + RETRY; return nil end
      checked = true
    end
    local at = call('Matrix4x4.translation', m)
    local x, y, z = nil, nil, nil
    if at then x, y, z = call('Vector3.to_elements', at) end
    if type(x) == 'number' and type(y) == 'number' and type(z) == 'number' and x == x and y == y and z == z then
      return x, y, z
    end
    return nil
  end
end)()

-- A point a round from the muzzle could be going for: far enough to give a direction, not behind the camera's view
-- (it can lag the camera a long way in a fast turn, and a stale value could lie anywhere).
function AIMING.usable(c, muzzle, nearest, farthest, x, y, z)
  if not x then return false end
  local dx, dy, dz = x - muzzle[1], y - muzzle[2], z - muzzle[3]
  local d = math.sqrt(dx * dx + dy * dy + dz * dz)
  return d >= nearest and d <= farthest and (dx * c.fx + dy * c.fy + dz * c.fz) / d > 0.3
end

-- The round leaves the muzzle for that point, in every pose. With neither read: for the point AIMING.TARGET m under the
-- crosshair (47 tracked rounds fly from the muzzle to a point on the camera's line whatever the barrel does).
-- In first person the same field, read ahead: it comes about AIM_LEAD s late (a round leaves on the frame after the click,
-- and the field agrees with it about 0.04 s after that: 5 tracked shots in which it was moving), which a sight on the screen
-- shows as soon as the view turns. test.c5 drew the field as it came and the arc trailed the sight; test.c6 drew the
-- camera's line and it ran ahead, for the sight swings behind the camera too. With no field: the camera's line, as far along
-- as x4joxek says.
AIMING.read_ahead = (function()
  local LEAD, SMOOTH, MOST = 0.04, 0.03, math.rad(25)
  local at, yaw, pitch, rate_y, rate_p
  local function wrap(a) return (a + math.pi) % (2 * math.pi) - math.pi end
  local function limit(a) return math.max(-MOST, math.min(MOST, a)) end
  return function(muzzle, x, y, z)
    local dx, dy, dz = x - muzzle[1], y - muzzle[2], z - muzzle[3]
    local ny, np = math.atan2(dy, dx), math.atan2(dz, math.sqrt(dx * dx + dy * dy))
    local t = now()
    local dt = at and t - at or 1
    if dt > 0.15 then
      rate_y, rate_p = 0, 0
    elseif dt > 0 then
      local k = 1 - math.exp(-dt / SMOOTH)
      rate_y = rate_y + (wrap(ny - yaw) / dt - rate_y) * k
      rate_p = rate_p + ((np - pitch) / dt - rate_p) * k
    end
    at, yaw, pitch = t, ny, np
    return ny + limit(rate_y * LEAD), np + limit(rate_p * LEAD)
  end
end)()

AIMING.TARGET = 100
local function weapon_aim(c, kind, u, muzzle, fp)
  if not muzzle then return nil, 'camera' end
  local hx, hy, hz = AIMING.field_point('rm_qp0d')
  local have = AIMING.usable(c, muzzle, 1.5, 2000, hx, hy, hz)
  if fp and have then
    local yaw, pitch = AIMING.read_ahead(muzzle, hx, hy, hz)
    return { yaw, pitch }, 'first-person'
  end
  local d, mode = AIMING.TARGET, 'crosshair'
  if fp then
    local ax, ay, az = AIMING.field_point('x4joxek')
    if ax then
      local along = (ax - c.x) * c.fx + (ay - c.y) * c.fy + (az - c.z) * c.fz
      if along >= 1.5 and along <= 2000 then d = along end
    end
  end
  local x, y, z = c.x + c.fx * d, c.y + c.fy * d, c.z + c.fz * d
  if have then
    x, y, z, mode = hx, hy, hz, 'weapon-hit'
  elseif not fp then
    local tx, ty, tz = AIMING.target()
    if AIMING.usable(c, muzzle, 20, 200, tx, ty, tz) then x, y, z, mode = tx, ty, tz, 'aim-target' end
  end
  AIMING.px, AIMING.py, AIMING.pz = x, y, z
  x, y, z = x - muzzle[1], y - muzzle[2], z - muzzle[3]
  return { math.atan2(y, x), math.atan2(z, math.sqrt(x * x + y * y)) }, mode
end

-- The aim circle for the rifles with no crosshair of their own, as the game draws it for the others: a white ring, half
-- see-through (screenshots at 1200 lines: 6.3 to 8.5 px from its centre, about half white over what is behind).
function AIMING.draw_circle()
  if not chef.ring then return end
  local sx, sy = chef.world_to_screen(AIMING.px, AIMING.py, AIMING.pz)
  if not sx then return end
  local _, h = chef.screen()
  chef.ring(sx, sy, h * 6.3 / 1200, h * 8.5 / 1200, chef.color(255, 255, 255, 128), (chef.TOP or 0) + 1100)
end

-- The game shows no crosshair while the hellpod comes down, seen from far off: the camera 28-37 m from my weapon (on foot
-- at most 6 m, seated about 7). No arc or circle then. Weapon arcs/circles also follow the loader mission flag;
-- older loaders could classify small missions as the ship, so keep this limitation explicit in the development notes.
function AIMING.my_view(c, muzzle)
  return not muzzle or (muzzle[1] - c.x) ^ 2 + (muzzle[2] - c.y) ^ 2 + (muzzle[3] - c.z) ^ 2 < 12 * 12
end
function AIMING.on_the_ship() return chef.in_mission ~= nil and chef.in_mission() == false end

-- Another mod's first-person camera (First Person Camera, Nexus 17827): the game goes on aiming from its own camera, so
-- the weapon's field holds, and x4joxek, on the real camera's line, lies off this one. Real cameras, held still, under
-- 100 m: within 0.21 m (test.c3, test.c5). So when off by CAMERA_OFF m for CAMERA_LONG frames: it has been moved.
AIMING.camera_moved = (function()
  local CAMERA_OFF, CAMERA_LONG = 0.35, 30
  local moved, count, fx, fy, fz, world = false, 0, nil, nil, nil, nil
  return function(c)
    if world ~= chef.world_id() then world, moved, count, fx = chef.world_id(), false, 0, nil end
    local still = fx and fx * c.fx + fy * c.fy + fz * c.fz > 0.99999
    fx, fy, fz = c.fx, c.fy, c.fz
    if not still then return moved end
    local hx, hy, hz = AIMING.field_point('x4joxek')
    if not hx then return moved end
    local dx, dy, dz = hx - c.x, hy - c.y, hz - c.z
    local along = dx * c.fx + dy * c.fy + dz * c.fz
    if along < 2 or along > 100 then return moved end
    local off = dx * dx + dy * dy + dz * dz - along * along > CAMERA_OFF * CAMERA_OFF
    count = math.max(0, math.min(CAMERA_LONG, count + (off and 1 or -1)))
    if (count >= CAMERA_LONG) ~= moved and (count >= CAMERA_LONG or count == 0) then
      moved = count >= CAMERA_LONG
      log('aim: the camera is %s', moved and "another mod's: the game's aim isn't along it" or 'the game\'s own')
    end
    return moved
  end
end)()

-- With its option (off by default) those rifles show their circle whenever they are in my hand: looked for five times a second, at the hand
-- (a weapon's root is at the grip), not with a throwable out. Not seated in a vehicle, unless aiming from it: the game's
-- crosshairs show only then.
AIMING.idle_circle = (function()
  local kind, unit, next_look = nil, nil, 0
  return function(c)
    if not (AIMING.circle_on and AIMING.circle_idle and weapon_watch and me) then return nil end
    local t = now()
    if t >= next_look then
      next_look, kind, unit = t + 0.2, nil, nil
      local grip, hand = hand_pose(), right_hand()
      if hand and grip ~= 40 and grip ~= 41 and grip ~= 42 then
        local best
        for _, it in ipairs(weapon_watch.items) do
          local w = WEAPONS[it.kind]
          if w and w.circle and not w.off and chef.unit_alive(it.unit) then
            local x, y, z = chef.unit_position(it.unit)
            local d = x and (x - hand[1]) ^ 2 + (y - hand[2]) ^ 2 + (z - hand[3]) ^ 2
            if d and d <= 0.35 * 0.35 and (not best or d < best) then best, kind, unit = d, it.kind, it.unit end
          end
        end
        if unit and in_vehicle() then kind, unit = nil, nil end
      end
    end
    if not (unit and chef.unit_alive(unit)) then return nil end
    local w = WEAPONS[kind]
    if first_person(c, unit, w) and not AIMING.camera_moved(c) then return nil end
    return w, muzzle_of(unit, w), unit, kind
  end
end)()

-- DEVELOPMENT_WEAPON_TRACE_BEGIN
-- Temporary test.6 direction evidence. Never changes the aim/calibration. At most 16 presses per load and three per weapon/context;
-- the existing loader watch scans only during each 0.35s sample window, never continuously while aiming.
local weapon_diagnostic = (function()
  local rounds = {
    ['02eecd0b1fa49630'] = 'a6cd8a90185b6567', ['fe3b29b2cfa63f9b'] = 'a6cd8a90185b6567',
    ['9eb160830321bfd6'] = 'b3bf071f477fc155', ['f49227a0630a3f7f'] = '8f063c5d3929316e',
    ['e91f569c2ad8af01'] = 'ccf18b6315a3d67f', ['26e40437ea275296'] = '36ab9a3dcae3d562',
  }
  local kinds = {}; for _, k in pairs(rounds) do kinds[k] = true end
  local watch = chef.watch and chef.watch(kinds, 0.05)
  if watch then watch.pause() end
  local previous, count, sample, budgets = false, 0, nil, {}
  local discovery, discovery_arms = nil, 0
  local history, history_unit, history_world = {}, nil, nil
  local function all_units()
    local units = chef.call('World.units', chef.world())
    return type(units) == 'table' and units or {}
  end
  -- test.c4: the values beside each other, to compare with the rounds: the animation's target and my helldiver's network
  -- fields af97ede7 (on the camera's line) and bdc1cb8a (where the arc goes). Read only, while aiming: four times a second,
  -- twenty while the camera turns, every frame around a click, and the frames before it.
  local aim_probe = (function()
    local FIELDS = { { 'hit', 'x4joxek' }, { 'weapon-hit', 'rm_qp0d' } }
    local state = { lines = 0, next = 0, after_click = 0, ring = {} }
    -- (only by the kind it says it is: test.c1 ended the game making numbers of a table)
    local function field_text(gs, avatar, f)
      local v = read_field(gs, avatar, 'vvhx8ga', f[2], 'aim probe ' .. f[1])
      local kind = type(v)
      if v == nil or kind == 'table' or kind == 'string' or kind == 'number' or kind == 'boolean' then return kind end
      if chef.call_kind('Script.type_name', 'aim probe type', v) ~= 'Vector3' then return 'other' end
      local x, y, z = chef.call_kind('Vector3.to_elements', 'aim probe vector', v)
      if type(x) ~= 'number' then return 'other' end
      return string.format('%.4f,%.4f,%.4f', x, y, z)
    end
    return function(c, muzzle, clicked, t)
      if state.world ~= chef.world_id() then state.world, state.ring = chef.world_id(), {} end
      local tx, ty, tz = AIMING.target()
      local target = tx and string.format('%.4f,%.4f,%.4f', tx, ty, tz) or 'none'
      local last = state.ring[#state.ring]
      local turning = last and last.fx * c.fx + last.fy * c.fy + last.fz * c.fz < 0.99996
      if clicked then
        state.after_click = 6
        for _, h in ipairs(state.ring) do
          log('aim pre t=%.6f dt=%.6f camera=%.4f,%.4f,%.4f forward=%.6f,%.6f,%.6f target=%s',
              t, h.t - t, h.x, h.y, h.z, h.fx, h.fy, h.fz, h.target)
        end
      end
      state.ring[#state.ring + 1] = { t = t, x = c.x, y = c.y, z = c.z, fx = c.fx, fy = c.fy, fz = c.fz, target = target }
      if #state.ring > 12 then table.remove(state.ring, 1) end
      if not (state.after_click > 0 or (t >= state.next and state.lines < 3000)) then return end
      local label = clicked and 'click' or (state.after_click > 0 and 'after' or (turning and 'turning' or 'aiming'))
      state.lines, state.next = state.lines + 1, t + (turning and 0.05 or 0.25)
      if state.after_click > 0 then state.after_click = state.after_click - 1 end
      local gs = chef.call_kind('Network.game_session', 'aim probe session')
      local avatar = gs and AIMING.avatar(gs)
      local bits = {}
      if avatar then
        for _, f in ipairs(FIELDS) do bits[#bits + 1] = f[1] .. '=' .. field_text(gs, avatar, f) end
      end
      log('aim quick t=%.6f %s camera=%.4f,%.4f,%.4f forward=%.6f,%.6f,%.6f muzzle=%.4f,%.4f,%.4f target=%s %s',
          t, label, c.x, c.y, c.z, c.fx, c.fy, c.fz, muzzle[1], muzzle[2], muzzle[3], target, table.concat(bits, ' '))
      local u = history_unit
      local fx, fy, fz
      if u and chef.unit_alive(u) then fx, fy, fz = chef.unit_rotation(u) end
      if type(fx) == 'number' then log('aim barrel t=%.6f %.6f,%.6f,%.6f', t, fx, fy, fz) end
    end
  end)()
  -- test.c5: aiming a weapon the mod doesn't know, what is at my hand, for its kind (the Apex's, the Sightliner's).
  local unknown_weapon = (function()
    local times, next_at = 0, 0
    return function(c, t)
      if not (aim_down and times < 12 and t >= next_at and me_unit) then return end
      local hand = right_hand()
      if not hand then return end
      times, next_at = times + 1, t + 3
      local bits = {}
      for _, unit in ipairs(all_units()) do
        local kind = chef.unit_kind(unit)
        if kind and kind ~= '46cab355bd8d4d37' and unit ~= me_unit and chef.unit_alive(unit) then
          local x, y, z = chef.unit_position(unit)
          if x and (x - hand[1]) ^ 2 + (y - hand[2]) ^ 2 + (z - hand[3]) ^ 2 < 0.36 then
            local fx, fy, fz = chef.unit_rotation(unit)
            if type(fx) == 'number' then
              bits[#bits + 1] = string.format('%s:%.3f', kind, fx * c.fx + fy * c.fy + fz * c.fz)
            end
          end
        end
      end
      log('aim unknown weapon t=%.3f at my hand (kind:along the camera) %s', t, table.concat(bits, ' '))
    end
  end)()
  local function vector(label, x, y, z)
    if type(x) == 'number' and type(y) == 'number' and type(z) == 'number' then
      log('weapon direction %d %s %.6f %.6f %.6f', count, label, x, y, z)
    end
  end
  -- test.11: forward-only weapon rotation cannot reveal torso roll. Observe named avatar aim/body nodes
  -- only at the already bounded shot snapshots. No per-frame reads, world scan, calibration or aim changes.
  local body = {}
  local body_names = { 'weapon_aim', 'aim_weapon', 'boss_aim', 'hips', 'chest', 'l_clavicle', 'r_clavicle' }
  local function body_snapshot(t)
    if not (me_unit and chef.unit_alive(me_unit) and chef.unit_node) then return end
    local world = chef.world_id()
    if body.unit ~= me_unit or body.world ~= world then body = { unit = me_unit, world = world, next = 0 } end
    if t >= body.next then
      body.next = t + GRIP_RETRY
      for _, name in ipairs(body_names) do
        if not body[name] then
          local node = chef.unit_node(me_unit, name)
          if type(node) == 'number' then body[name] = node end
        end
      end
    end
    vector('avatar-root-forward', chef.unit_rotation(me_unit))
    for _, name in ipairs(body_names) do
      local node = body[name]
      if node then
        vector('avatar-' .. name .. '-position', chef.unit_position(me_unit, node))
        vector('avatar-' .. name .. '-forward', chef.unit_rotation(me_unit, node))
      else
        log('weapon direction %d avatar-%s unavailable', count, name)
      end
    end
  end
  local function finish_sample()
    for i, tr in ipairs(sample.tracks) do
      local elapsed = (tr.last_t or tr.first_t) - tr.first_t
      local speed = elapsed > 0 and tr.distance / elapsed or 0
      local plausible = tr.n >= 3 and elapsed >= 0.035 and speed >= sample.speed * 0.5 and speed <= sample.speed * 1.5
      log('weapon direction %d candidate-summary track=%d kind=%s samples=%d mean-speed=%.3f plausible=%s; identity unverified',
          count, i, tr.kind, tr.n, speed, tostring(plausible))
    end
    log('weapon direction %d sample-end candidates=%d discovery-scans=%d', count, #sample.tracks, sample.scans or 0)
    if watch then watch.pause() end
    sample = nil
  end
  local function candidate(unit, kind, t)
    if sample.seen[unit] then return end
    sample.seen[unit] = true
    if not (kind and kind ~= '46cab355bd8d4d37' and chef.unit_alive(unit)) then return end
    local x, y, z = chef.unit_position(unit)
    local o = sample.origin
    if not (x and x == x and y == y and z == z) then return end
    if (x-o[1])^2+(y-o[2])^2+(z-o[3])^2 >= 400 or #sample.tracks >= (sample.discover and 12 or 3) then return end
    sample.tracks[#sample.tracks+1] = { unit=unit, kind=kind, first_t=t, n=0, distance=0 }
    log('weapon direction %d candidate %d kind=%s; association unverified', count, #sample.tracks, kind)
  end
  return {
    update = function(c, w, muzzle, aim, u, kind, aim_mode)
      local down, t = chef.mouse_down('left') == true, now()
      if w and muzzle then aim_probe(c, muzzle, down and not previous, t)
      elseif not w then unknown_weapon(c, t) end
      if history_unit ~= u or history_world ~= chef.world_id() then history = {} end
      history_unit, history_world = u, chef.world_id()
      -- Restore the old test.3-6 new-unit path for GR-8, without assuming a projectile hash.
      -- One baseline per aiming/equipped unit (six arms/load), then at most six scans per shot; test builds only.
      if not (kind == '9f80d67a12a7e40f' or (w and w.circle)) then discovery = nil
      elseif not discovery or discovery.unit ~= u or discovery.world ~= chef.world_id() then
        if discovery_arms < 6 and count < 16 then
          discovery_arms = discovery_arms + 1
          local before = {} -- retain baseline handles until aim/window ends; do not let GC invent new units
          for _, unit in ipairs(all_units()) do before[unit] = true end
          discovery = { unit=u, world=chef.world_id(), before=before }
          log('GR-8 discovery armed %d; new-unit identity remains unverified', discovery_arms)
        end
      end
      -- (only so that the shots of one stance don't use up the records of the others)
      local stance, key
      if down and not previous and w and count < 16 then
        local height = select(3, chef.unit_position(u)) - (feet_z or c.z)
        stance = height < 0.5 and 'prone' or (height < 1 and 'crouch' or 'standing')
        key = kind .. '/' .. stance
        if in_vehicle() then key = key .. '/vehicle' end
        if first_person(c, u, w) then key = key .. '/first-person' end
      end
      local before = history[#history]
      if key and before and before[13] * c.fx + before[14] * c.fy + before[15] * c.fz < 0.99996 then
        key = key .. '/turning'
      end
      if down and not previous and w and muzzle and count < 16 and (budgets[key] or 0) < 3 then
        if sample then finish_sample() end
        budgets[key] = (budgets[key] or 0) + 1
        count = count + 1
        local mx, my = my_move()
        log('weapon direction %d shot t=%.6f world=%s kind=%s hand=%s root-height=%.4f',
            count, t, tostring(chef.world_id()), kind, tostring(hand_pose()),
            select(3, chef.unit_position(u)) - (feet_z or c.z))
        vector('camera-position', c.x, c.y, c.z)
        vector('camera-forward', c.fx, c.fy, c.fz)
        vector('root-position', chef.unit_position(u))
        vector('root-forward', chef.unit_rotation(u))
        local nodes = weapon_nodes(u, w)
        if nodes.muzzle then vector('muzzle-forward', chef.unit_rotation(u, nodes.muzzle)) end
        vector('muzzle-position', muzzle[1], muzzle[2], muzzle[3])
        local x, y, z, vx, vy, vz = launch(c, w, mx, my, aim, muzzle)
        vector('predicted-velocity', vx, vy, vz)
        vector('player-velocity', mx, my, 0)
        body_snapshot(t)
        log('weapon direction %d evidence-stance=%s; geometric classification only', count, stance)
        -- A click and the first visible round are different engine frames. Retain recent pre-click weapon
        -- poses to test latency/recoil, never fit a correction from a later animated/recoiling weapon pose.
        for _, h in ipairs(history) do
          if h.t < t and t-h.t <= 0.25 then
            log('weapon direction %d pre-shot dt=%.6f muzzle=%.6f %.6f %.6f root=%.6f %.6f %.6f'
                .. ' forward=%.6f %.6f %.6f camera=%.6f %.6f %.6f camera-forward=%.6f %.6f %.6f',
                count,h.t-t,h[1],h[2],h[3],h[4],h[5],h[6],h[7],h[8],h[9],h[10],h[11],h[12],h[13],h[14],h[15])
          end
        end
        log('weapon direction %d direction-mode=%s first-person=%s', count, aim_mode or 'unavailable',
            tostring(first_person(c, u, w)))
        local seen = setmetatable({}, { __mode = 'k' })
        if watch then for _, it in ipairs(watch.items) do seen[it.unit] = true end end
        local discover = (kind == '9f80d67a12a7e40f' or w.circle) and discovery
        sample = { at=t, world=chef.world_id(), kind=rounds[kind], origin=muzzle, speed=w[1],
                   seen=seen, tracks={}, next=0, scans=0, next_scan=0, weapon=u, row=w,
                   discover=discover and true or false, before=discover and discover.before }
        if sample.kind and watch then watch.resume(); watch.refresh()
        elseif sample.discover then if watch then watch.pause() end
        else sample = nil; if watch then watch.pause() end end
      end
      previous = down
      if w and muzzle and count < 16 then
        local x,y,z = chef.unit_position(u)
        local fx,fy,fz = chef.unit_rotation(u)
        if x and type(fx)=='number' then
          history[#history+1] = {muzzle[1],muzzle[2],muzzle[3],x,y,z,fx,fy,fz,c.x,c.y,c.z,c.fx,c.fy,c.fz,t=t}
          if #history > 8 then table.remove(history, 1) end
        end
      else history = {} end
      if not sample then return end
      if t-sample.at > 0.35 or sample.world ~= chef.world_id() then finish_sample(); return end
      if sample.discover and t-sample.at <= 0.14 and sample.scans < 6 and t >= sample.next_scan then
        sample.scans, sample.next_scan = sample.scans+1, t+0.02
        local examined = 0
        for _, unit in ipairs(all_units()) do
          if not sample.before[unit] then
            sample.before[unit] = true
            examined = examined+1
            if chef.unit_alive(unit) then candidate(unit, chef.unit_kind(unit), t) end
            if examined >= 64 then break end
          end
        end
      elseif sample.kind and watch then
        for _, it in ipairs(watch.items) do
          if it.kind == sample.kind then candidate(it.unit, it.kind, t) end
        end
      end
      if t >= sample.next then
        sample.next = t+0.02
        -- Sample the firing weapon once per tick, even if another weapon is now selected.
        if sample.weapon and chef.unit_alive(sample.weapon) then
          local live = muzzle_of(sample.weapon, sample.row)
          local x,y,z = chef.unit_position(sample.weapon)
          local fx,fy,fz = chef.unit_rotation(sample.weapon)
          if live and x and type(fx)=='number' then
            log('weapon direction %d sync dt=%.6f muzzle=%.6f %.6f %.6f root=%.6f %.6f %.6f'
                .. ' forward=%.6f %.6f %.6f camera=%.6f %.6f %.6f camera-forward=%.6f %.6f %.6f',
                count,t-sample.at,live[1],live[2],live[3],x,y,z,fx,fy,fz,c.x,c.y,c.z,c.fx,c.fy,c.fz)
          end
        end
        for i, tr in ipairs(sample.tracks) do
          if chef.unit_alive(tr.unit) then
            local x,y,z = chef.unit_position(tr.unit)
            if x and x==x and y==y and z==z then
              if tr.last then tr.distance = tr.distance+math.sqrt((x-tr.last[1])^2+(y-tr.last[2])^2+(z-tr.last[3])^2) end
              tr.last, tr.last_t, tr.n = {x,y,z}, t, tr.n+1
              log('weapon direction %d track=%d dt=%.6f position=%.6f %.6f %.6f',count,i,t-sample.at,x,y,z)
            end
          end
        end
      end
    end,
    stop = function() if watch then watch.stop() end end,
  }
end)()
-- DEVELOPMENT_WEAPON_TRACE_END

-- one WEAPON_STEP of a round's flight
local function fly(w, px, py, pz, vx, vy, vz)
  local d = WEAPON_K * w[3] * math.sqrt(vx * vx + vy * vy + vz * vz) * WEAPON_STEP
  vx, vy, vz = vx - d * vx, vy - d * vy, vz - GRAVITY * w[2] * WEAPON_STEP - d * vz
  return px + vx * WEAPON_STEP, py + vy * WEAPON_STEP, pz + vz * WEAPON_STEP, vx, vy, vz
end

-- the round's path from the muzzle, until its lifetime, MOST_T or DEEPEST under my feet: points SEG m apart (farther
-- far off). test.4: from the muzzle itself; test.2-3 cut the camera's line where it passed the muzzle's distance, which
-- hung in the air ahead of the weapon while walking sideways (the weapon swinging off that line)
local function weapon_path(c, w, muzzle, aim)
  local mx, my = my_move()
  local px, py, pz, vx, vy, vz = launch(c, w, mx, my, aim, muzzle)
  local last = math.min(w[4] or MOST_T, MOST_T)
  local deepest = (feet_z or (c.z - 2)) - DEEPEST
  local pts, to_go = {}, 0       -- to_go: m of flight until the next point
  local function put(x, y, z)
    pts[#pts + 1] = { x, y, z }
    to_go = math.max(SEG * (vz < 0 and DOWN or 1), SEG_FAR * math.sqrt((x - c.x) ^ 2 + (y - c.y) ^ 2 + (z - c.z) ^ 2))
  end
  local t = 0
  while t < last and #pts < MOST_POINTS do
    local qx, qy, qz
    qx, qy, qz, vx, vy, vz = fly(w, px, py, pz, vx, vy, vz)
    t = t + WEAPON_STEP
    if #pts == 0 then put(px, py, pz) end
    local len = math.sqrt((qx - px) ^ 2 + (qy - py) ^ 2 + (qz - pz) ^ 2)
    local s = 0
    while len - s >= to_go and #pts < MOST_POINTS do
      s = s + to_go
      local f = s / len
      put(px + (qx - px) * f, py + (qy - py) * f, pz + (qz - pz) * f)
    end
    to_go = to_go - (len - s)
    px, py, pz = qx, qy, qz
    if pz < deepest then break end
  end
  pts[#pts + 1] = { px, py, pz }
  return pts
end

-- test.8: is the underbarrel launcher selected? As NarrowHUD tells it: my weapons' network objects, their fire mode
-- field (if5_pz) with the 8 bit set selects the underbarrel. Which of my objects are weapons is found by trying each
-- against the weapon types that declare that field (WEAPON_TYPES, from NarrowHUD's data), UB_BUDGET tries a frame (as
-- host I own every soldier's objects: thousands); a field is read only from an object just found to be of such a type
-- (reading one a type doesn't declare can end the game). Only while the One-Two is in hand; my objects looked for again
-- every UB_LOOK s.
local underbarrel_on = (function()
  local TYPES, FIRE_MODE, UB_BUDGET, UB_LOOK = {}, 'if5_pz', 300, 2
  for name in ("@WEAPON_TYPES@"):gmatch('%S+') do TYPES[#TYPES + 1] = name end
  local session, tried, weapons, next_look = nil, {}, {}, 0
  local function call(name, tag, ...) return chef.call_kind(name, 'ub ' .. tag, ...) end
  return function()
    local gs = call('Network.game_session', 'session')
    if not gs then return false end
    -- (by the world: the session comes back as a new value each call, and test.9 started over every frame, 19,000
    -- "my object is weapon type" lines in a mission)
    if chef.world_id() ~= session then session, tried, weapons = chef.world_id(), {}, {} end
    if now() >= next_look then
      next_look = now() + UB_LOOK
      local peer = call('Network.peer_id', 'peer')
      local mine = peer and call('GameSession.objects_owned_by', 'owned', gs, peer)
      if type(mine) == 'table' then for _, g in pairs(mine) do if tried[g] == nil then tried[g] = 1 end end end
    end
    local budget = UB_BUDGET
    for g, i in pairs(tried) do
      if budget <= 0 then break end
      if type(i) == 'number' then
        if i == 1 and call('GameSession.game_object_exists', 'exists', gs, g) ~= true then i = #TYPES + 1 end
        while budget > 0 and i <= #TYPES do
          budget = budget - 1
          if call('GameSession.game_object_is_type', 'type', gs, g, TYPES[i]) == true then
            weapons[g] = TYPES[i]
            log('one-two: my object %s is weapon type %s', tostring(g), TYPES[i])
            break
          end
          i = i + 1
        end
        -- (test.8-9 wrote this as "(...) and false or i", which is always i: found again every frame)
        if weapons[g] or i > #TYPES then tried[g] = false else tried[g] = i end
      end
    end
    local on = false
    for g, name in pairs(weapons) do
      if call('GameSession.game_object_exists', 'exists', gs, g) == true
         and call('GameSession.game_object_is_type', 'type', gs, g, name) == true then
        local fm = read_field(gs, g, name, FIRE_MODE, 'ub fire mode')
        if type(fm) == 'number' and math.floor(fm / 8) % 2 == 1 then on = true end
      else
        weapons[g], tried[g] = nil, nil
      end
    end
    return on
  end
end)()

-- 1.1.0: grenades. The grenade in my hand is a unit of its own kind (test.13 on), so it is told by its kind, from the
-- game's throwables (THROWABLES, filediver's names): one within GRENADE_HAND m across and GRENADE_LOW to GRENADE_HIGH
-- m above my feet. While one is in my hand and G (the game keeps it in hand until G is let go, "cooking"), left (cooking
-- one drawn with its key) or right (aiming it) is held, its arc, as its kind is thrown: from where its throws start
-- (from my feet, along and across my heading), turned its kind's yaw from the camera's heading, its kind's lift over the
-- camera, at its kind's speed (my walk along the aim added, test.15, and the throw-range perks), slowed by its kind's
-- DRAG (a = -drag |v| v). No grenade in hand: no arc (test.17 drew one from the air when G had none to throw). Guided
-- kinds: no arc.
-- Each kind's throw is learned from its flights, kept across launches (chef.save_table): the grenade that leaves my hand
-- (that unit, followed) is measured over its free flight, from the first step after it leaves the hand at GRENADE_FAST
-- m/s or more and steady (within GRENADE_STEADY of the next: the frames it jumps from the hand to its path run 25-35
-- m/s), for GRENADE_FIT s or until it lands (a step at less than half the one before): least squares, falling at
-- GRAVITY (and DRAG). Its start: that path back at the frame it left my hand, from my feet then. Standing and walking
-- (WALK m/s along the aim or more: the game's own deadzone for a thrower's velocity, "thrower_velocity_deadzone", is 1)
-- lifts apart (test.15: Gigas 3 degrees standing, 6-16 walking). Each value is the median of its last GRENADE_KEEP
-- measurements (with the measured ones to start), so one odd throw doesn't move it. Not measured yet: GRENADE_SPEED,
-- GRENADE_LIFT, no yaw, from the grenade in hand RELEASE_UP above it and GRENADE_RIGHT across.
-- test.19: drag is no longer learned (test.18's, from the speed across at a flight's start and end, ran 0.0001-0.35:
-- landings and bounces in it) but fixed, from whole flights; the start and yaw are (test.18: a Melta mine is thrown from
-- 0.8 m up, 0.5 m right of the hand, an Arc grenade 0.3 m right of my feet: the arc from the hand was off).
-- Keys rebound in the game aren't followed.
-- (lift: the game's "throw_angle_offset" is 5 degrees, in the Helldiver's AvatarComponent data dumped in
-- github.com/shalzuth/HelldiversData; a grenade's speed and drag aren't in that data)
local grenade = (function()
  local GRENADE_SPEED, GRENADE_LIFT, WALK = 21, 5, 1
  -- (GRENADE_LOW 0.2: a Melta mine is held low, and 0.6 until test.20 took it for in hand only now and then)
  local GRENADE_HAND, GRENADE_LOW, GRENADE_HIGH = 1.0, 0.2, 2.4
  local GRENADE_FAST, GRENADE_STEADY, GRENADE_FIT, GRENADE_FLY, GRENADE_KEEP = 5, 0.15, 0.65, 2.5, 9
  local GRENADE_SOON, GRENADE_REACH, GRENADE_OFF, GRENADE_SKIP = 0.2, 3, 0.15, 1.5
  local SAVE = 'grenade_throws6'  -- (test.12-19's files are not read: learned the wrong things)
  -- drag by kind, from whole flights (test.16: thermite 22 to 18 m/s across over 2 s, Giga 18.7 to 17 over 1.4 s;
  -- test.17: Arc, Melta and Impact kept their speed)
  local DRAG = { ['c5c05fcb5747c799'] = 0.0053, ['46333fc9e3d4bd34'] = 0.004 }
  -- the game's throwables (content/fac_helldivers/equipment/throwables/*), not their parts (a frag's spoon, caltrops'
  -- effect and the caltrops themselves)
  local THROWABLES = {}
  for kind in ([[6002622114037024 db922a7afc42894b 46333fc9e3d4bd34 8e325c933e55bf62 2968deba6d6c2f09 075b19b068fb1045
                 ee89cc10d80b6afb 14368dc8784220b0 1ff81c46cc79fd34 1b9ac59697006337 0080869506299773 4ce9eab785a79b7b
                 0416984f4922757b 693028644d27ffef 6b11fc757618c57e 7686544f539bb9b7 dab81b0d80b511c7 04653ab33f3ffb44
                 eb725c39fc38b87c e49a5ae078aad407 a20683199dfc19e8 ee4c107b941ab7f4 5c14f27759dd3be0 2d398d1ec35e0838
                 5de8fd02a05b4b0a c5c05fcb5747c799 3fa94f58f596bc0b 032489cf1d439bba f7b35a9c5ae340b6
                 03f31caf3a7d8f4e]]):gmatch('%x+') do THROWABLES[kind] = true end
  -- guided ones: no arc (they steer themselves once thrown); nothing learned
  local GUIDED = { ['2d398d1ec35e0838'] = true,       -- throwables/self_destruct_drone (G-50 Seeker)
                   ['8e325c933e55bf62'] = true }      -- throwables/at_self_destruct_drone (G-60 Anti-Tank Seeker)
  local FIELDS = { 'speed', 'lift', 'walk', 'yaw', 'ahead', 'right', 'up',
                   'offset_ahead', 'offset_right', 'offset_up' }
  -- Uses code / research from HD2Runtime by SkyeShade. Native rows distinguish the launch curves without needing
  -- the player to own/throw every kind. The caller's baseline strength is transferred from our measured 22.4m/s
  -- standard grenade, not mistaken for a documented native constant. Existing per-kind measurements still win.
  local PROFILES = "@GRENADE_PROFILES@"
  local REF_STRENGTH = (22.4 * 22.4 / 18 - 0.1) / (20 - 0.1)
  local function base_speed(kind)
    local p = PROFILES[kind]
    if not p then return GRENADE_SPEED end
    if p.measured then return p.measured end
    return p[3] > 0 and p[3] or math.sqrt(18 * math.max(0, p[1] + (p[2] - p[1]) * REF_STRENGTH))
  end
  local function motion_term(kind, along)
    local p = PROFILES[kind]
    if not (p and p[2]) then return nil end
    if p[3] > 0 then return 0 end
    -- ThrowableComponent's deadzone is 1m/s (decoded game data); forward/backward adjust strength, not m/s.
    local delta = along > WALK and p[4] or (along < -WALK and -p[5] or 0)
    return 18 * (p[2] - p[1]) * delta
  end
  local function moved_speed(kind, base, along, bonus)
    local term = motion_term(kind, along)
    local s = base * bonus
    return term and math.sqrt(math.max(0, s * s + term)) or math.max(0, s + along)
  end
  -- kind -> { field = { the last measurements } }, from testing to start (speeds and lifts as test.16-18 measured
  -- them; starts and yaws from test.18 where it had them)
  local known = {
    ['c5c05fcb5747c799'] = { speed = { 22.6, 23.3, 23.5 }, lift = { 7.0, 6.5, 5.4 }, walk = { 7.6, 6.6 } },  -- Thermite
    ['46333fc9e3d4bd34'] = { speed = { 17.0, 17.7, 17.6 }, lift = { 4.3, 6.4, 6.9 }, walk = { 4.1, 4.8 } },  -- G-48 Giga
    ['db922a7afc42894b'] = { speed = { 22.3, 22.5, 22.2 }, lift = { 3.2, 3.2, 3.4 }, walk = { 4.5, 4.6 },  -- G-31 Arc
                             yaw = { 0 }, ahead = { 0.1 }, right = { 0.3 }, up = { 1.5 } },
    ['ee4c107b941ab7f4'] = { speed = { 10.5, 10.6, 10.9 }, lift = { 4.5, 4.6 }, walk = { 3.8, 4.3 },  -- G/40-K Melta mine
                             yaw = { 0 } },
    ['7686544f539bb9b7'] = { speed = { 22.4 }, lift = { 4.2 } },                                     -- G-16 Impact
    ['5c14f27759dd3be0'] = { speed = { 22.2, 22.2, 22.3 }, lift = { 4.0, 3.9, 3.5 }, walk = { 4.2, 5.0 },  -- molotov
                             yaw = { 0 }, ahead = { 0.03, 0.09, 0.3 }, right = { 0.29, 0.31, 0.38 },
                             up = { 2.2, 2.24, 2.07 } },
  }
  -- Safety bounds, not fitted throw parameters. A backwards flight must not teach a forward aim (the old save
  -- accepted an Impact at -168 degrees). Keep legitimate kinds free to learn different speeds/lifts; selection and
  -- release timing need their own validation too. The 1000 m/s ceiling only guards numeric blow-ups, not game balance.
  local function valid_value(field, x)
    if type(x) ~= 'number' or x ~= x or x == math.huge or x == -math.huge then return false end
    if field == 'speed' then return x > 0 and x <= 1000 end
    if field == 'yaw' then return math.abs(x) < 90 end
    if field == 'lift' or field == 'walk' then return math.abs(x) <= 90 end
    if field == 'up' then return x >= 0 and x <= GRENADE_REACH end
    return math.abs(x) <= GRENADE_REACH
  end
  -- Old saves have separate arrays with no sample ids. If any field is invalid, restoring that whole kind is safer
  -- than combining unpaired remnants of a bad throw. Other kinds retain their valid calibration.
  local function checked_row(v)
    if type(v) ~= 'table' then return nil end
    local k = {}
    for _, field in ipairs(FIELDS) do
      local list, out, count = v[field], {}, 0
      if list ~= nil then
        if type(list) ~= 'table' then return nil end
        for i, x in pairs(list) do
          if type(i) ~= 'number' or i < 1 or i % 1 ~= 0 or not valid_value(field, x) then return nil end
          count = count + 1
        end
        if count ~= #list then return nil end        -- sparse arrays must not hide an invalid tail
        for i = math.max(1, count - GRENADE_KEEP + 1), count do out[#out + 1] = list[i] end
      end
      k[field] = out
    end
    if #k.speed == 0 then return nil end
    if #k.ahead ~= #k.right or #k.ahead ~= #k.up then return nil end
    if #k.offset_ahead ~= #k.offset_right or #k.offset_ahead ~= #k.offset_up then return nil end
    for i, a in ipairs(k.ahead) do
      if a * a + k.right[i] * k.right[i] > GRENADE_REACH * GRENADE_REACH then return nil end
    end
    k.fit_revision = v.fit_revision == 2 and 2 or nil
    return k
  end
  local can_save = true
  local fit_backups = {}                   -- old angle/origin calibration retained before changing reference frame
  local function persist()
    if can_save and chef.save_table then
      local ok, why = chef.save_table(SAVE, { known = known, fit_backups = fit_backups })
      if not ok then log('grenade calibration: save failed (%s)', tostring(why)) end
    end
  end
  do
    local saved, load_error
    if chef.load_table then saved, load_error = chef.load_table(SAVE) end
    if saved == nil and load_error and load_error ~= 'none saved' then
      -- The loader cannot give us the original bytes of an unreadable file to back up. Preserve it on disk.
      can_save = false
      log('grenade calibration: load failed (%s); original not overwritten', tostring(load_error))
    end
    local repair = saved ~= nil and (type(saved) ~= 'table' or type(saved.known) ~= 'table')
    if type(saved) == 'table' and type(saved.known) == 'table' then
      if type(saved.fit_backups) == 'table' then fit_backups = saved.fit_backups end
      for kind, v in pairs(saved.known) do
        if THROWABLES[kind] and not GUIDED[kind] then
          local k = checked_row(v)
          if k then
            local seed = known[kind] or {}
            for _, field in ipairs(FIELDS) do if #k[field] == 0 then k[field] = seed[field] or {} end end
            known[kind] = k
          else
            repair = true
            log('grenade calibration: invalid saved kind %s; using its defaults', kind)
          end
        end
      end
    end
    if repair then
      -- Back up BEFORE any write to the original name. An existing backup is retained across launches. If backup
      -- fails (disk full, unavailable API), use safe values in memory and leave the original file alone this launch.
      local backup = SAVE .. '_before_validation1'
      local old = chef.load_table and chef.load_table(backup)
      can_save = type(old) == 'table' and old.original ~= nil
      if not can_save and chef.save_table then can_save = chef.save_table(backup, { original = saved }) == true end
      if can_save then
        log('grenade calibration: original preserved as %s; saving repaired values', backup)
        persist()
      else
        log('grenade calibration: backup failed; repaired values stay in memory, original not overwritten')
      end
    end
  end
  local watch = chef.watch and chef.watch(THROWABLES, 0.2)

  local function median(l)
    if not l or #l == 0 then return nil end
    local s = {}
    for i, x in ipairs(l) do s[i] = x end
    table.sort(s)
    local m = math.floor((#s + 1) / 2)
    return #s % 2 == 1 and s[m] or (s[m] + s[m + 1]) / 2
  end

  -- Calibrations change only at load/learn, not at render frequency. Sort at most nine samples once per change.
  local cached = {}
  local function values(kind)
    local k = cached[kind]
    if not k then
      k = {}
      for _, field in ipairs(FIELDS) do k[field] = median((known[kind] or {})[field]) end
      cached[kind] = k
    end
    return k
  end

  -- the grenade in my hand: its unit and kind, or nil
  local function close_to_hand(u, hand, x, y, z)
    if not x then x, y, z = chef.unit_position(u) end
    if not x then return false end
    if hand then
      return (x - hand[1]) ^ 2 + (y - hand[2]) ^ 2 + (z - hand[3]) ^ 2 <= 0.8 * 0.8
    end
    -- Compatibility fallback when the loader/model cannot expose the hand node. Pose still gates this below.
    local d, up = (x - me[1]) ^ 2 + (y - me[2]) ^ 2, z - me[3]
    return d < GRENADE_HAND * GRENADE_HAND and up >= GRENADE_LOW and up <= GRENADE_HIGH
  end
  local function in_hand(skip, hand, grip)
    if not (watch and me) then return nil end
    if grip ~= nil and grip ~= 40 and grip ~= 41 and grip ~= 42 then return nil end
    local best, kind, bd
    for _, it in ipairs(watch.items) do
      if chef.unit_alive(it.unit) and not skip[it.unit] then
        local x, y, z = chef.unit_position(it.unit)
        if x and close_to_hand(it.unit, hand, x, y, z) then
          local h = hand or me
          local d = (x - h[1]) ^ 2 + (y - h[2]) ^ 2 + (z - h[3]) ^ 2
          if not bd or d < bd then
            best, kind, bd = it.unit, it.kind, d
          end
        end
      end
    end
    return best, kind
  end

  local preview = nil                    -- immutable launch state of the most recently displayed grenade arc
  -- the arc, as path() draws a stratagem ball's, with drag
  local function arc(c, u, kind, anchor)
    if GUIDED[kind] then return nil end
    local fh = math.sqrt(c.fx * c.fx + c.fy * c.fy)
    local hx, hy = 0, 1
    if fh > 1e-6 then hx, hy = c.fx / fh, c.fy / fh end
    local k = values(kind)
    if not anchor then
      local x, y, z = chef.unit_position(u)
      if not x then return nil end
      anchor = { x, y, z }
    end
    -- Follow the actual held object's pose rather than replaying a standing feet offset while prone/crouched.
    -- Retain legacy feet samples for diagnosis; new samples learn release offsets relative to this held object.
    local ahead, right, up = k.offset_ahead or 0, k.offset_right or 0, k.offset_up or RELEASE_UP
    local ox = anchor[1] + hx * ahead + hy * right
    local oy, oz = anchor[2] + hy * ahead - hx * right, anchor[3] + up
    local mx, my = my_move()
    local along = mx * hx + my * hy
    local yaw = math.rad(k.yaw or 0)       -- (+: right)
    local dx, dy = hx * math.cos(yaw) + hy * math.sin(yaw), hy * math.cos(yaw) - hx * math.sin(yaw)
    local s = moved_speed(kind, k.speed or base_speed(kind), along, speed_up(false))
    local lift = (math.abs(along) >= WALK and k.walk) or k.lift or GRENADE_LIFT
    local drag = DRAG[kind] or 0
    local pitch = camera_pitch(c) + math.rad(lift)
    local vx, vy, vz = dx * s * math.cos(pitch), dy * s * math.cos(pitch), s * math.sin(pitch)
    preview = { kind = kind, t = now(), x = ox, y = oy, z = oz, vx = vx, vy = vy, vz = vz,
                drag = drag, along = along, bonus = speed_up(false),
                anchor = { anchor[1], anchor[2], anchor[3] }, hx = hx, hy = hy,
                pitch = math.deg(camera_pitch(c)) }
    local deepest = (feet_z or (c.z - 2)) - DEEPEST
    local pts, t, x, y, z = { { ox, oy, oz } }, 0, ox, oy, oz
    while t < MOST_T do
      local dt = (vz < 0 and finer(pts[1], pts[#pts])) and STEP * DOWN or STEP
      for _ = 1, 3 do                             -- (three steps a segment: drag)
        local h = dt / 3
        local d = drag * math.sqrt(vx * vx + vy * vy + vz * vz) * h
        vx, vy, vz = vx - d * vx, vy - d * vy, vz - GRAVITY * h - d * vz
        x, y, z = x + vx * h, y + vy * h, z + vz * h
      end
      t = t + dt
      pts[#pts + 1] = { x, y, z }
      if z < deepest then break end
    end
    -- drawn from GRENADE_SKIP m off the start: from the hand it was in the way of the view
    local from = 1
    while from < #pts - 1 and (pts[from][1] - ox) ^ 2 + (pts[from][2] - oy) ^ 2 + (pts[from][3] - oz) ^ 2
          < GRENADE_SKIP * GRENADE_SKIP do from = from + 1 end
    if from > 1 then
      local out = {}
      for i = from, #pts do out[#out + 1] = pts[i] end
      pts = out
    end
    return pts
  end

  -- a throw from the grenade's positions after it left my hand: speed, lift, yaw, and where it started from my feet
  -- (ahead, right, up), or nil
  local function measure(f)
    local p = f.pts
    local v = {}                                -- each step's speed
    for i = 2, #p do
      local dt = p[i][1] - p[i - 1][1]
      v[i] = dt > 0 and math.sqrt((p[i][2] - p[i - 1][2]) ^ 2 + (p[i][3] - p[i - 1][3]) ^ 2
                                  + (p[i][4] - p[i - 1][4]) ^ 2) / dt or 0
    end
    -- The first fast positions can still be the throw animation (especially Melta). Test.3's first matching pair
    -- could select that swing, then give up after a bad fit. Fit an early airborne window instead, retrying only
    -- candidates within the existing 0.2s early-flight limit. A longer window averages Giga's oscillating root path.
    local function fit(first)
      local t0 = p[first][1]
      local n, st, stt, sx, sy, sz, stx, sty, stz, span = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
      for i = first, #p do
        local t = p[i][1] - t0
        if t > GRENADE_FIT or (i > first + 1 and v[i] < 0.5 * v[i - 1]) then break end
        local z = p[i][4] + 0.5 * GRAVITY * t * t
        n, st, stt, span = n + 1, st + t, stt + t * t, t
        sx, sy, sz = sx + p[i][2], sy + p[i][3], sz + z
        stx, sty, stz = stx + t * p[i][2], sty + t * p[i][3], stz + t * z
      end
      local den = n * stt - st * st
      if n < 4 or span < 0.25 or den <= 0 then return nil end
      local vx, vy, vz = (n * stx - st * sx) / den, (n * sty - st * sy) / den, (n * stz - st * sz) / den
      local x0, y0, z0 = (sx - vx * st) / n, (sy - vy * st) / n, (sz - vz * st) / n
      local off = 0
      for i = first, first + n - 1 do
        local t = p[i][1] - t0
        off = off + (p[i][2] - x0 - vx * t) ^ 2 + (p[i][3] - y0 - vy * t) ^ 2
              + (p[i][4] - z0 - vz * t + 0.5 * GRAVITY * t * t) ^ 2
      end
      off = math.sqrt(off / n)
      if off > GRENADE_OFF then return nil end
      return { t0 = t0, n = n, st = st, vx = vx, vy = vy, vz = vz, x = x0, y = y0, z = z0, rms = off, span = span }
    end
    local fitted
    for i = 2, #p - 2 do
      local elapsed = p[i][1] - f.left
      if elapsed > GRENADE_SOON then break end
      if elapsed >= 0.15 and v[i + 1] >= GRENADE_FAST and v[i + 2] >= GRENADE_FAST
         and math.abs(v[i + 1] - v[i + 2]) <= GRENADE_STEADY * v[i + 2] then
        fitted = fit(i)
        if fitted then break end
      end
    end
    if not fitted then return nil, 'no steady early flight fit' end
    local t0, n, st = fitted.t0, fitted.n, fitted.st
    local vx, vy, vz, x0, y0, z0 = fitted.vx, fitted.vy, fitted.vz, fitted.x, fitted.y, fitted.z
    local h = math.sqrt(vx * vx + vy * vy)
    if h < 1e-6 then return nil end
    -- the start: that path back at the last frame it was in my hand, from my feet then
    local tb = f.left - t0
    local bx, by, bz = x0 + vx * tb, y0 + vy * tb, z0 + vz * tb - 0.5 * GRAVITY * tb * tb
    local hx, hy = f.hx, f.hy
    local dx, dy = bx - f.feet[1], by - f.feet[2]
    local yaw = math.deg(math.atan2(vx * hy - vy * hx, vx * hx + vy * hy))
    if math.abs(yaw) < 1e-8 then yaw = 0 end
    -- The parabola's vz is at t0, not at release. Restore it to f.left, just as the position above is restored.
    -- Horizontal drag uses the actual mean sample time instead of assuming every fit lasted the full 0.3s.
    -- This remains a short-flight drag approximation; drag-free ballistic fixtures are exact at any frame rate.
    local r = 1 + (DRAG[f.kind] or 0) * math.sqrt(h * h + vz * vz) * (st / n - tb)
    h, vz = h * r, (vz - GRAVITY * tb) * r
    -- Invert the same native strength adjustment used to draw, preserving the fitted flight angle.
    local term = motion_term(f.kind, f.along)
    local speed = term and math.sqrt(math.max(0, h * h + vz * vz - term))
                  or math.sqrt(h * h + vz * vz) - f.along
    if speed <= 0 then return nil, 'thrown backwards' end
    local sa, sr, su = dx * hx + dy * hy, dx * hy - dy * hx, bz - f.feet[3]
    if sa * sa + sr * sr > GRENADE_REACH * GRENADE_REACH or su < 0 or su > GRENADE_REACH then
      return nil, string.format('a start no hand reaches (%.1f ahead %.1f right %.1f up)', sa, sr, su)
    end
    local anchor = f.anchor or f.feet
    local ax, ay = bx - anchor[1], by - anchor[2]
    return speed / f.up, math.deg(math.atan2(vz, h)) - f.pitch, yaw, sa, sr, su,
           ax * hx + ay * hy, ax * hy - ay * hx, bz - anchor[3], fitted.rms, fitted.span
  end

  local function remember(list, x)
    list[#list + 1] = x
    while #list > GRENADE_KEEP do table.remove(list, 1) end
  end

  local function learn(f)
    if GUIDED[f.kind] then return end
    -- One compact record per tracked throw, not one disk write per sample. The displayed launch is captured
    -- before the fast hand motion; actual points let us separate origin, yaw, movement and drag errors offline.
    if f.preview then
      local a, samples, next_t = f.preview, {}, 0
      for _, p in ipairs(f.pts) do
        local dt = p[1] - f.left
        if dt >= next_t and #samples < 16 then
          samples[#samples + 1] = string.format('%.4f:%.4f,%.4f,%.4f', dt, p[2], p[3], p[4])
          next_t = dt + (dt < 0.5 and 0.05 or 0.2)
        end
      end
      log('grenade compare: %s preview_age=%.4f start=%.4f,%.4f,%.4f velocity=%.4f,%.4f,%.4f '
          .. 'drag=%.6f along=%.4f bonus=%.3f samples=%s', f.kind, f.left - a.t, a.x, a.y, a.z,
          a.vx, a.vy, a.vz, a.drag, a.along, a.bonus, table.concat(samples, ';'))
    end
    local s, lift, yaw, ahead, right, up, oa, oright, oup, rms, span = measure(f)
    if s then
      local sample = { speed = s, lift = lift, yaw = yaw, ahead = ahead, right = right, up = up,
                       offset_ahead = oa, offset_right = oright, offset_up = oup }
      for field, x in pairs(sample) do
        if not valid_value(field, x) then s, lift = nil, 'invalid ' .. field; break end
      end
    end
    if not s then
      log('grenade %s thrown: not measured (%s; %d positions)', f.kind, lift or '?', #f.pts)
      return
    end
    local k = known[f.kind] or {}
    if k.fit_revision ~= 2 then
      -- Old angles/origins used the swing frame and short fit. Preserve them, but don't dilute this reference
      -- correction with nine stale samples. Speeds and feet-history remain available; other kinds are untouched.
      if not fit_backups[f.kind] then
        local old = { fit_revision = k.fit_revision }
        for _, field in ipairs(FIELDS) do
          old[field] = {}
          for i, x in ipairs(k[field] or {}) do old[field][i] = x end
        end
        fit_backups[f.kind] = old
      end
      for _, field in ipairs({ 'lift', 'walk', 'yaw', 'offset_ahead', 'offset_right', 'offset_up' }) do k[field] = {} end
      k.fit_revision = 2
      log('grenade calibration: %s fit revision 2; previous angles/origin preserved in fit_backups', f.kind)
    end
    for _, field in ipairs(FIELDS) do k[field] = k[field] or {} end
    known[f.kind] = k
    local walking = math.abs(f.along) >= WALK
    remember(k.speed, s)
    remember(walking and k.walk or k.lift, lift)
    remember(k.yaw, yaw)
    remember(k.ahead, ahead)
    remember(k.right, right)
    remember(k.up, up)
    remember(k.offset_ahead, oa)
    remember(k.offset_right, oright)
    remember(k.offset_up, oup)
    cached[f.kind] = nil
    log('grenade fit: %s span=%.3f rms=%.4f release_offset=%.4f,%.4f,%.4f', f.kind, span, rms, oa, oright, oup)
    log('grenade %s thrown%s: %.1f m/s %+.1f deg up %+.1f right, from %.2f ahead %.2f right %.2f up; now %.1f m/s, '
        .. '%+.1f standing, %s walking, %+.1f right, from %.2f %.2f %.2f', f.kind, walking and ' walking' or '', s, lift,
        yaw, ahead, right, up, median(k.speed), median(k.lift) or GRENADE_LIFT,
        median(k.walk) and string.format('%+.1f', median(k.walk)) or '-', median(k.yaw), median(k.ahead),
        median(k.right), median(k.up))
    persist()
  end

  -- Speed starts a possible flight, never confirms a release by itself. Keep drawing a fast-moving grenade still
  -- beside the hand; only follow/learn it once it separates. Buffer early positions so confirmation doesn't shift
  -- the measured release to the edge of the hand radius. A brief pose transition may precede physical separation.
  local held, pending = nil, nil
  local flights, flying = {}, {}     -- grenades thrown: { u, kind, pts, pitch, mx, my, along, up, at, feet, hx, hy,
                                     -- left }; unit -> true while followed
  local context, last_grip, last_keys, refresh_at = nil, nil, false, 0
  local said_hand = nil
  local world_seen = nil
  local armour_next = 0
  local M2 = { on = true }
  function M2.stop() if watch then watch.stop() end end
  -- called every frame; free: nothing else is drawn. Returns the arc's points, or nil
  function M2.update(c, free)
    local t = now()
    if context ~= me_unit or world_seen ~= chef.world_id() then
      held, pending, flights, flying, preview, armour_next = nil, nil, {}, {}, nil, 0
      context, world_seen, last_grip, last_keys, refresh_at = me_unit, chef.world_id(), nil, false, 0
      said_hand = nil
    end
    local grip = hand_pose()
    local keys = chef.key_down('g') == true or throw_down or aim_down
    local posed = grip == 40 or grip == 41 or grip == 42
    local hand = (held or keys or posed or grip == nil) and right_hand() or nil
    if watch and ((keys and not last_keys) or (posed and grip ~= last_grip)) and t >= refresh_at then
      watch.refresh()                          -- asynchronous, not an immediate list; no per-frame full scans
      refresh_at = t + 0.1
    end
    last_keys, last_grip = keys, grip
    if held and me and chef.unit_alive(held.u) and t - held.seen <= 0.2 then
      local x, y, z = chef.unit_position(held.u)
      local fast = x and t > held.t and ((x - held.p[1]) ^ 2 + (y - held.p[2]) ^ 2 + (z - held.p[3]) ^ 2)
                       / ((t - held.t) ^ 2) >= GRENADE_FAST * GRENADE_FAST
      if fast and not pending then
        local ref = held.preview
        if not ref or held.t - ref.t > 0.25 then ref = held end
        pending = { u = held.u, kind = held.kind, pts = { { held.t, held.p[1], held.p[2], held.p[3] } },
                    pitch = ref.pitch, mx = held.mx, my = held.my, along = ref.along, up = ref.bonus or held.up,
                    feet = { held.feet[1], held.feet[2], held.feet[3] }, hx = ref.hx, hy = ref.hy, left = held.t,
                    preview = held.preview, anchor = ref.anchor and { ref.anchor[1], ref.anchor[2], ref.anchor[3] }
                                                   or { held.p[1], held.p[2], held.p[3] } }
      end
      if fast and not close_to_hand(held.u, hand, x, y, z) then
        pending.at = t
        flights[#flights + 1], flying[held.u] = pending, true
        log('grenade release: %s (separated from %s)', held.kind, hand and 'hand node' or 'feet fallback')
        pending = nil
      elseif fast then
        pending.pts[#pending.pts + 1] = { t, x, y, z }
        -- A long run/hand swing isn't an early free flight; retain a bounded candidate window.
        if t - pending.left > GRENADE_SOON then pending = nil end
      else
        pending = nil
      end
    else
      held, pending = nil, nil
    end
    local u, kind = in_hand(flying, hand, grip)
    if u ~= said_hand then
      said_hand = u
      log('grenade hand: %s (pose %s, %s)', kind or 'none', tostring(grip), hand and 'hand node' or 'feet fallback')
    end
    if u then
      local x, y, z = chef.unit_position(u)
      if x then
        if armour_of ~= me_unit and t >= armour_next then
          find_armour()
          armour_next = t + GRIP_RETRY       -- failed armour lookup must not scan every frame
        end
        if not held or held.u ~= u then held, pending = { u = u, kind = kind, p = {}, feet = {} }, nil end
        local mx, my = my_move()
        local fh = math.max(1e-6, math.sqrt(c.fx * c.fx + c.fy * c.fy))
        held.t, held.seen, held.pitch = t, t, math.deg(camera_pitch(c))
        held.p[1], held.p[2], held.p[3] = x, y, z
        held.mx, held.my, held.along, held.up = mx, my, (mx * c.fx + my * c.fy) / fh, speed_up(false)
        held.feet[1], held.feet[2], held.feet[3], held.hx, held.hy = me[1], me[2], me[3], c.fx / fh, c.fy / fh
      end
    elseif held and not flying[held.u] and chef.unit_alive(held.u) and me and close_to_hand(held.u, hand) then
      -- Pending pose transition: update displacement samples, but do not extend its 0.2s grace or draw an arc.
      local x, y, z = chef.unit_position(held.u)
      held.t, held.p = t, { x, y, z }
    else
      held, pending = nil, nil
    end
    local keep = {}
    for _, f in ipairs(flights) do
      local x, y, z
      if chef.unit_alive(f.u) then x, y, z = chef.unit_position(f.u) end
      if x and t - f.at <= GRENADE_FLY then
        f.pts[#f.pts + 1] = { t, x, y, z }
        keep[#keep + 1] = f
      else
        flying[f.u] = nil
        learn(f)
      end
    end
    flights = keep
    if u and keys and free and M2.on then
      local pts = arc(c, u, kind, held and held.p)
      if pts and held then held.preview = preview end
      return pts
    end
    return nil
  end
  return M2
end)()

-- the weapon to draw for this frame: its row in WEAPONS and its muzzle, or nil
local function weapon_aimed(c)
  if AIMING.on_the_ship() then
    said_weapon, held, held_miss, weapon_log_at = nil, nil, nil, 0
    return nil
  end
  if not ((weapon_arcs or AIMING.circle_on) and aim_down) then
    said_weapon, held = nil, nil
    weapon_log_at = 0
    return AIMING.idle_circle(c)
  end
  local kind, u = held_weapon(c)
  if kind and WEAPONS[kind].ub and not underbarrel_on() then kind = nil end     -- (its rifle: no arc)
  if kind and (WEAPONS[kind].off or not (WEAPONS[kind].circle and AIMING.circle_on or not WEAPONS[kind].circle and weapon_arcs)) then
    kind, held_miss = nil, nil
  end
  if kind then
    local seated, vehicle_kind, _, up = in_vehicle()
    -- Recorded FRV driver hand/root stays 0.46m above feet, versus 0.97-1.15m when a passenger aims.
    -- Require elevated vehicle geometry to avoid suppressing a prone soldier beside an FRV on the ground.
    if seated and up and up >= 0.35
       and (vehicle_kind == 'cc21c7ffd3ebefb9' or vehicle_kind == '2d85bfe3d8717fe5'
           or vehicle_kind == '9b2140378640432e') then
      local _, _, z = chef.unit_position(u)
      if z and z - me[3] < 0.7 then
        kind, held_miss = nil, 'FRV weapon not raised for aiming'
      end
    end
  end
  local fp = kind and first_person(c, u, WEAPONS[kind]) and not AIMING.camera_moved(c)
  local hidden = fp and (WEAPONS[kind].circle or not AIMING.first_person)
  local said = kind and (WEAPONS[kind][5] .. (hidden and ' (first person: not drawn)' or (fp and ' (first person)' or '')))
               or ('none' .. (held_miss and ' (' .. held_miss .. ')' or ''))
  if said ~= said_weapon and (kind or held_miss == 'throwable hand pose' or now() >= weapon_log_at) then
    said_weapon = said
    weapon_log_at = now() + 0.5
    log('weapon aimed: %s', said)
  end
  if not kind or hidden then return nil end
  return WEAPONS[kind], muzzle_of(u, WEAPONS[kind]), u, kind, fp
end

-- ------------------------------------------------------------------ C4's mode by the crosshair
-- C4 is known for not showing which of its two is in the hand. While it is in mine (hand pose C4_GRIP) and its mode can
-- be read, an icon to the right of the crosshair, the game's own: an arrow up over a charge for DEPLOY, a toothed ring
-- for DETONATE. An option turns it off (another HUD mod may show it).
-- The icons are cut from the game's HUD atlas (tools/c4_icons.py) and shipped in the mod's patch, each at a few sizes
-- (the screen's drawing has no mipmaps): ICONS, put in by build.py, is mode -> { size, texture, ... } from the smallest.
-- The icon fills ICON_FILL of its texture's height. Where a texture can't be drawn (chef.bitmap gives false), the icon
-- is drawn with shapes after it, as 1.0.0 did.
local ICON_SIZE, ICON_GAP = 0.024, 0.06     -- of the screen's height: the icon's height, and from the centre to its left
local ICONS = "@ICONS@"
local ICON_FILL, ICON_ALPHA = 65 / 76, 200
if type(ICONS) == 'table' and chef.texture_sizes then
  local sizes = {}
  for _, l in pairs(ICONS) do sizes[l[#l]] = l end
  chef.texture_sizes(sizes)
end
local show_icon = true
if chef.has and chef.has('menu') then
  chef.title('Universal Trajectory Indicator')
  -- Rows in folded sections on a loader that has them (Chef 1.4.0), one flat list on an older one.
  local headed = chef.has('option_headings')
  local function heading(text) return headed and text or nil end
  local function toggle(id, label, default, set, section)
    local v = chef.option(id, { type = 'toggle', label = label, default = default, heading = heading(section) })
    if v == nil then v = default end
    set(v)
    chef.on_change(id, function(value) set(value == true) end)
  end
  arc_color = chef.option('arc_color', { type = 'choice', label = 'Arc colour', heading = heading('Arc look'),
                                         choices = { 'Green', 'White', 'Blue', 'Red' }, default = 1 })
  chef.on_change('arc_color', function(v) arc_color = v end)
  arc_width = chef.option('arc_width', { type = 'slider', label = 'Arc width', min = 1, max = 7, step = 1, default = 3 })
  chef.on_change('arc_width', function(v) arc_width = v end)
  toggle('arc_solid', 'Solid arc (no dashes)', false, function(v) arc_solid = v end)
  toggle('stratagem_arcs', 'Stratagem arcs', true, function(v) AIMING.stratagem_on = v end, 'Stratagems, C4 and grenades')
  toggle('c4_arcs', 'C4 arcs', true, function(v) AIMING.c4_on = v end)
  toggle('c4_icon', 'C4 mode icon by the crosshair', true, function(v) show_icon = v end)
  toggle('grenade_arcs', 'Grenade arcs (G held, or one in hand aimed)', true, function(v) grenade.on = v end)
  toggle('weapon_arcs', 'All weapon arcs', true, function(v) weapon_arcs = v end, 'Weapon arcs')
  toggle('weapon_arcs_first_person', 'Arcs in first person too', false, function(v) AIMING.first_person = v end)
  local rows = {}
  for kind in pairs(WEAPONS) do rows[#rows + 1] = kind end
  table.sort(rows, function(a, b) return WEAPONS[a][5] < WEAPONS[b][5] end)
  local function weapon_rows(circle)
    for _, kind in ipairs(rows) do
      local w = WEAPONS[kind]
      if (w.circle == true) == circle then
        toggle('weapon_' .. kind, w[5], true, function(v) w.off = not v end)
      end
    end
  end
  weapon_rows(false)
  toggle('aim_circle', 'All aim circles', true, function(v) AIMING.circle_on = v end, 'Aim circle for rifles with no crosshair')
  toggle('aim_circle_idle', 'Also while not aiming', false, function(v) AIMING.circle_idle = v end)
  weapon_rows(true)
end
local icon_mode, icon_next = nil, 0

-- In a vehicle the icon shows only in C4's aim pose (1.0.0 kept it up all the time; 1.0.1-test.1-7 left it out): a
-- passenger leans out to aim, the driver can't aim. My helldiver seated in one is within VEHICLE_NEAR m of
-- its middle across, or within VEHICLE_SEAT m and VEHICLE_UP m or more above its base (standing by one, my feet are on
-- the ground). Seats measured: an FRV's 0.4-0.7 m off its middle and 0.6 m up, a tank's on its top 3.1 m off and 2.4 m
-- up (1.0.1-test.1-5; standing by an FRV, 2 m off and 0.4 m under its base). The vehicles: the FRVs, the tanks and the
-- exosuit (filediver's names, as in Extended Pickup Icons Range).
local VEHICLES = { cc21c7ffd3ebefb9 = true, ['2d85bfe3d8717fe5'] = true, ['9b2140378640432e'] = true,
                   ['16474112801385b6'] = true, b0c9faf4af8903f9 = true, ['79e4b3d2da5e45e3'] = true }
local VEHICLE_NEAR, VEHICLE_SEAT, VEHICLE_UP = 1.2, 4.5, 0.35
local vehicle_watch = chef.watch and chef.watch(VEHICLES, 0.5)

in_vehicle = function()
  if not (vehicle_watch and me) then return false end
  local best, bup, selected
  for _, it in ipairs(vehicle_watch.items) do
    if chef.unit_alive(it.unit) then
      local x, y, z = chef.unit_position(it.unit)
      if x then
        local across = math.sqrt((x - me[1]) ^ 2 + (y - me[2]) ^ 2)
        if not best or across < best then best, bup, selected = across, me[3] - z, it end
      end
    end
  end
  return best ~= nil and (best < VEHICLE_NEAR or (best < VEHICLE_SEAT and bup >= VEHICLE_UP)),
         selected and selected.kind, selected and selected.unit, bup
end

-- DEVELOPMENT_VEHICLE_TRACE_BEGIN
-- test.8: seat/aim eligibility is not yet exposed by a verified loader API. Collect existing animation variables
-- on vehicle aim transitions without guessing a driver enum or suppressing working passenger arcs.
-- No new watch/world scan; at most 16 snapshots per load (entry and 0.7s after entry).
weapon_diagnostic.vehicle = (function()
  local state = { count = 0, indices = {} }
  local names = { 'character_state', 'steering_turn', 'gunner_traverse', 'move_speed', 'aim_horizontal', 'aim_vertical' }
  local function variable(name)
    if state.unit ~= me_unit then state.unit, state.indices = me_unit, {} end
    local row = state.indices[name]
    if not row or (not row.index and now() >= row.next) then
      row = { next = now() + GRIP_RETRY }; state.indices[name] = row
      if chef.call_kind('Unit.has_animation_state_machine', PLAYER, me_unit) == true
         and chef.call_kind('Unit.animation_has_variable', PLAYER, me_unit, name) == true then
        local idx = chef.call_kind('Unit.animation_find_variable', PLAYER, me_unit, name)
        if type(idx) == 'number' then row.index = idx end
      end
    end
    return row.index and chef.call_kind('Unit.animation_get_variable', PLAYER, me_unit, row.index)
  end
  return function(c, w, muzzle, unit, kind)
    local right, t = aim_down, now()
    local entry = right and (not state.right or state.world ~= chef.world_id())
    state.right, state.world = right, chef.world_id()
    if not right then state.next = nil; return end
    if state.count >= 16 or (not entry and (not state.next or t < state.next)) then return end
    -- Check proximity only for the two scheduled snapshots, not every held-aim frame.
    local seated, vehicle_kind, _, vehicle_up = in_vehicle()
    if not seated then state.next = nil; return end
    local phase
    if entry then phase, state.next = 'entry', t + 0.7
    elseif state.next and t >= state.next then phase, state.next = 'settled', nil end
    if not phase then return end
    state.count = state.count + 1
    log('vehicle aim %d %s t=%.6f hand=%s weapon=%s; proximity is not confirmed seat membership',
        state.count, phase, t, tostring(hand_pose()), tostring(kind))
    log('vehicle aim %d vehicle-kind=%s feet-above-root=%s', state.count, tostring(vehicle_kind), tostring(vehicle_up))
    local function point(label, x, y, z)
      if type(x) == 'number' then log('vehicle aim %d %s %.6f %.6f %.6f', state.count, label, x, y, z) end
    end
    point('camera-position', c.x, c.y, c.z)
    point('camera-forward', c.fx, c.fy, c.fz)
    if me then point('feet', me[1], me[2], me[3]) end
    local hand = right_hand()
    if hand then point('right-hand', hand[1], hand[2], hand[3]) end
    if unit then
      point('weapon-root', chef.unit_position(unit))
      point('weapon-forward', chef.unit_rotation(unit))
    end
    if muzzle then point('muzzle', muzzle[1], muzzle[2], muzzle[3]) end
    if me_unit then
      for _, name in ipairs(names) do
        log('vehicle aim %d animation %s=%s', state.count, name, tostring(variable(name)))
      end
    end
  end
end)()
-- DEVELOPMENT_VEHICLE_TRACE_END

local function draw_icon(mode)
  local w, h = chef.screen()
  if not (w and h) then return end
  local sz = math.floor(h * ICON_SIZE + 0.5)
  local layer = (chef.TOP or 0) + 1100      -- over the HUD and the map, under the menus
  local tex = type(ICONS) == 'table' and ICONS[mode]
  if tex and chef.bitmap then
    local box = sz / ICON_FILL
    if chef.bitmap(tex[#tex], w / 2 + h * ICON_GAP - (box - sz) / 2, h / 2 - box / 2, box, box,
                   chef.color(255, 255, 255, ICON_ALPHA), layer) then
      return
    end
  end
  local ink = chef.color(250, 250, 236, 190)
  local shade = chef.color(0, 0, 0, 110)
  -- a shadow 1/16 down and right, then the icon
  for pass = 1, 2 do
    local o = pass == 1 and math.max(1, sz / 16) or 0
    local col, l = pass == 1 and shade or ink, layer + pass
    local x, y = w / 2 + h * ICON_GAP + o, h / 2 - sz / 2 - o   -- the icon's bottom left
    if mode == 'deploy' then
      -- the game's icon on a grid 18 wide and 33.5 tall: an arrow up over a charge of two sticks, banded twice
      local u = sz / 33.5
      local function box(bx, by, bw, bh) chef.rect(x + bx * u, y + by * u, bw * u, bh * u, col, l) end
      chef.triangle(x + 9 * u, y + 33.5 * u, x, y + 27 * u, x + 18 * u, y + 27 * u, col, l)
      box(3.5, 22, 11, 5)
      for _, sx in ipairs({ 0, 10 }) do
        box(sx, 0, 8, 3)
        box(sx, 5, 8, 10)
        box(sx, 17, 8, 3)
      end
    else
      -- the game's icon: a ring with 20 teeth round it, open in the middle
      local r = sz / 2
      local cx, cy, base, half = x + r, y + r, r * 0.7, math.pi / 20
      for i = 0, 19 do
        local a = i * math.pi / 10
        chef.triangle(cx + math.sin(a) * r, cy + math.cos(a) * r, cx + math.sin(a - half) * base,
                      cy + math.cos(a - half) * base, cx + math.sin(a + half) * base, cy + math.cos(a + half) * base, col, l)
      end
      chef.ring(cx, cy, r * 0.42, r * 0.72, col, l)
    end
  end
end

local function c4_icon(c)
  if not show_icon then return end
  if now() >= icon_next then
    icon_next = now() + 0.1
    icon_mode = hand_pose() == C4_GRIP and (c4_posed or not in_vehicle()) and c4_mode(true) or nil
  end
  if icon_mode then draw_icon(icon_mode) end
end

-- ------------------------------------------------------------------ the hold's end

-- the hold, or nil once the throw has left my hand
local function follow_hold()
  if not hold then return nil end
  local h = hold
  local hx, hy, hz = h.pos[1], h.pos[2], h.pos[3]
  if h.off and me then hx, hy, hz = me[1] + h.off[1], me[2] + h.off[2], me[3] + h.off[3] end
  local gone = now() - h.at > (h.c4 and C4_HOLD or HOLD_MOST)
  if not gone and not h.c4 then
    local x, y, z
    if chef.unit_alive(h.unit) then x, y, z = chef.unit_position(h.unit) end
    gone = not x or (x - hx) ^ 2 + (y - hy) ^ 2 + (z - hz) ^ 2 >= HOLD_GONE * HOLD_GONE
  end
  if gone then
    hold = nil
    return nil
  end
  return h
end

-- ------------------------------------------------------------------ the frame
local said_world = nil

function M.update(dt)
  if said_world == nil then
    said_world = false
    log('Universal Trajectory Indicator %s, loader %s, api %s', VERSION, tostring(chef.loader_version), tostring(chef.api))
  end
  local c = chef.camera()
  if not (chef.world() and c) then return end
  if said_world ~= chef.world_id() then
    said_world = chef.world_id()
    ball, aiming, looking = nil, false, false
    c4_aim, c4_posed, c4_det, hold = false, false, nil, nil
  end
  update_feet(c)
  update_trail()
  read_buttons()
  read_input(c)
  read_c4(c)
  c4_icon(c)
  local h = follow_hold()
  local weapon, muzzle, weapon_unit, weapon_kind, weapon_fp, aim, aim_mode
  if not (aiming or c4_aim or h) then weapon, muzzle, weapon_unit, weapon_kind, weapon_fp = weapon_aimed(c) end
  if weapon and not AIMING.my_view(c, muzzle) then weapon, muzzle, weapon_unit, weapon_kind, weapon_fp = nil, nil, nil, nil, nil end
  if weapon then
    aim, aim_mode = weapon_aim(c, weapon_kind, weapon_unit, muzzle, weapon_fp)
  end
  weapon_diagnostic.vehicle(c, weapon, muzzle, weapon_unit, weapon_kind)
  weapon_diagnostic.update(c, weapon, muzzle, aim, weapon_unit, weapon_kind, aim_mode)
  local nade = grenade.update(c, not (aiming or c4_aim or h or (weapon and aim_down)))
  local c4_arc = not aiming and (c4_aim or (h and h.c4))
  if (aiming or c4_aim or h) and not (c4_arc and AIMING.c4_on or not c4_arc and AIMING.stratagem_on) then
    clear_arc()
  elseif aiming then
    draw_arc(c, false, release_point(c, ball, false))
  elseif c4_aim then
    draw_arc(c, true, release_point(c, c4_det, true))
  elseif h then
    draw_arc(c, h.c4, release_point(c, h.unit, h.c4, h.off))
  elseif nade then
    draw_points(c, nade)
  elseif weapon and weapon.circle then
    clear_arc()
    if aim and not AIMING.on_the_ship() then AIMING.draw_circle() end
  elseif weapon then
    draw_points(c, weapon_path(c, weapon, muzzle, aim))
  else
    clear_arc()
  end
end

function M.shutdown()
  if players then players.stop() end
  if det_watch then det_watch.stop() end
  if vehicle_watch then vehicle_watch.stop() end
  if ball_watch then ball_watch.stop() end
  if weapon_watch then weapon_watch.stop() end
  weapon_diagnostic.stop()
  grenade.stop()
end

return M
