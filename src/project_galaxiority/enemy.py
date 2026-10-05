"""Вражеский корабль с простым ИИ: сближение + стрельба по игроку."""
import math
import random

from raylibpy import (MAGENTA, ORANGE, RAD2DEG, RED, WHITE, Vector3,
                      draw_model, rl_pop_matrix, rl_push_matrix,
                      rl_rotatef, rl_translatef)

from .bullet import Bullet
from .settings import PITCH_LIMIT

_cos, _sin, _sqrt = math.cos, math.sin, math.sqrt
_pi = math.pi
_TAU = _pi * 2.0


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def _wrap(a):
    return (a + _pi) % _TAU - _pi


ENEMY_MAX_HP         = 30
ENEMY_FIRE_RATE      = 1.3
ENEMY_BULLET_SPEED   = 42.0
ENEMY_BULLET_LIFE    = 3.5
ENEMY_BULLET_DAMAGE  = 4
ENEMY_BULLET_RADIUS  = 0.08
ENEMY_MAX_SPEED      = 30.0
ENEMY_TURN_RATE      = 0.9
ENEMY_PREFERRED_DIST = 70.0
ENEMY_DIST_BAND      = 25.0
ENEMY_FIRE_CONE      = 0.94
ENEMY_FIRE_RANGE     = 220.0
ENEMY_STRAFE_FACTOR  = 0.25

ENEMY_BAR_OFFSET_Y   = 2.6     # <-- высота полоски над моделью (в мировых метрах)
# Переиспользуемые векторы
_ORIGIN  = Vector3(0.0, 0.0, 0.0)
_UP_Y    = Vector3(0.0, 1.0, 0.0)
_ONE     = Vector3(1.0, 1.0, 1.0)
_FLAME_L = Vector3(-0.35, 0.0, 2.5)
_FLAME_R = Vector3( 0.35, 0.0, 2.5)


class Enemy:
    """Вражеский корабль: летит к игроку, держит дистанцию, стреляет."""

    __slots__ = ("position", "yaw", "pitch", "roll",
                 "fx", "fy", "fz", "ux", "uy", "uz", "rx", "ry", "rz",
                 "hp", "max_hp", "cooldown", "hit_flash",
                 "bullets", "alive",
                 "_strafe_sign", "_strafe_timer")

    def __init__(self, position: Vector3, yaw: float = 0.0) -> None:
        self.position = position
        self.yaw   = yaw
        self.pitch = 0.0
        self.roll  = 0.0

        self.hp     = ENEMY_MAX_HP
        self.max_hp = ENEMY_MAX_HP
        self.cooldown   = random.uniform(0.6, 1.6)  # не стреляет мгновенно
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
        # --- Направление и дистанция до игрока ---
        dx = player_pos.x - self.position.x
        dy = player_pos.y - self.position.y
        dz = player_pos.z - self.position.z
        dsq = dx * dx + dy * dy + dz * dz
        dist = _sqrt(dsq) if dsq > 1e-6 else 1e-6

        # --- Плавный доворот к цели ---
        target_yaw   = math.atan2(-dx, -dz)
        target_pitch = math.asin(_clamp(dy / dist, -1.0, 1.0))

        max_turn = ENEMY_TURN_RATE * dt
        dyaw = _wrap(target_yaw - self.yaw)
        self.yaw   += _clamp(dyaw, -max_turn, max_turn)
        self.pitch += _clamp(target_pitch - self.pitch, -max_turn, max_turn)
        self.pitch  = _clamp(self.pitch, -PITCH_LIMIT, PITCH_LIMIT)

        # Визуальный крен при повороте — «закладывает вираж»
        self.roll += _clamp(-dyaw * 2.0, -1.5, 1.5) * dt
        self.roll  = _wrap(self.roll)

        self._update_basis()

        # --- Продольное движение ---
        if dist > ENEMY_PREFERRED_DIST + ENEMY_DIST_BAND:
            move = ENEMY_MAX_SPEED * dt          # догоняет
        elif dist < ENEMY_PREFERRED_DIST - ENEMY_DIST_BAND:
            move = -ENEMY_MAX_SPEED * 0.5 * dt   # отходит
        else:
            move = ENEMY_MAX_SPEED * 0.15 * dt   # маневрирует

        self.position.x += self.fx * move
        self.position.y += self.fy * move
        self.position.z += self.fz * move

        # --- Боковой стрейф: делает врагов «живее» и сложнее для попадания ---
        self._strafe_timer -= dt
        if self._strafe_timer <= 0.0:
            self._strafe_sign  = -self._strafe_sign
            self._strafe_timer = random.uniform(1.5, 3.0)
        strafe = self._strafe_sign * ENEMY_MAX_SPEED * ENEMY_STRAFE_FACTOR * dt
        self.position.x += self.rx * strafe
        self.position.y += self.ry * strafe
        self.position.z += self.rz * strafe

        # --- Стрельба ---
        self.cooldown -= dt
        if self.hit_flash > 0.0:
            self.hit_flash -= dt

        if (self.cooldown <= 0.0
                and dist < ENEMY_FIRE_RANGE
                and self._aim_ok(dx, dy, dz, dist)):
            self._fire()
            self.cooldown = 1.0 / ENEMY_FIRE_RATE

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
        return dot >= ENEMY_FIRE_CONE

    # ------------------------------------------------------------------
    def _fire(self) -> None:
        # Небольшая неточность — враги не снайперы
        spread = 0.04
        vx = self.fx + random.uniform(-spread, spread)
        vy = self.fy + random.uniform(-spread, spread)
        vz = self.fz + random.uniform(-spread, spread)
        inv = 1.0 / _sqrt(vx * vx + vy * vy + vz * vz)
        vx *= inv; vy *= inv; vz *= inv

        pos = Vector3(
            self.position.x + vx * 1.6,
            self.position.y + vy * 1.6,
            self.position.z + vz * 1.6,
            )
        vel = Vector3(vx * ENEMY_BULLET_SPEED,
                      vy * ENEMY_BULLET_SPEED,
                      vz * ENEMY_BULLET_SPEED)
        self.bullets.append(Bullet(pos, vel, ENEMY_BULLET_LIFE,
                                   ENEMY_BULLET_DAMAGE,
                                   False, ENEMY_BULLET_RADIUS))

    # ------------------------------------------------------------------
    def take_damage(self, amount: int) -> bool:
        """Возвращает True, если враг уничтожен."""
        if not self.alive:
            return False
        self.hp -= amount
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    def draw(self, ship_model, sphere_model, bullet_model) -> None:
        p = self.position
        rl_push_matrix()
        rl_translatef(p.x, p.y, p.z)
        rl_rotatef(self.yaw   * RAD2DEG, 0.0, 1.0, 0.0)
        rl_rotatef(self.pitch * RAD2DEG, 1.0, 0.0, 0.0)
        rl_rotatef(self.roll  * RAD2DEG, 0.0, 0.0, 1.0)

        tint = RED if self.hit_flash > 0.0 else WHITE
        ship_model.draw_ex(_ORIGIN, _UP_Y, 180.0, _ONE, tint)

        # Небольшое постоянное пламя
        flame = 0.10
        draw_model(sphere_model, _FLAME_L, flame, ORANGE)
        draw_model(sphere_model, _FLAME_R, flame, ORANGE)

        rl_pop_matrix()

        # Пульки врага — в мировых координатах (после pop_matrix)
        for b in self.bullets:
            draw_model(bullet_model, b.position, b.radius * 30.0, MAGENTA)