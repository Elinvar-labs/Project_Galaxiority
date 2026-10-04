"""Пул звёзд и астероидов на параллельных массивах.

Массивы вынесены в атрибуты класса, чтобы избежать per-frame
списочных компрехеншенов и сохранить горячий цикл «плоским».
"""


class StarField:
    __slots__ = ("pos_x", "pos_y", "pos_z", "radius", "color",
                 "count", "_random_pos")

    def __init__(self, make_star, random_pos, count: int, ship_position):
        stars = [make_star(ship_position) for _ in range(count)]
        self.pos_x = [s["pos"].x for s in stars]
        self.pos_y = [s["pos"].y for s in stars]
        self.pos_z = [s["pos"].z for s in stars]
        self.radius = [s["radius"] for s in stars]
        self.color = [s["color"] for s in stars]
        self.count = len(stars)
        self._random_pos = random_pos

    def recycle(self, sx: float, sy: float, sz: float,
                field_sq: float, ship_position) -> None:
        px, py, pz = self.pos_x, self.pos_y, self.pos_z
        random_pos = self._random_pos
        for i in range(self.count):
            dx = px[i] - sx
            dy = py[i] - sy
            dz = pz[i] - sz
            if dx * dx + dy * dy + dz * dz > field_sq:
                p = random_pos(ship_position)
                px[i] = p.x
                py[i] = p.y
                pz[i] = p.z


class AsteroidField:
    __slots__ = ("pos_x", "pos_y", "pos_z", "radius", "color",
                 "count", "_random_pos")

    def __init__(self, make_asteroid, random_pos, count: int, ship_position):
        asteroids = [make_asteroid(ship_position) for _ in range(count)]
        self.pos_x = [a["pos"].x for a in asteroids]
        self.pos_y = [a["pos"].y for a in asteroids]
        self.pos_z = [a["pos"].z for a in asteroids]
        self.radius = [a["radius"] for a in asteroids]
        self.color = [a["color"] for a in asteroids]
        self.count = len(asteroids)
        self._random_pos = random_pos

    def update(self, sx: float, sy: float, sz: float,
               field_sq: float, ship_position,
               ship_radius: float, collision_scale: float,
               on_collision) -> None:
        """Рециркуляция + проверка столкновений.

        on_collision(x, y, z, radius) вызывается при попадании;
        астероид тут же респавнится вдали.
        """
        px, py, pz = self.pos_x, self.pos_y, self.pos_z
        radius = self.radius
        random_pos = self._random_pos

        for i in range(self.count):
            dx = px[i] - sx
            dy = py[i] - sy
            dz = pz[i] - sz
            dist_sq = dx * dx + dy * dy + dz * dz

            if dist_sq > field_sq:
                p = random_pos(ship_position)
                px[i] = p.x
                py[i] = p.y
                pz[i] = p.z
                continue

            hit_r = radius[i] * collision_scale + ship_radius
            if dist_sq < hit_r * hit_r:
                on_collision(px[i], py[i], pz[i], radius[i])
                p = random_pos(ship_position)
                px[i] = p.x
                py[i] = p.y
                pz[i] = p.z