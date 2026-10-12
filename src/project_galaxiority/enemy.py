"""Вражеский корабль с простым ИИ: сближение + стрельба по игроку."""
import math
import random

from raylibpy import (ORANGE, RAD2DEG, RED, WHITE, Vector3,
                      draw_model, rl_pop_matrix, rl_push_matrix,
                      rl_rotatef, rl_translatef)

from .bullet import Bullet
from .enemy_types import EnemyType, LIGHT
from .settings import PITCH_LIMIT

_cos, _sin, _sqrt = math.cos, math.sin, math.sqrt
_pi = math.pi
_TAU = _pi * 2.0


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def _wrap(a):
    return (a + _pi) % _TAU - _pi


_ORIGIN  = Vector3(0.0, 0.0, 0.0)
_UP_Y    = Vector3(0.0, 1.0, 0.0)
_FLAME_L = Vector3(-0.35, 0.0, 2.5)
_FLAME_R = Vector3( 0.35, 0.0, 2.5)


class Enemy:
    """Вражеский корабль: летит к игроку, держит дистанцию, стреляет."""

    __slots__ = ("position", "yaw", "pitch", "roll",
                 "fx", "fy", "fz", "ux", "uy", "uz", "rx", "ry", "rz",
                 "hp", "max_hp", "cooldown", "hit_flash",
                 "bullets", "alive", "etype",
                 "_strafe_sign", "_strafe_timer")

    def __init__(self, position: Vector3, yaw: float = 0.0,
                 etype: EnemyType = LIGHT) -> None:
        self.etype = etype
        self.position = position
        self.yaw   = yaw
        self.pitch = 0.0
        self.roll  = 0.0

        self.hp     = etype.max_hp
        self.max_hp = etype.max_hp
        self.cooldown   = random.uniform(0.6, 1.6)
        self.hit_flash  = 0.0

        self.bullets: list[Bullet] = []
        self.alive = True

        self._strafe_sign  = 1.0 if random.random() < 0.5 else -1.0
        self._strafe_timer = random.uniform(1.5, 3.0)

        self.fx = self.fy = self.fz = 0.0
        self.ux = self.uy = self.uz = 0.0
        self.rx = self.ry = self.rz = 0.0
        self._update_basis()

    # ------------------------------------------------------------------
    def _update_basis(self) -> None:
        cy, sy = _cos(self.yaw),   _sin(self.yaw)
        cp, sp = _cos(self.pitch), _sin(self.pitch)
        cr, sr = _cos(self.roll),  _sin(self.roll)

        self.fx = -sy * cp
        self.fy =  sp
        self.fz = -cy * cp

        self.ux = -cy * sr + sy * sp * cr
        self.uy =  cp * cr
        self.uz =  sy * sr + cy * sp * cr

        self.rx = self.fy * self.uz - self.fz * self.uy
        self.ry = self.fz * self.ux - self.fx * self.uz
        self.rz = self.fx * self.uy - self.fy * self.ux

    # ------------------------------------------------------------------
    def update(self, dt: float, player_pos: Vector3) -> None:
        et = self.etype

        dx = player_pos.x - self.position.x
        dy = player_pos.y - self.position.y
        dz = player_pos.z - self.position.z
        dsq = dx * dx + dy * dy + dz * dz
        dist = _sqrt(dsq) if dsq > 1e-6 else 1e-6

        # --- Доворот к игроку ---
        target_yaw   = math.atan2(-dx, -dz)
        target_pitch = math.asin(_clamp(dy / dist, -1.0, 1.0))

        max_turn = et.turn_rate * dt
        dyaw = _wrap(target_yaw - self.yaw)
        self.yaw   += _clamp(dyaw, -max_turn, max_turn)
        self.pitch += _clamp(target_pitch - self.pitch, -max_turn, max_turn)
        self.pitch  = _clamp(self.pitch, -PITCH_LIMIT, PITCH_LIMIT)

        self.roll += _clamp(-dyaw * 2.0, -1.5, 1.5) * dt
        self.roll  = _wrap(self.roll)

        self._update_basis()

        # --- Продольное движение ---
        if dist > et.preferred_dist + et.dist_band:
            move = et.speed * dt
        elif dist < et.preferred_dist - et.dist_band:
            move = -et.speed * 0.5 * dt
        else:
            move = et.speed * 0.15 * dt

        self.position.x += self.fx * move
        self.position.y += self.fy * move
        self.position.z += self.fz * move

        # --- Стрейф ---
        self._strafe_timer -= dt
        if self._strafe_timer <= 0.0:
            self._strafe_sign  = -self._strafe_sign
            self._strafe_timer = random.uniform(1.5, 3.0)
        strafe = self._strafe_sign * et.speed * et.strafe_factor * dt
        self.position.x += self.rx * strafe
        self.position.y += self.ry * strafe
        self.position.z += self.rz * strafe

        # --- Стрельба ---
        self.cooldown -= dt
        if self.hit_flash > 0.0:
            self.hit_flash -= dt

        if (self.cooldown <= 0.0
                and dist < et.fire_range
                and self._aim_ok(dx, dy, dz, dist)):
            self._fire()
            self.cooldown = 1.0 / et.fire_rate

        # --- Пульки ---
        alive = []
        for b in self.bullets:
            if b.update(dt):
                alive.append(b)
        self.bullets = alive

    # ------------------------------------------------------------------
    def _aim_ok(self, dx, dy, dz, dist) -> bool:
        inv = 1.0 / dist
        dot = (self.fx * dx + self.fy * dy + self.fz * dz) * inv
        return dot >= self.etype.fire_cone

    # ------------------------------------------------------------------
    def _fire(self) -> None:
        et = self.etype
        count = et.muzzle_count
        spread = et.spread

        for k in range(count):
            # Веер: сдвигаем направление по правому базису
            if count > 1:
                side = (k - (count - 1) * 0.5) * spread * 2.0
            else:
                side = 0.0

            vx = self.fx + side * self.rx + random.uniform(-spread, spread)
            vy = self.fy + side * self.ry + random.uniform(-spread, spread)
            vz = self.fz + side * self.rz + random.uniform(-spread, spread)
            inv = 1.0 / _sqrt(vx * vx + vy * vy + vz * vz)
            vx *= inv; vy *= inv; vz *= inv

            pos = Vector3(
                self.position.x + vx * et.muzzle_offset,
                self.position.y + vy * et.muzzle_offset,
                self.position.z + vz * et.muzzle_offset,
                )
            vel = Vector3(vx * et.bullet_speed,
                          vy * et.bullet_speed,
                          vz * et.bullet_speed)
            self.bullets.append(Bullet(pos, vel, et.bullet_life,
                                       et.bullet_damage, False,
                                       et.bullet_radius))

    # ------------------------------------------------------------------
    def take_damage(self, amount: int) -> bool:
        if not self.alive:
            return False
        self.hp -= amount
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    def draw(self, enemy_models, sphere_model, bullet_model) -> None:
        # Выбираем модель по типу врага
        ship_model = enemy_models.get(self.etype.model_file)
        if ship_model is None:
            return

        p = self.position
        s = self.etype.model_scale

        rl_push_matrix()
        rl_translatef(p.x, p.y, p.z)
        rl_rotatef(self.yaw   * RAD2DEG, 0.0, 1.0, 0.0)
        rl_rotatef(self.pitch * RAD2DEG, 1.0, 0.0, 0.0)
        rl_rotatef(self.roll  * RAD2DEG, 0.0, 0.0, 1.0)

        tint = RED if self.hit_flash > 0.0 else WHITE
        scale_vec = Vector3(s, s, s)
        ship_model.draw_ex(_ORIGIN, _UP_Y, 180.0, scale_vec, tint)

        flame = 0.10 * s
        draw_model(sphere_model,
                   Vector3(_FLAME_L.x * s, _FLAME_L.y * s, _FLAME_L.z * s),
                   flame, ORANGE)
        draw_model(sphere_model,
                   Vector3(_FLAME_R.x * s, _FLAME_R.y * s, _FLAME_R.z * s),
                   flame, ORANGE)

        rl_pop_matrix()

        for b in self.bullets:
            draw_model(bullet_model, b.position,
                       b.radius * 30.0, self.etype.bullet_color)