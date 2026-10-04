"""3D-частицы для взрывов астероидов."""
import math
import random

from raylibpy import Color, Vector3, draw_model

_TAU = math.pi * 2.0


class Particle3D:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz",
                 "life", "max_life", "size", "r", "g", "b")

    def __init__(self, x: float, y: float, z: float, scale: float = 1.0):
        theta = random.uniform(0.0, _TAU)
        cosphi = random.uniform(-1.0, 1.0)
        sinphi = math.sqrt(1.0 - cosphi * cosphi)
        spd = random.uniform(3.0, 20.0) * scale

        self.x, self.y, self.z = x, y, z
        self.vx = math.cos(theta) * sinphi * spd
        self.vy = cosphi * spd
        self.vz = math.sin(theta) * sinphi * spd

        self.life = random.uniform(0.5, 1.3)
        self.max_life = self.life
        self.size = random.uniform(0.10, 0.28) * scale

        # бело-жёлтый → оранжевый разброс
        t = random.random()
        self.r = 255
        self.g = int(160 + 95 * t)
        self.b = int(40 + 120 * t * t)


class ParticleSystem:
    """Пул частиц с swap-remove, шар-модель для отрисовки."""

    __slots__ = ("_sphere_model", "_particles", "_tmp")

    def __init__(self, sphere_model):
        self._sphere_model = sphere_model
        self._particles: list[Particle3D] = []
        self._tmp = Vector3(0.0, 0.0, 0.0)

    def spawn_explosion(self, x: float, y: float, z: float, radius: float) -> None:
        scale = 0.6 + radius * 0.6
        count = int(30 + 30 * radius)
        for _ in range(count):
            self._particles.append(Particle3D(x, y, z, scale))

        # Одна крупная центральная вспышка
        flash = Particle3D(x, y, z, scale * 0.2)
        flash.vx = flash.vy = flash.vz = 0.0
        flash.size = 0.5 + radius * 0.5
        flash.life = flash.max_life = 0.22
        flash.r, flash.g, flash.b = 255, 255, 220
        self._particles.append(flash)

    def update(self, dt: float) -> None:
        parts = self._particles
        i = 0
        while i < len(parts):
            p = parts[i]
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.z += p.vz * dt
            drag = 1.0 - 1.8 * dt
            p.vx *= drag
            p.vy *= drag
            p.vz *= drag
            p.life -= dt
            if p.life <= 0.0:
                parts[i] = parts[-1]
                parts.pop()
            else:
                i += 1

    def draw(self) -> None:
        tmp = self._tmp
        model = self._sphere_model
        for p in self._particles:
            t = p.life / p.max_life
            tmp.x, tmp.y, tmp.z = p.x, p.y, p.z
            size = p.size * (0.3 + 0.7 * t)
            col = Color(255, int(p.g * t), int(p.b * t * t), 255)
            draw_model(model, tmp, size, col)