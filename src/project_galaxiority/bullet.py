import raylibpy as rl
from raylibpy import *
import math
from dataclasses import dataclass
from typing import List


@dataclass
class Bullet:
    """Снаряд (лазерный болт или ракета) в мировом пространстве."""
    __slots__ = ("position", "velocity", "lifetime",
                 "damage", "is_missile", "radius")

    def __init__(self, position: Vector3, velocity: Vector3,
                 lifetime: float, damage: int,
                 is_missile: bool = False, radius: float = 0.08) -> None:
        self.position = position
        self.velocity = velocity
        self.lifetime = lifetime
        self.damage = damage
        self.is_missile = is_missile
        self.radius = radius

    def update(self, dt: float) -> bool:
        """Двигает снаряд. Возвращает False, если он исчерпал время жизни."""
        self.position.x += self.velocity.x * dt
        self.position.y += self.velocity.y * dt
        self.position.z += self.velocity.z * dt
        self.lifetime -= dt
        return self.lifetime > 0.0
