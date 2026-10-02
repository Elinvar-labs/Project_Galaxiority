from raylibpy import *
from settings import *

from src.project_galaxy.skybox import create_skybox
from src.project_galaxy.stars import *
from src.project_galaxy.camera import ChaseCamera
from src.project_galaxy.input import Input



# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------
init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Project Galaxy")
set_target_fps(60)
toggle_fullscreen()

input = Input(SCREEN_WIDTH, SCREEN_HEIGHT)

chase_camera = ChaseCamera()
camera = chase_camera.camera

# Ship condition
ship_position = Vector3(0.0, -0.5, 0.0)
yaw = 0.0  # yaw (left/right)
pitch = 0.0  # pitch (up/down)
roll = 0.0  # roll
throttle = 0.35
boost = False
speed = 0.0

stars = [make_star(ship_position) for _ in range(STAR_COUNT)]

# =========================================================================
# Cache and constants for the hot loop
# =========================================================================

# draw_sphere() generates a mesh EVERY call — this is very expensive.
# Build a low-poly unit sphere once and reuse it
# for all stars and both engine nozzles (scale via draw_model).
star_model = load_model_from_mesh(gen_mesh_sphere(1.0, 4, 6))

# Parallel arrays instead of a list of dictionaries: no dict unpacking,
# no attribute lookups in the hottest loop.
star_pos_x = [s["pos"].x for s in stars]
star_pos_y = [s["pos"].y for s in stars]
star_pos_z = [s["pos"].z for s in stars]
star_r     = [s["radius"] for s in stars]
star_col   = [s["color"]  for s in stars]
STAR_N     = len(stars)

# Aliases for frequent calls (saves global lookups).
_cos, _sin, _exp = math.cos, math.sin, math.exp
_clamp = clamp

# Reusable Vector3 — avoid allocations per frame.
_origin    = Vector3(0.0, 0.0, 0.0)
_up_y      = Vector3(0.0, 1.0, 0.0)
_one       = Vector3(1.0, 1.0, 1.0)
_star_tmp  = Vector3(0.0, 0.0, 0.0)          # scratch vector for star position
_flame_pos_l = Vector3(-0.35, 0.0, 2.5)
_flame_pos_r = Vector3( 0.35, 0.0, 2.5)

# HUD colors: Color(...) is created once, not every frame.
HUD_TEXT    = RAYWHITE
HUD_GREEN   = GREEN
HUD_ORANGE  = ORANGE
STICK_RING  = Color(255, 255, 255, 25)
BAR_BG      = Color(40, 40, 40, 200)
RETICLE_COL = Color(255, 255, 255, 170)

FIELD_SQ = FIELD_RADIUS * FIELD_RADIUS


Sky, sky_shader = create_skybox()
ship = load_model("assets/models/Striker/glTF/Striker.gltf")

init_audio_device()
bg_music = load_music_stream("assets/audio/music/action_0.mp3")
bg_music.play()
bg_music.looping = True

play_music_stream(bg_music)

while not window_should_close():
    delta = get_frame_time()
    if delta > 0.05:
        delta = 0.05

    update_music_stream(bg_music)

    # ---------------- INPUT ----------------
    input.update()
    if input.wants_quit:
        break


    # ---------------- ORIENTATION ----------------
    yaw   -= input.stick_x * TURN_RATE * delta
    pitch -= input.stick_y * TURN_RATE * delta
    pitch  = _clamp(pitch, -PITCH_LIMIT, PITCH_LIMIT)

    roll += input.roll_dir * ROLL_RATE * delta
    roll  = (roll + math.pi) % (2.0 * math.pi) - math.pi

    # ---------------- THROTTLE ----------------
    throttle += input.throttle_wheel * 0.08
    throttle += input.throttle_axis * THROTTLE_SPEED * delta
    if input.brake:
        throttle -= 2.0 * delta
    throttle = _clamp(throttle, 0.0, 1.0)

    boost = input.boost

    # ---------------- SHIP BASIS (scalar, without Vector3) ----------------
    cy = _cos(yaw);   sy = _sin(yaw)
    cp = _cos(pitch); sp = _sin(pitch)
    cr = _cos(roll);  sr = _sin(roll)

    fx = -sy * cp
    fy =  sp
    fz = -cy * cp

    ux = -cy * sr + sy * sp * cr
    uy =  cp * cr
    uz =  sy * sr + cy * sp * cr
    # right is not used — don't compute it at all.

    # ---------------- MOVE ----------------
    speed  = throttle * MAX_SPEED * (BOOST_MULT if boost else 1.0)
    spd_dt = speed * delta
    sx  = ship_position.x + fx * spd_dt
    sy_ = ship_position.y + fy * spd_dt
    sz  = ship_position.z + fz * spd_dt
    ship_position.x = sx
    ship_position.y = sy_
    ship_position.z = sz

    # ---------------- STARS: recycle ----------------
    # Local references to arrays speed up indexing.
    px_arr, py_arr, pz_arr = star_pos_x, star_pos_y, star_pos_z
    for i in range(STAR_N):
        dx = px_arr[i] - sx
        dy = py_arr[i] - sy_
        dz = pz_arr[i] - sz
        if dx * dx + dy * dy + dz * dz > FIELD_SQ:
            p = random_star_position(ship_position)
            px_arr[i] = p.x
            py_arr[i] = p.y
            pz_arr[i] = p.z

    # ---------------- CAMERA ----------------
    desired_x = sx - fx * CAM_DISTANCE + ux * CAM_HEIGHT
    desired_y = sy_ - fy * CAM_DISTANCE + uy * CAM_HEIGHT
    desired_z = sz - fz * CAM_DISTANCE + uz * CAM_HEIGHT

    k = 1.0 - _exp(-14.0 * delta)
    cam = camera.position
    cam.x += (desired_x - cam.x) * k
    cam.y += (desired_y - cam.y) * k
    cam.z += (desired_z - cam.z) * k

    tgt = camera.target
    tgt.x = sx + fx * CAM_LOOK_AHEAD
    tgt.y = sy_ + fy * CAM_LOOK_AHEAD
    tgt.z = sz + fz * CAM_LOOK_AHEAD

    cam_up = camera.up
    cam_up.x = ux
    cam_up.y = uy
    cam_up.z = uz

    # ---------------- RENDER ----------------
    begin_drawing()
    clear_background(BLACK)
    begin_mode3d(camera)

    # --- Skybox: no depth writes, no backface culling ---
    rl_disable_backface_culling()
    rl_disable_depth_mask()
    draw_model(Sky, _origin, 1.0, WHITE)
    rl_enable_backface_culling()
    rl_enable_depth_mask()

    # --- Stars: one model, scaled and colored ---
    for i in range(STAR_N):
        _star_tmp.x = px_arr[i]
        _star_tmp.y = py_arr[i]
        _star_tmp.z = pz_arr[i]
        draw_model(star_model, _star_tmp, star_r[i], star_col[i])

    # --- Ship and nozzles ---
    rl_push_matrix()
    rl_translatef(sx, sy_, sz)
    rl_rotatef(yaw   * RAD2DEG, 0.0, 1.0, 0.0)
    rl_rotatef(pitch * RAD2DEG, 1.0, 0.0, 0.0)
    rl_rotatef(roll  * RAD2DEG, 0.0, 0.0, 1.0)

    ship.draw_ex(_origin, _up_y, 180.0, _one, WHITE)

    flame = 0.12 + 0.30 * throttle
    if boost:
        flame *= 1.8
    if flame > 0.05:
        draw_model(star_model, _flame_pos_l, flame, ORANGE)
        draw_model(star_model, _flame_pos_r, flame, ORANGE)

    rl_pop_matrix()
    end_mode3d()

    # ---------------- HUD ----------------
    draw_text("Mouse = virtual stick (steer)   Arrows = steer too", 10, 10, 20, HUD_TEXT)
    draw_text("A / D = roll    W / S or Wheel = throttle",           10, 36, 20, HUD_TEXT)
    draw_text("Shift = boost   Space = brake",                       10, 62, 20, HUD_TEXT)
    draw_text(f"Speed: {speed:6.1f}",              10,  96, 20,
              HUD_ORANGE if boost else HUD_GREEN)
    draw_text(f"Throttle: {throttle * 100:3.0f}%", 10, 122, 20, HUD_TEXT)
    draw_text(f"Roll: {roll * RAD2DEG:6.1f} deg",  10, 148, 20, HUD_TEXT)

    bar_x, bar_y, bar_w, bar_h = SCREEN_WIDTH - 46, 140, 22, 420
    draw_rectangle(bar_x, bar_y, bar_w, bar_h, BAR_BG)
    fill_h = int(bar_h * throttle)
    draw_rectangle(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h,
                   HUD_ORANGE if boost else HUD_GREEN)
    draw_rectangle_lines(bar_x, bar_y, bar_w, bar_h, HUD_TEXT)

    cx_px = SCREEN_WIDTH  // 2
    cy_px = SCREEN_HEIGHT // 2
    draw_circle(cx_px, cy_px, 42, STICK_RING)

    mx = int(input.mouse.x)
    my = int(input.mouse.y)
    draw_line(mx - 18, my, mx - 6, my, RETICLE_COL)
    draw_line(mx + 6, my, mx + 18, my, RETICLE_COL)
    draw_line(mx, my - 18, mx, my - 6, RETICLE_COL)
    draw_line(mx, my + 6, mx, my + 18, RETICLE_COL)
    draw_circle(mx, my, 2, RETICLE_COL)

    draw_fps(10, SCREEN_HEIGHT - 30)
    end_drawing()

close_window()