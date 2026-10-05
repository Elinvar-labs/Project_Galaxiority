"""Снаряд (лазерный болт или ракета) в мировом пространстве."""
import math

from raylibpy import Vector3


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


class Bullet:
    __slots__ = ("position", "velocity", "lifetime",
                 "damage", "is_missile", "radius",
                 "homing", "turn_rate", "speed")

    def __init__(self, position: Vector3, velocity: Vector3,
                 lifetime: float, damage: int,
                 is_missile: bool = False, radius: float = 0.08,
                 homing: bool = False, turn_rate: float = 0.0) -> None:
        self.position = position
        self.velocity = velocity
        self.lifetime = lifetime
        self.damage = damage
        self.is_missile = is_missile
        self.radius = radius
        self.homing = homing
        self.turn_rate = turn_rate

        # Запоминаем модуль скорости — при самонаведении держим его постоянным
        vx, vy, vz = velocity.x, velocity.y, velocity.z
        self.speed = math.sqrt(vx * vx + vy * vy + vz * vz)

    # ------------------------------------------------------------------
    def _steer(self, dt: float, enemies) -> None:
        """Поворот вектора скорости к ближайшему живому врагу."""
        px, py, pz = self.position.x, self.position.y, self.position.z

        bx = by = bz = 0.0
        best_d2 = float("inf")
        found = False
        for e in enemies:
            if not e.alive:
                continue
            ex, ey, ez = e.position.x, e.position.y, e.position.z
            dx = ex - px
            dy = ey - py
            dz = ez - pz
            d2 = dx * dx + dy * dy + dz * dz
            if d2 < best_d2:
                best_d2 = d2
                bx, by, bz = dx, dy, dz
                found = True

        if not found:
            return

        # Желаемое направление (нормированное)
        dlen = math.sqrt(bx * bx + by * by + bz * bz) or 1.0
        bx /= dlen; by /= dlen; bz /= dlen

        # Текущее направление
        vx, vy, vz = self.velocity.x, self.velocity.y, self.velocity.z
        vlen = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
        vx /= vlen; vy /= vlen; vz /= vlen

        # Ограничиваем поворот угловой скоростью turn_rate (рад/с)
        dot = _clamp(vx * bx + vy * by + vz * bz, -1.0, 1.0)
        angle = math.acos(dot)
        if angle < 1e-4:
            return
        t = min(1.0, (self.turn_rate * dt) / angle)

        # Линейная интерполяция направления — даёт плавную дугу
        nx = vx + (bx - vx) * t
        ny = vy + (by - vy) * t
        nz = vz + (bz - vz) * t
        nlen = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx /= nlen; ny /= nlen; nz /= nlen

        spd = self.speed
        self.velocity.x = nx * spd
        self.velocity.y = ny * spd
        self.velocity.z = nz * spd

    # ------------------------------------------------------------------
    def update(self, dt: float, enemies=None) -> bool:
        """Двигает снаряд. Возвращает False, если он исчерпал время жизни."""
        if self.homing and enemies:
            self._steer(dt, enemies)

        self.position.x += self.velocity.x * dt
        self.position.y += self.velocity.y * dt
        self.position.z += self.velocity.z * dt
        self.lifetime -= dt
        return self.lifetime > 0.0


# import raylibpy as rl
# from raylibpy import *
# import math
# from dataclasses import dataclass
# from typing import List
#
#
# @dataclass
# class Bullet:
#     """Снаряд (лазерный болт или ракета) в мировом пространстве."""
#     __slots__ = ("position", "velocity", "lifetime",
#                  "damage", "is_missile", "radius")
#
#     def __init__(self, position: Vector3, velocity: Vector3,
#                  lifetime: float, damage: int,
#                  is_missile: bool = False, radius: float = 0.08) -> None:
#         self.position = position
#         self.velocity = velocity
#         self.lifetime = lifetime
#         self.damage = damage
#         self.is_missile = is_missile
#         self.radius = radius
#
#     def update(self, dt: float) -> bool:
#         """Двигает снаряд. Возвращает False, если он исчерпал время жизни."""
#         self.position.x += self.velocity.x * dt
#         self.position.y += self.velocity.y * dt
#         self.position.z += self.velocity.z * dt
#         self.lifetime -= dt
#         return self.lifetime > 0.0
