"""Оркестратор сцены и главный цикл."""
from raylibpy import (BLACK, WHITE, Vector3,
                      begin_drawing, begin_mode3d, clear_background,
                      close_window, draw_model, end_drawing, end_mode3d,
                      get_frame_time, init_window, load_music_stream,
                      play_music_stream, rl_disable_backface_culling,
                      rl_disable_depth_mask, rl_enable_backface_culling,
                      rl_enable_depth_mask, set_target_fps,
                      update_music_stream, window_should_close,
                      init_audio_device, toggle_fullscreen)

from .camera import ChaseCamera, follow_ship
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


class Game:
    __slots__ = ("assets", "input", "camera",
                 "ship", "stars", "asteroids",
                 "particles", "hud",
                 "explosion_count", "audio",
                 "_origin", "_star_tmp", "_aster_tmp",
                 "_field_sq")

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

        self.particles = ParticleSystem(self.assets.sphere_model)
        self.hud = HUD(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.explosion_count = 0
        self.audio = AudioManager()

        # Reusable Vector3
        self._origin = Vector3(0.0, 0.0, 0.0)
        self._star_tmp = Vector3(0.0, 0.0, 0.0)
        self._aster_tmp = Vector3(0.0, 0.0, 0.0)

        self._field_sq = FIELD_RADIUS * FIELD_RADIUS

        # toggle_fullscreen()

    # ------------------------------------------------------------------
    def _on_asteroid_hit(self, x, y, z, radius) -> None:
        self.particles.spawn_explosion(x, y, z, radius)
        self.audio.play_explosion(radius)
        self.explosion_count += 1

    # ------------------------------------------------------------------
    def run(self) -> None:
        ship = self.ship

        while not window_should_close():
            dt = get_frame_time()
            if dt > 0.05:
                dt = 0.05


            self.audio.update(dt, ship)

            # --- INPUT ---
            self.input.update()
            if self.input.wants_quit:
                break

            # --- SHIP ---
            ship.update(self.input, dt)

            # --- FIELDS ---
            p = ship.position
            self.stars.recycle(p.x, p.y, p.z, self._field_sq, p)
            self.asteroids.update(
                p.x, p.y, p.z, self._field_sq, p,
                SHIP_COLLISION_RADIUS, ASTEROID_COLLISION_SCALE,
                self._on_asteroid_hit,
            )

            # --- PARTICLES ---
            self.particles.update(dt)

            # --- CAMERA ---
            follow_ship(self.camera, ship, dt)

            # --- RENDER ---
            self._render()

        self.audio.close()
        close_window()

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

        # Ship + flame
        ship.draw(assets.ship_model, sphere)

        # Explosion particles
        self.particles.draw()

        end_mode3d()

        # HUD
        self.hud.draw(ship, self.input, self.explosion_count)
        end_drawing()
