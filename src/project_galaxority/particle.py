class Particle:
    def __init__(self, x, y):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(60, 320)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.4, 1.0)
        self.max_life = self.life
        self.size = random.uniform(1.5, 4.0)
        # цвет от жёлто-белого к красному
        self.base = rl.Color(255, random.randint(140, 230), random.randint(0, 60), 255)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        # трение + небольшое притяжение вниз для "гравитационного" вида
        self.vx *= (1 - 1.2 * dt)
        self.vy *= (1 - 1.2 * dt)
        self.life -= dt

    def draw(self):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        c = rl.Color(self.base.r, self.base.g, self.base.b, int(255 * t))
        r = self.size * t + 0.5
        rl.draw_circle(int(self.x), int(self.y), r, c)

    @property
    def alive(self):
        return self.life > 0