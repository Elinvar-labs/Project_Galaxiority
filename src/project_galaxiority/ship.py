"""Состояние и управление кораблём игрока (с системой вооружения)."""
import math

from raylibpy import (ORANGE, RAD2DEG, RED, WHITE, YELLOW, Vector3,
                      draw_model, rl_pop_matrix, rl_push_matrix,
                      rl_rotatef, rl_translatef)

from .bullet import Bullet
from .settings import (BOOST_MULT, MAX_SPEED, PITCH_LIMIT, ROLL_RATE,
                       THROTTLE_SPEED, TURN_RATE)

_cos, _sin, _clamp = math.cos, math.sin, __import__("raylibpy").clamp
_TAU = math.pi * 2.0

# --- Параметры оружия ---
PRIMARY_FIRE_RATE      = 12.0
PRIMARY_BULLET_SPEED   = 120.0
PRIMARY_BULLET_LIFE    = 2.5
PRIMARY_DAMAGE         = 5

SECONDARY_FIRE_RATE    = 1.5
SECONDARY_BULLET_SPEED = 60.0
SECONDARY_BULLET_LIFE  = 6.0
SECONDARY_DAMAGE       = 40

# --- Параметры живучести ---
PLAYER_MAX_HP          = 100
PLAYER_HIT_FLASH_TIME  = 0.18
PLAYER_RESPAWN_INVULN  = 1.2

# --- Самонаведение ракеты ---
SECONDARY_HOMING       = True
SECONDARY_TURN_RATE    = 3.5      # рад/с (~200°/с) — комфортный радиус разворота

_MUZZLE_LEFT   = Vector3(-0.6,  0.0,  1.8)
_MUZZLE_RIGHT  = Vector3( 0.6,  0.0,  1.8)
_MUZZLE_CENTER = Vector3( 0.0, -0.2,  1.8)

_ORIGIN = Vector3(0.0, 0.0, 0.0)
_UP_Y   = Vector3(0.0, 1.0, 0.0)
_ONE    = Vector3(1.0, 1.0, 1.0)
_FLAME_L = Vector3(-0.35, 0.0, 2.5)
_FLAME_R = Vector3( 0.35, 0.0, 2.5)

def _draw_puff(model, pos: Vector3, ux: float, uy: float, uz: float,
               dist: float, scale: float, color) -> None:
    """Рисует шарик дыма на расстоянии dist ПОЗАДИ точки pos вдоль -u."""
    draw_model(
        model,
        Vector3(pos.x - ux * dist,
                pos.y - uy * dist,
                pos.z - uz * dist),
        scale, color,
    )

class Ship:
    __slots__ = ("position", "yaw", "pitch", "roll",
                 "throttle", "boost", "speed",
                 "fx", "fy", "fz",
                 "ux", "uy", "uz",
                 "rx", "ry", "rz",
                 "primary_cd", "secondary_cd",
                 "bullets",
                 "hp", "max_hp", "hit_flash", "invuln")   # <-- НОВОЕ

    def __init__(self) -> None:
        self.position = Vector3(0.0, -0.5, 0.0)
        self.yaw   = 0.0
        self.pitch = 0.0
        self.roll  = 0.0
        self.throttle = 0.35
        self.boost    = False
        self.speed    = 0.0

        self.fx = self.fy = self.fz = 0.0
        self.ux = self.uy = self.uz = 0.0
        self.rx = self.ry = self.rz = 0.0

        self.primary_cd   = 0.0
        self.secondary_cd = 0.0
        self.bullets: list[Bullet] = []

        # HP                                                       # <-- НОВОЕ
        self.max_hp  = PLAYER_MAX_HP
        self.hp      = PLAYER_MAX_HP
        self.hit_flash = 0.0
        self.invuln    = 0.0

    # ------------------------------------------------------------------
    def take_damage(self, amount: int) -> bool:
        """Возвращает True, если игрок погиб (HP ≤ 0)."""
        if self.invuln > 0.0:
            return False
        self.hp -= amount
        self.hit_flash = PLAYER_HIT_FLASH_TIME
        if self.hp <= 0:
            self.hp = 0
            return True
        return False

    def respawn(self) -> None:
        """Простой респавн на месте со сбросом HP и кратковременной неуязвимостью."""
        self.hp = self.max_hp
        self.hit_flash = 0.0
        self.invuln = PLAYER_RESPAWN_INVULN
        self.throttle = 0.35
        self.bullets.clear()

    # ------------------------------------------------------------------
    def update(self, inp, dt: float, enemies=None) -> None:
        if self.hit_flash > 0.0:
            self.hit_flash -= dt
        if self.invuln > 0.0:
            self.invuln -= dt

        # --- Ориентация ---
        self.yaw   -= inp.stick_x * TURN_RATE * dt
        self.pitch -= inp.stick_y * TURN_RATE * dt
        self.pitch = _clamp(self.pitch, -PITCH_LIMIT, PITCH_LIMIT)
        self.roll += inp.roll_dir * ROLL_RATE * dt
        self.roll  = (self.roll + math.pi) % _TAU - math.pi

        # --- Тяга ---
        self.throttle += inp.throttle_wheel * 0.08
        self.throttle += inp.throttle_axis * THROTTLE_SPEED * dt
        if inp.brake:
            self.throttle -= 2.0 * dt
        self.throttle = _clamp(self.throttle, 0.0, 1.0)
        self.boost = inp.boost

        # --- Базис ---
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

        # --- Перемещение ---
        self.speed = self.throttle * MAX_SPEED * (BOOST_MULT if self.boost else 1.0)
        spd_dt = self.speed * dt
        self.position.x += self.fx * spd_dt
        self.position.y += self.fy * spd_dt
        self.position.z += self.fz * spd_dt

        # --- Стрельба и снаряды ---
        self._update_weapons(inp, dt)
        self._update_bullets(dt, enemies)

    # ------------------------------------------------------------------
    def _update_weapons(self, inp, dt: float) -> None:
        if self.primary_cd   > 0.0: self.primary_cd   -= dt
        if self.secondary_cd > 0.0: self.secondary_cd -= dt

        if getattr(inp, "fire_primary", False) and self.primary_cd <= 0.0:
            self.fire_primary()
            self.primary_cd = 1.0 / PRIMARY_FIRE_RATE

        if getattr(inp, "fire_secondary", False) and self.secondary_cd <= 0.0:
            self.fire_secondary()
            self.secondary_cd = 1.0 / SECONDARY_FIRE_RATE

    def _update_bullets(self, dt: float, enemies=None) -> None:
        alive: list[Bullet] = []
        for b in self.bullets:
            if b.update(dt, enemies):
                alive.append(b)
        self.bullets = alive

    # ------------------------------------------------------------------
    def _muzzle_world(self, local: Vector3) -> Vector3:
        return Vector3(
            self.position.x + self.rx * local.x + self.ux * local.y + self.fx * local.z,
            self.position.y + self.ry * local.x + self.uy * local.y + self.fy * local.z,
            self.position.z + self.rz * local.x + self.uz * local.y + self.fz * local.z,
            )

    def _spawn(self, local_offset: Vector3, speed: float, lifetime: float,
               damage: int, is_missile: bool, radius: float,
               homing: bool = False, turn_rate: float = 0.0) -> None:
        pos = self._muzzle_world(local_offset)
        total = speed + self.speed
        vel = Vector3(self.fx * total, self.fy * total, self.fz * total)
        self.bullets.append(
            Bullet(pos, vel, lifetime, damage, is_missile, radius,
                   homing=homing, turn_rate=turn_rate)
        )
    def fire_primary(self) -> None:
        """Парный залп лазеров с крыльев — без самонаведения."""
        self._spawn(_MUZZLE_LEFT,  PRIMARY_BULLET_SPEED, PRIMARY_BULLET_LIFE,
                    PRIMARY_DAMAGE, False, 0.04)
        self._spawn(_MUZZLE_RIGHT, PRIMARY_BULLET_SPEED, PRIMARY_BULLET_LIFE,
                    PRIMARY_DAMAGE, False, 0.04)

    def fire_secondary(self) -> None:
        """Тяжёлая самонаводящаяся ракета из подфюзеляжного узла."""  # <-- ИЗМЕНЕНО
        self._spawn(_MUZZLE_CENTER, SECONDARY_BULLET_SPEED, SECONDARY_BULLET_LIFE,
                    SECONDARY_DAMAGE, True, 0.08,
                    homing=SECONDARY_HOMING,
                    turn_rate=SECONDARY_TURN_RATE)
    # ------------------------------------------------------------------
    def draw(self, ship_model, sphere_model, bullet_model=None) -> None:
        # --- Сам корабль в локальной системе ---
        p = self.position
        rl_push_matrix()
        rl_translatef(p.x, p.y, p.z)
        rl_rotatef(self.yaw   * RAD2DEG, 0.0, 1.0, 0.0)
        rl_rotatef(self.pitch * RAD2DEG, 1.0, 0.0, 0.0)
        rl_rotatef(self.roll  * RAD2DEG, 0.0, 0.0, 1.0)

        if self.hit_flash > 0.0:
            tint = RED
        elif self.invuln > 0.0 and (int(self.invuln * 12) & 1):
            tint = (255, 255, 255, 90)
        else:
            tint = WHITE

        ship_model.draw_ex(_ORIGIN, _UP_Y, 180.0, _ONE, tint)

        flame = 0.12 + 0.30 * self.throttle
        if self.boost:
            flame *= 1.8
        if flame > 0.05:
            draw_model(sphere_model, _FLAME_L, flame, ORANGE)
            draw_model(sphere_model, _FLAME_R, flame, ORANGE)

        rl_pop_matrix()

        # --- Снаряды в МИРОВЫХ координатах ---
        if bullet_model is not None:
            for b in self.bullets:
                if b.is_missile:
                    # Ракета — компактнее (было radius * 30)
                    draw_model(bullet_model, b.position, b.radius * 17.0, YELLOW)

                    # Дымовой след: 5 сфер с затухающим цветом
                    vx, vy, vz = b.velocity.x, b.velocity.y, b.velocity.z
                    vlen = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
                    ux, uy, uz = vx / vlen, vy / vlen, vz / vlen

                    _draw_puff(bullet_model, b.position, ux, uy, uz,
                               1.6, b.radius * 13.0, (255, 220, 90, 255))
                    _draw_puff(bullet_model, b.position, ux, uy, uz,
                               3.0, b.radius * 11.0, (255, 150, 50, 255))
                    _draw_puff(bullet_model, b.position, ux, uy, uz,
                               4.4, b.radius *  9.0, (200, 100, 40, 255))
                    _draw_puff(bullet_model, b.position, ux, uy, uz,
                               5.8, b.radius *  7.0, (140,  80, 55, 255))
                    _draw_puff(bullet_model, b.position, ux, uy, uz,
                               7.2, b.radius *  5.0, ( 90,  60, 50, 255))
                else:
                    # Лазерный болт — как раньше
                    draw_model(bullet_model, b.position, b.radius * 30.0, RED)