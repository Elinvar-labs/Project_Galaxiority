"""Отрисовка HUD: текст, шкала тяги, ring, прицел."""
from raylibpy import (Color, GREEN, ORANGE, RAYWHITE,
                      draw_circle, draw_fps, draw_line, draw_rectangle,
                      draw_rectangle_lines, draw_text)


class HUD:
    __slots__ = ("screen_w", "screen_h",
                 "_text", "_green", "_orange",
                 "_stick_ring", "_bar_bg", "_reticle",
                 "_bar_x", "_bar_y", "_bar_w", "_bar_h")

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h

        self._text = RAYWHITE
        self._green = GREEN
        self._orange = ORANGE
        self._stick_ring = Color(255, 255, 255, 25)
        self._bar_bg = Color(40, 40, 40, 200)
        self._reticle = Color(255, 255, 255, 170)

        self._bar_x = screen_w - 46
        self._bar_y = 140
        self._bar_w = 22
        self._bar_h = 420

    def draw(self, ship, input_, explosion_count: int) -> None:
        text = self._text
        green = self._green
        orange = self._orange

        draw_text("Mouse = virtual stick (steer)   Arrows = steer too", 10, 10, 20, text)
        draw_text("A / D = roll    W / S or Wheel = throttle", 10, 36, 20, text)
        draw_text("Shift = boost   Space = brake", 10, 62, 20, text)
        draw_text(f"Speed: {ship.speed:6.1f}", 10, 96, 20,
                  orange if ship.boost else green)
        draw_text(f"Throttle: {ship.throttle * 100:3.0f}%", 10, 122, 20, text)
        draw_text(f"Roll: {ship.roll * 57.29578:6.1f} deg", 10, 148, 20, text)
        draw_text(f"Explosions: {explosion_count}", 10, 174, 20, orange)

        # Вертикальная шкала тяги
        bar_x, bar_y, bar_w, bar_h = self._bar_x, self._bar_y, self._bar_w, self._bar_h
        draw_rectangle(bar_x, bar_y, bar_w, bar_h, self._bar_bg)
        fill_h = int(bar_h * ship.throttle)
        draw_rectangle(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h,
                       orange if ship.boost else green)
        draw_rectangle_lines(bar_x, bar_y, bar_w, bar_h, text)

        # Центральный «стик»
        cx = self.screen_w // 2
        cy = self.screen_h // 2
        draw_circle(cx, cy, 42, self._stick_ring)

        # Прицел у мыши
        mx = int(input_.mouse.x)
        my = int(input_.mouse.y)
        ret = self._reticle
        draw_line(mx - 18, my, mx - 6, my, ret)
        draw_line(mx + 6, my, mx + 18, my, ret)
        draw_line(mx, my - 18, mx, my - 6, ret)
        draw_line(mx, my + 6, mx, my + 18, ret)
        draw_circle(mx, my, 2, ret)

        draw_fps(10, self.screen_h - 30)