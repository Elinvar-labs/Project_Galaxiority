"""Состояние и управление кораблём игрока."""
import math

from raylibpy import (ORANGE, RAD2DEG, WHITE, Vector3,
                      draw_model, rl_pop_matrix, rl_push_matrix,
                      rl_rotatef, rl_translatef)

from .settings import (BOOST_MULT, MAX_SPEED, PITCH_LIMIT, ROLL_RATE,
                       THROTTLE_SPEED, TURN_RATE)

_cos, _sin, _clamp = math.cos, math.sin, __import__("raylibpy").clamp
_TAU = math.pi * 2.0

# Переиспользуемые векторы
_ORIGIN = Vector3(0.0, 0.0, 0.0)
_UP_Y = Vector3(0.0, 1.0, 0.0)
_ONE = Vector3(1.0, 1.0, 1.0)
_FLAME_L = Vector3(-0.35, 0.0, 2.5)
_FLAME_R = Vector3(0.35, 0.0, 2.5)


class Ship:
    """Позиция/ориентация/тяга + базис (forward/up)."""

    __slots__ = ("position", "yaw", "pitch", "roll",
                 "throttle", "boost", "speed",
                 "fx", "fy", "fz", "ux", "uy", "uz")

    def __init__(self) -> None:
        self.position = Vector3(0.0, -0.5, 0.0)
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.throttle = 0.35
        self.boost = False
        self.speed = 0.0

        self.fx = self.fy = self.fz = 0.0
        self.ux = self.uy = self.uz = 0.0

    def update(self, inp, dt: float) -> None:
        # --- Ориентация ---
        self.yaw -= inp.stick_x * TURN_RATE * dt
        self.pitch -= inp.stick_y * TURN_RATE * dt
        self.pitch = _clamp(self.pitch, -PITCH_LIMIT, PITCH_LIMIT)
        self.roll += inp.roll_dir * ROLL_RATE * dt
        self.roll = (self.roll + math.pi) % _TAU - math.pi

        # --- Тяга ---
        self.throttle += inp.throttle_wheel * 0.08
        self.throttle += inp.throttle_axis * THROTTLE_SPEED * dt
        if inp.brake:
            self.throttle -= 2.0 * dt
        self.throttle = _clamp(self.throttle, 0.0, 1.0)
        self.boost = inp.boost

        # --- Базис ---
        cy, sy = _cos(self.yaw), _sin(self.yaw)
        cp, sp = _cos(self.pitch), _sin(self.pitch)
        cr, sr = _cos(self.roll), _sin(self.roll)

        self.fx = -sy * cp
        self.fy = sp
        self.fz = -cy * cp

        self.ux = -cy * sr + sy * sp * cr
        self.uy = cp * cr
        self.uz = sy * sr + cy * sp * cr

        # --- Перемещение ---
        self.speed = self.throttle * MAX_SPEED * (BOOST_MULT if self.boost else 1.0)
        spd_dt = self.speed * dt
        self.position.x += self.fx * spd_dt
        self.position.y += self.fy * spd_dt
        self.position.z += self.fz * spd_dt

    def draw(self, ship_model, sphere_model) -> None:
        p = self.position
        rl_push_matrix()
        rl_translatef(p.x, p.y, p.z)
        rl_rotatef(self.yaw * RAD2DEG, 0.0, 1.0, 0.0)
        rl_rotatef(self.pitch * RAD2DEG, 1.0, 0.0, 0.0)
        rl_rotatef(self.roll * RAD2DEG, 0.0, 0.0, 1.0)

        ship_model.draw_ex(_ORIGIN, _UP_Y, 180.0, _ONE, WHITE)

        flame = 0.12 + 0.30 * self.throttle
        if self.boost:
            flame *= 1.8
        if flame > 0.05:
            draw_model(sphere_model, _FLAME_L, flame, ORANGE)
            draw_model(sphere_model, _FLAME_R, flame, ORANGE)

        rl_pop_matrix()