"""Пул вражеских кораблей: спавн, респавн, рециркуляция."""
import math
import random

from raylibpy import Vector3

from .enemy import Enemy


class EnemyField:
    """Список врагов. Их немного (4–6), поэтому ООП-подход уместен."""

    __slots__ = ("enemies", "max_count", "spawn_timer",
                 "spawn_distance", "respawn_delay")

    def __init__(self, count: int, ship_position: Vector3,
                 spawn_distance: float = 200.0,
                 respawn_delay: float = 6.0) -> None:
        self.max_count      = count
        self.spawn_distance = spawn_distance
        self.respawn_delay  = respawn_delay
        self.spawn_timer    = 0.0

        self.enemies: list[Enemy] = [
            self._make_enemy(ship_position) for _ in range(count)
        ]

    # ------------------------------------------------------------------
    def _make_enemy(self, ship_position: Vector3) -> Enemy:
        pos = self._random_spawn(ship_position)
        return Enemy(pos, random.uniform(-math.pi, math.pi))

    def _random_spawn(self, ship_position: Vector3) -> Vector3:
        """Точка в сферическом слое [0.5R, R] вокруг игрока."""
        r = self.spawn_distance
        for _ in range(20):  # rejection sampling
            x = ship_position.x + random.uniform(-r, r)
            y = ship_position.y + random.uniform(-r, r)
            z = ship_position.z + random.uniform(-r, r)
            dx = x - ship_position.x
            dy = y - ship_position.y
            dz = z - ship_position.z
            d2 = dx * dx + dy * dy + dz * dz
            if (r * 0.5) ** 2 < d2 < r * r:
                return Vector3(x, y, z)
        # fallback
        return Vector3(ship_position.x + r * 0.7,
                       ship_position.y,
                       ship_position.z)

    # ------------------------------------------------------------------
    def update(self, dt: float, ship_position: Vector3) -> None:
        alive = []
        recycle_sq = (self.spawn_distance * 1.7) ** 2

        for e in self.enemies:
            if not e.alive:
                continue
            e.update(dt, ship_position)

            # Если враг ушёл слишком далеко — «телепортируем» поближе
            dx = e.position.x - ship_position.x
            dy = e.position.y - ship_position.y
            dz = e.position.z - ship_position.z
            if dx * dx + dy * dy + dz * dz > recycle_sq:
                e.position = self._random_spawn(ship_position)

            alive.append(e)

        self.enemies = alive

        # Респавн взамен убитых (с задержкой)
        if len(self.enemies) < self.max_count:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0.0:
                self.enemies.append(self._make_enemy(ship_position))
                self.spawn_timer = self.respawn_delay

    # ------------------------------------------------------------------
    def draw(self, ship_model, sphere_model, bullet_model) -> None:
        for e in self.enemies:
            if e.alive:
                e.draw(ship_model, sphere_model, bullet_model)