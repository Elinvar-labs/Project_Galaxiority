"""Оркестратор сцены и главный цикл."""
import math
import os

from raylibpy import (BLACK, WHITE, DARKGRAY, RED, ORANGE, GREEN,
                      Vector2, Vector3,
                      begin_drawing, begin_mode3d, clear_background,
                      close_window, draw_model, end_drawing, end_mode3d,
                      get_frame_time, init_window,
                      rl_disable_backface_culling,
                      rl_disable_depth_mask, rl_enable_backface_culling,
                      rl_enable_depth_mask, set_target_fps,
                      window_should_close,
                      get_world_to_screen,
                      draw_rectangle, draw_rectangle_lines,
                      draw_text, draw_text_ex, measure_text_ex,
                      load_font, get_font_default,
                      is_key_pressed,
                      KEY_ENTER, KEY_KP_ENTER, KEY_SPACE, KEY_Y,
                      get_time, draw_circle, draw_circle_lines, Color)

from .camera import ChaseCamera, follow_ship
from .enemy_field import EnemyField
from .fields import AsteroidField, StarField
from .hud import HUD
from .input import Input
from .particles import ParticleSystem
from .scene import SceneAssets
from .settings import (ASTEROID_COUNT, FIELD_RADIUS, SCREEN_HEIGHT,
                       SCREEN_WIDTH, STAR_COUNT)
from .ship import Ship
from .stars import (make_asteroid, make_star,
                    random_asteroid_position, random_star_position)
from .audio import AudioManager

# --- Collision tuning ---
SHIP_COLLISION_RADIUS = 1.2
ASTEROID_COLLISION_SCALE = 1.1

BULLET_HIT_SURF = 1.05
SMALL_HIT_SCALE = 0.35

# --- Баланс врагов ---
ENEMY_COUNT          = 4
ENEMY_SPAWN_DISTANCE = 200.0
ENEMY_RESPAWN_DELAY  = 7.0
PLAYER_HIT_RADIUS    = 1.4
ENEMY_HIT_RADIUS     = 1.4

# --- Геометрия полосок HP ---
ENEMY_BAR_W          = 70
ENEMY_BAR_H          = 7
PLAYER_BAR_W         = 320
PLAYER_BAR_H         = 22
PLAYER_BAR_MARGIN    = 30

# --- Состояния игры ---
STATE_PLAYING   = "playing"
STATE_GAME_OVER = "game_over"

# --- Пути к шрифту с кириллицей (по порядку приоритета) ---
_FONT_CANDIDATES = (
    "assets/fonts/main.ttf",
    "assets/fonts/ui.ttf",
    "assets/fonts/Orbitron.ttf",
    "assets/fonts/Roboto-Regular.ttf",
)


class Game:
    __slots__ = ("assets", "input", "camera",
                 "ship", "stars", "asteroids", "enemies",
                 "particles", "hud",
                 "explosion_count", "audio", "player_hits",
                 "_origin", "_star_tmp", "_aster_tmp",
                 "_field_sq",
                 "state", "_ui_font", "_ui_font_cyrillic")

    def __init__(self) -> None:
        init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Project Galaxority")
        set_target_fps(60)

        self.assets = SceneAssets()
        self.input = Input(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.camera = ChaseCamera().camera

        self.ship = Ship()

        self.stars = StarField(make_star, random_star_position,
                               STAR_COUNT, self.ship.position)
        self.asteroids = AsteroidField(make_asteroid, random_asteroid_position,
                                       ASTEROID_COUNT, self.ship.position)
        self.enemies = EnemyField(ENEMY_COUNT, self.ship.position,
                                  ENEMY_SPAWN_DISTANCE, ENEMY_RESPAWN_DELAY)

        self.particles = ParticleSystem(self.assets.sphere_model)
        self.hud = HUD(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.explosion_count = 0
        self.player_hits = 0
        self.audio = AudioManager()

        self._origin = Vector3(0.0, 0.0, 0.0)
        self._star_tmp = Vector3(0.0, 0.0, 0.0)
        self._aster_tmp = Vector3(0.0, 0.0, 0.0)

        self._field_sq = FIELD_RADIUS * FIELD_RADIUS

        self.state = STATE_PLAYING

        # UI-шрифт (для экрана Game Over)                         # <-- НОВОЕ
        self._ui_font = None
        self._ui_font_cyrillic = False
        self._init_ui_font()

    # ------------------------------------------------------------------
    #  Шрифт для UI
    # ------------------------------------------------------------------
    def _init_ui_font(self) -> None:
        """Пытается загрузить шрифт с кириллицей; иначе — дефолтный raylib."""
        for path in _FONT_CANDIDATES:
            if not os.path.exists(path):
                continue
            try:
                f = load_font(path)
                if getattr(f, "texture", None) is not None and f.texture.id != 0:
                    self._ui_font = f
                    self._ui_font_cyrillic = True
                    return
            except Exception:
                continue
        # Фолбэк — стандартный шрифт (без кириллицы)
        try:
            self._ui_font = get_font_default()
        except Exception:
            self._ui_font = None
        self._ui_font_cyrillic = False

    # ------------------------------------------------------------------
    def _on_asteroid_hit(self, x, y, z, radius) -> None:
        self.particles.spawn_explosion(x, y, z, radius)
        self.audio.play_explosion(radius)
        self.explosion_count += 1

    # ------------------------------------------------------------------
    #  Сброс мира (после проигрыша)
    # ------------------------------------------------------------------
    def _reset_world(self) -> None:
        self.ship = Ship()
        p = self.ship.position

        self.stars = StarField(make_star, random_star_position,
                               STAR_COUNT, p)
        self.asteroids = AsteroidField(make_asteroid, random_asteroid_position,
                                       ASTEROID_COUNT, p)
        self.enemies = EnemyField(ENEMY_COUNT, p,
                                  ENEMY_SPAWN_DISTANCE, ENEMY_RESPAWN_DELAY)
        self.particles = ParticleSystem(self.assets.sphere_model)

        self.explosion_count = 0
        self.player_hits = 0
        self.state = STATE_PLAYING

    # ------------------------------------------------------------------
    def _trigger_game_over(self) -> None:
        self.state = STATE_GAME_OVER
        ship_pos = self.ship.position
        self.particles.spawn_explosion(
            ship_pos.x, ship_pos.y, ship_pos.z, 4.0)
        self.audio.play_explosion(4.0)
        self.explosion_count += 1

    # ------------------------------------------------------------------
    def _handle_game_over_input(self) -> None:
        if (is_key_pressed(KEY_ENTER)
                or is_key_pressed(KEY_KP_ENTER)
                or is_key_pressed(KEY_SPACE)
                or is_key_pressed(KEY_Y)):
            self._reset_world()

    # ------------------------------------------------------------------
    def run(self) -> None:
        while not window_should_close():
            dt = get_frame_time()
            if dt > 0.05:
                dt = 0.05

            self.input.update()
            if self.input.wants_quit:
                break

            if self.state == STATE_GAME_OVER:
                # Мир заморожен, обновляем только частицы (догорают)
                self.particles.update(dt)
                self._handle_game_over_input()
            else:
                self._update(dt)

            self._render()

        self.audio.close()
        close_window()

    # ------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        ship = self.ship
        self.audio.update(dt, ship)

        # ship.update(self.input, dt)
        ship.update(self.input, dt, self.enemies.enemies)

        p = ship.position
        self.stars.recycle(p.x, p.y, p.z, self._field_sq, p)
        self.asteroids.update(
            p.x, p.y, p.z, self._field_sq, p,
            SHIP_COLLISION_RADIUS, ASTEROID_COLLISION_SCALE,
            self._on_asteroid_hit,
        )

        self.enemies.update(dt, p)

        self._resolve_bullet_hits()
        self._resolve_enemy_bullets()

        self.particles.update(dt)

        follow_ship(self.camera, ship, dt)

    # ------------------------------------------------------------------
    def _render(self) -> None:
        ship = self.ship
        stars = self.stars
        asteroids = self.asteroids
        assets = self.assets

        begin_drawing()
        clear_background(BLACK)
        begin_mode3d(self.camera)

        # Skybox
        rl_disable_backface_culling()
        rl_disable_depth_mask()
        draw_model(assets.sky, self._origin, 1.0, WHITE)
        rl_enable_backface_culling()
        rl_enable_depth_mask()

        # Stars
        s_tmp = self._star_tmp
        sphere = assets.sphere_model
        for i in range(stars.count):
            s_tmp.x = stars.pos_x[i]
            s_tmp.y = stars.pos_y[i]
            s_tmp.z = stars.pos_z[i]
            draw_model(sphere, s_tmp, stars.radius[i], stars.color[i])

        # Asteroids
        a_tmp = self._aster_tmp
        ast_model = assets.asteroid_model
        for i in range(asteroids.count):
            a_tmp.x = asteroids.pos_x[i]
            a_tmp.y = asteroids.pos_y[i]
            a_tmp.z = asteroids.pos_z[i]
            draw_model(ast_model, a_tmp, asteroids.radius[i], WHITE)

        # Ship + flame (в game_over не рисуем — корабль «взорвался»)
        if self.state == STATE_PLAYING:
            ship.draw(assets.ship_model, sphere, sphere)

        # Enemies (корабли + их пули)
        self.enemies.draw(assets.ship_model, sphere, sphere)

        # Explosion particles
        self.particles.draw()

        end_mode3d()

        # === 2D overlay ===
        self.hud.draw(ship, self.input, self.explosion_count)
        self._draw_enemy_hp_bars()
        self._draw_player_hp_bar()
        self._draw_enemy_indicators()
        if self.state == STATE_GAME_OVER:
            self._draw_game_over_screen()       # <-- НОВОЕ

        end_drawing()

    # ------------------------------------------------------------------
    #  Экран проигрыша
    # ------------------------------------------------------------------
    def _draw_game_over_screen(self) -> None:
        # Затемнение
        draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 190))

        title_ru  = "ВЫ ПРОИГРАЛИ..."
        title_en  = "YOU DIED..."
        prompt_ru = "Начать с начала?"
        prompt_en = "Restart?"
        hint_ru   = "Нажмите ENTER, ПРОБЕЛ или Y"
        hint_en   = "Press ENTER, SPACE or Y"

        if self._ui_font_cyrillic:
            title, prompt, hint = title_ru, prompt_ru, hint_ru
        else:
            title, prompt, hint = title_en, prompt_en, hint_en

        cx = SCREEN_WIDTH  * 0.5
        cy = SCREEN_HEIGHT * 0.5

        self._draw_centered(title,  cx, cy - 120, 84, RED, spacing=3.0)
        self._draw_centered(prompt, cx, cy + 20,  46, WHITE, spacing=1.0)

        # Мигающая подсказка (2 Гц)
        if int(get_time() * 2.0) % 2 == 0:
            self._draw_centered(hint, cx, cy + 120, 22,
                                (180, 180, 180, 255), spacing=1.0)

    def _draw_centered(self, text: str, cx: float, y: float,
                       size: int, color, spacing: float = 1.0) -> None:
        """Рисует текст, горизонтально центрированный по cx."""
        if self._ui_font is None:
            # Совсем без шрифта — используем draw_text
            approx_w = len(text) * size * 0.55
            draw_text(text, int(cx - approx_w * 0.5), int(y), size, color)
            return

        v = Vector2(cx, y)
        m = measure_text_ex(self._ui_font, text, float(size), spacing)
        v.x = cx - m.x * 0.5
        draw_text_ex(self._ui_font, text, v, float(size), spacing, color)

    # ------------------------------------------------------------------
    #  Полоски HP
    # ------------------------------------------------------------------
    def _draw_enemy_hp_bars(self) -> None:
        cam = self.camera
        cam_pos = cam.position
        tgt = cam.target

        fx = tgt.x - cam_pos.x
        fy = tgt.y - cam_pos.y
        fz = tgt.z - cam_pos.z
        flen = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
        fx /= flen; fy /= flen; fz /= flen

        w = ENEMY_BAR_W
        h = ENEMY_BAR_H

        for e in self.enemies.enemies:
            if not e.alive:
                continue
            ep = e.position

            dx = ep.x - cam_pos.x
            dy = ep.y - cam_pos.y
            dz = ep.z - cam_pos.z
            if dx * fx + dy * fy + dz * fz <= 0.5:
                continue

            wp = Vector3(ep.x, ep.y + 2.6, ep.z)
            sp = get_world_to_screen(wp, cam)

            if sp.x < -100 or sp.x > SCREEN_WIDTH + 100:
                continue
            if sp.y < -100 or sp.y > SCREEN_HEIGHT + 100:
                continue

            x = int(sp.x - w * 0.5)
            y = int(sp.y)

            frac = e.hp / e.max_hp if e.max_hp > 0 else 0.0
            if frac < 0.0: frac = 0.0

            draw_rectangle(x - 1, y - 1, w + 2, h + 2, BLACK)
            draw_rectangle(x, y, w, h, DARKGRAY)

            fill = int(w * frac)
            if fill > 0:
                if frac < 0.35:
                    c = RED
                elif frac < 0.7:
                    c = ORANGE
                else:
                    c = GREEN
                draw_rectangle(x, y, fill, h, c)

            draw_rectangle_lines(x - 1, y - 1, w + 2, h + 2, WHITE)

    def _draw_player_hp_bar(self) -> None:
        ship = self.ship
        w = PLAYER_BAR_W
        h = PLAYER_BAR_H
        x = PLAYER_BAR_MARGIN
        y = SCREEN_HEIGHT - PLAYER_BAR_MARGIN - h

        draw_rectangle(x - 2, y - 2, w + 4, h + 4, BLACK)

        frac = ship.hp / ship.max_hp if ship.max_hp > 0 else 0.0
        if frac < 0.0: frac = 0.0

        draw_rectangle(x, y, w, h, DARKGRAY)

        fill = int(w * frac)
        if fill > 0:
            if frac < 0.3:
                c = RED
            elif frac < 0.6:
                c = ORANGE
            else:
                c = GREEN
            draw_rectangle(x, y, fill, h, c)

        if ship.hit_flash > 0.0:
            frame = WHITE
        else:
            frame = (200, 200, 200, 255)
        draw_rectangle_lines(x - 2, y - 2, w + 4, h + 4, frame)

        draw_text(f"HP  {ship.hp} / {ship.max_hp}", x + 10, y + 4, 16, WHITE)

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    #  Индикаторы врагов на краях экрана
    # ------------------------------------------------------------------
    def _draw_enemy_indicators(self) -> None:
        """Красные кружки на границе экрана для врагов вне поля зрения."""
        enemies = self.enemies.enemies
        if not enemies:
            return

        cam = self.camera
        cam_pos = cam.position
        tgt = cam.target

        # --- forward ---
        fx = tgt.x - cam_pos.x
        fy = tgt.y - cam_pos.y
        fz = tgt.z - cam_pos.z
        flen = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
        fx /= flen; fy /= flen; fz /= flen

        # --- right = normalize(forward × up_world) ---
        uwx, uwy, uwz = cam.up.x, cam.up.y, cam.up.z
        rx = fy * uwz - fz * uwy
        ry = fz * uwx - fx * uwz
        rz = fx * uwy - fy * uwx
        rlen = math.sqrt(rx * rx + ry * ry + rz * rz)
        if rlen < 1e-6:
            # Фолбэк: up_world = (0, 1, 0)
            rx = -fz; ry = 0.0; rz = fx
            rlen = math.sqrt(rx * rx + rz * rz) or 1.0
        rx /= rlen; ry /= rlen; rz /= rlen

        # --- up = right × forward ---
        ux = ry * fz - rz * fy
        uy = rz * fx - rx * fz
        uz = rx * fy - ry * fx

        cx = SCREEN_WIDTH * 0.5
        cy = SCREEN_HEIGHT * 0.5
        margin = 46                                    # отступ от края экрана
        half_w = SCREEN_WIDTH * 0.5 - margin
        half_h = SCREEN_HEIGHT * 0.5 - margin
        radius = 11

        for e in enemies:
            if not e.alive:
                continue

            ep = e.position
            dx = ep.x - cam_pos.x
            dy = ep.y - cam_pos.y
            dz = ep.z - cam_pos.z

            f = dx * fx + dy * fy + dz * fz

            # Враг в поле зрения? — пропускаем индикатор
            if f > 0.5:
                sp = get_world_to_screen(ep, cam)
                if (margin <= sp.x <= SCREEN_WIDTH - margin and
                        margin <= sp.y <= SCREEN_HEIGHT - margin):
                    continue
                sx = sp.x - cx
                sy = sp.y - cy
            else:
                # Враг позади камеры — берём направление в базисе камеры,
                # чтобы индикатор НЕ «отражался» на противоположный край
                r = dx * rx + dy * ry + dz * rz
                u = dx * ux + dy * uy + dz * uz
                sx = r
                sy = -u        # экранный y идёт вниз

            slen = math.sqrt(sx * sx + sy * sy)
            if slen < 1e-4:
                # Враг ровно позади по центру — ставим индикатор снизу
                sx, sy = 0.0, 1.0
            else:
                sx /= slen
                sy /= slen

            # Пересечение луча из центра с прямоугольником экрана (со сжатием)
            tx = half_w / abs(sx) if abs(sx) > 1e-6 else 1e9
            ty = half_h / abs(sy) if abs(sy) > 1e-6 else 1e9
            t = tx if tx < ty else ty

            ix = int(cx + sx * t)
            iy = int(cy + sy * t)

            # Красный кружок с белой обводкой и точкой-«прицелом» внутри
            draw_circle(ix, iy, radius, Color(200, 30, 30, 220))
            draw_circle_lines(ix, iy, radius, WHITE)
            draw_circle(ix, iy, 3, WHITE)
    def _resolve_bullet_hits(self) -> None:
        """Пули игрока: враги (приоритет) → астероиды."""
        ast = self.asteroids
        ship = self.ship
        enemies = self.enemies.enemies

        if not ship.bullets or (ast.count == 0 and not enemies):
            return

        px, py, pz = ast.pos_x, ast.pos_y, ast.pos_z
        radius = ast.radius
        hp = ast.hp
        n = ast.count
        ship_pos = ship.position

        survivors = []
        for b in ship.bullets:
            bx, by, bz = b.position.x, b.position.y, b.position.z
            br = b.radius
            hit = False

            for e in enemies:
                if not e.alive:
                    continue
                dx = bx - e.position.x
                dy = by - e.position.y
                dz = bz - e.position.z
                r = ENEMY_HIT_RADIUS + br
                if dx * dx + dy * dy + dz * dz <= r * r:
                    killed = e.take_damage(b.damage)
                    if killed:
                        self.particles.spawn_explosion(
                            e.position.x, e.position.y, e.position.z, 2.0)
                        self.audio.play_explosion(2.0)
                        self.explosion_count += 1
                    else:
                        self.particles.spawn_explosion(bx, by, bz, 0.4)
                    hit = True
                    break

            if not hit:
                for i in range(n):
                    dx = bx - px[i]
                    dy = by - py[i]
                    dz = bz - pz[i]
                    r = radius[i] * BULLET_HIT_SURF + br
                    if dx * dx + dy * dy + dz * dz <= r * r:
                        hp[i] -= b.damage
                        if hp[i] <= 0:
                            self._on_asteroid_hit(px[i], py[i], pz[i], radius[i])
                            ast.respawn(i, ship_pos)
                        else:
                            self.particles.spawn_explosion(
                                bx, by, bz, radius[i] * SMALL_HIT_SCALE)
                        hit = True
                        break

            if not hit:
                survivors.append(b)

        ship.bullets = survivors

    # ------------------------------------------------------------------
    def _resolve_enemy_bullets(self) -> None:
        """Пули врагов: игрок (урон) + случайные попадания в астероиды."""
        enemies = self.enemies.enemies
        if not enemies:
            return

        ship = self.ship
        ast = self.asteroids
        ship_pos = ship.position

        px, py, pz = ast.pos_x, ast.pos_y, ast.pos_z
        radius = ast.radius
        hp = ast.hp
        n = ast.count

        for e in enemies:
            if not e.bullets:
                continue
            survivors = []
            for b in e.bullets:
                bx, by, bz = b.position.x, b.position.y, b.position.z
                br = b.radius
                hit = False

                # 1) Урон игроку
                dx = bx - ship_pos.x
                dy = by - ship_pos.y
                dz = bz - ship_pos.z
                r = PLAYER_HIT_RADIUS + br
                if dx * dx + dy * dy + dz * dz <= r * r:
                    self.player_hits += 1
                    self.particles.spawn_explosion(bx, by, bz, 0.6)
                    died = ship.take_damage(b.damage)
                    if died:
                        self._trigger_game_over()   # <-- НОВОЕ
                    hit = True

                # 2) Случайное попадание в астероид
                if not hit:
                    for i in range(n):
                        dx = bx - px[i]
                        dy = by - py[i]
                        dz = bz - pz[i]
                        r = radius[i] * BULLET_HIT_SURF + br
                        if dx * dx + dy * dy + dz * dz <= r * r:
                            hp[i] -= b.damage
                            if hp[i] <= 0:
                                self._on_asteroid_hit(
                                    px[i], py[i], pz[i], radius[i])
                                ast.respawn(i, ship_pos)
                            else:
                                self.particles.spawn_explosion(
                                    bx, by, bz,
                                    radius[i] * SMALL_HIT_SCALE)
                            hit = True
                            break

                if not hit:
                    survivors.append(b)

            e.bullets = survivors

