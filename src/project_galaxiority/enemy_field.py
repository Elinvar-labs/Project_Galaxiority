"""Пул вражеских кораблей: волны, спавн, респавн, рециркуляция."""
import math
import random

from raylibpy import Vector3

from .enemy import Enemy
from .enemy_types import BOSS, HEAVY, LIGHT, MEDIUM


# ======================================================================
#  План волн
# ======================================================================
def _wave_plan(index: int) -> list:
    """Возвращает список EnemyType для волны index (0-based).

    * Каждая 5-я волна — босс (с эскортом).
    * Обычные волны плавно наращивают состав.
    """
    # --- Босс-волны ---
    if (index + 1) % 5 == 0:
        tier = (index + 1) // 5
        bosses = 1 + (tier - 1) // 2          # 1, 1, 2, 2, 3...
        escorts = min(4, tier)                 # 1..4 средних
        return [BOSS] * bosses + [MEDIUM] * escorts

    # --- Обычные волны ---
    light  = min(8, 3 + index // 2)
    medium = min(6, max(0, index - 1))
    heavy  = min(4, max(0, (index - 3) // 2))
    return [LIGHT] * light + [MEDIUM] * medium + [HEAVY] * heavy


class EnemyField:
    """Управляет волнами врагов. Пока волна жива — новая не спавнится."""

    STATE_FIGHTING     = "fighting"
    STATE_INTERMISSION = "intermission"

    __slots__ = ("enemies", "spawn_distance", "wave_index",
                 "wave_state", "wave_delay", "inter_wave_delay")

    def __init__(self, ship_position: Vector3,
                 spawn_distance: float = 200.0,
                 inter_wave_delay: float = 3.0) -> None:
        self.spawn_distance    = spawn_distance
        self.inter_wave_delay  = inter_wave_delay

        self.wave_index  = 0
        self.wave_state  = self.STATE_INTERMISSION
        self.wave_delay  = 1.5                # пауза перед 1-й волной
        self.enemies: list[Enemy] = []

    # ------------------------------------------------------------------
    #  Спавн
    # ------------------------------------------------------------------
    def _random_spawn(self, ship_position: Vector3) -> Vector3:
        """Точка в сферическом слое [0.5R, R] вокруг игрока."""
        r = self.spawn_distance
        for _ in range(20):
            x = ship_position.x + random.uniform(-r, r)
            y = ship_position.y + random.uniform(-r, r)
            z = ship_position.z + random.uniform(-r, r)
            dx = x - ship_position.x
            dy = y - ship_position.y
            dz = z - ship_position.z
            d2 = dx * dx + dy * dy + dz * dz
            if (r * 0.5) ** 2 < d2 < r * r:
                return Vector3(x, y, z)
        return Vector3(ship_position.x + r * 0.7,
                       ship_position.y,
                       ship_position.z)

    def _spawn_wave(self, ship_position: Vector3) -> None:
        plan = _wave_plan(self.wave_index)
        for et in plan:
            pos = self._random_spawn(ship_position)
            self.enemies.append(
                Enemy(pos, random.uniform(-math.pi, math.pi), et)
            )
        self.wave_index += 1
        self.wave_state = self.STATE_FIGHTING

    # ------------------------------------------------------------------
    #  Обновление
    # ------------------------------------------------------------------
    def update(self, dt: float, ship_position: Vector3) -> None:
        # --- Движение живых + рециркуляция слишком далёких ---
        alive = []
        base_recycle = self.spawn_distance * 1.7

        for e in self.enemies:
            if not e.alive:
                continue
            e.update(dt, ship_position)

            r = base_recycle * (2.5 if e.etype.is_boss else 1.0)
            dx = e.position.x - ship_position.x
            dy = e.position.y - ship_position.y
            dz = e.position.z - ship_position.z
            if dx * dx + dy * dy + dz * dz > r * r:
                e.position = self._random_spawn(ship_position)

            alive.append(e)

        self.enemies = alive

        # --- Логика волн ---
        if self.wave_state == self.STATE_FIGHTING:
            if not self.enemies:
                self.wave_state = self.STATE_INTERMISSION
                self.wave_delay = self.inter_wave_delay
        else:  # intermission
            self.wave_delay -= dt
            if self.wave_delay <= 0.0:
                self._spawn_wave(ship_position)

    # ------------------------------------------------------------------
    def draw(self, enemy_models, sphere_model, bullet_model) -> None:
        for e in self.enemies:
            if e.alive:
                e.draw(enemy_models, sphere_model, bullet_model)