import raylib as rl
import math
from dataclasses import dataclass
from typing import List

class Weapon:
    def __init__(self, fire_rate: float, bullet_speed: float, bullet_color: rl.Color):
        self.fire_rate = fire_rate  # Выстрелов в секунду
        self.bullet_speed = bullet_speed
        self.bullet_color = bullet_color
        self.cooldown = 0.0

    def can_fire(self) -> bool:
        return self.cooldown <= 0

    def fire(self, start_pos: rl.Vector2, direction: rl.Vector2) -> Bullet:
        # Нормализуем направление и задаем скорость
        norm_dir = rl.vector2_normalize(direction)
        velocity = rl.Vector2(norm_dir.x * self.bullet_speed, norm_dir.y * self.bullet_speed)
        self.cooldown = 1.0 / self.fire_rate
        return Bullet(start_pos, velocity, self.bullet_color)

    def update(self, dt: float):
        if self.cooldown > 0:
            self.cooldown -= dt