from raylibpy import *


class Input:
    """Reads keyboard and mouse input and outputs normalized signals.

    The class does not know about the ship and does not store the game state - it only
    converts “hardware” into logic-friendly values:

        stick_x / stick_y — virtual stick (mouse + arrows), -1..1
        roll_dir — roll direction (A=+1, D=-1), -1..1
        throttle_axis — thrust axis (W=+1, S=-1), -1..1
        throttle_wheel - impulse from the mouse wheel per frame
        brake / boost - Space and Shift flags
        mouse — cursor position (for drawing the crosshair)
        wants_quit — pressed ESC
    """

    def __init__(self, screen_width: int, screen_height: int,
                 dead_zone: float = 0.07):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dead_zone = dead_zone

        self.mouse = Vector2(0.0, 0.0)
        self.stick_x = 0.0
        self.stick_y = 0.0
        self.roll_dir = 0.0
        self.throttle_axis = 0.0
        self.throttle_wheel = 0.0
        self.brake = False
        self.boost = False
        self.wants_quit = False

    # ------------------------------------------------------------------ #
    def update(self) -> None:
        """Count all input as current frame. Call once per frame."""
        self._read_stick()
        self._read_roll()
        self._read_throttle()
        self._read_modifiers()

    # ------------------------------------------------------------------ #
    def _read_stick(self) -> None:
        """Mouse as a virtual stick + duplication of arrows."""
        self.mouse = get_mouse_position()

        # Normalize the cursor position relative to the center of the screen.
        sx = clamp((self.mouse.x - self.screen_width * 0.5)
                   / (self.screen_width * 0.5), -1.0, 1.0)
        sy = clamp((self.mouse.y - self.screen_height * 0.5)
                   / (self.screen_height * 0.5), -1.0, 1.0)

        # Dead zone so that the cursor in the center does not jerk the ship.
        if abs(sx) < self.dead_zone:
            sx = 0.0
        if abs(sy) < self.dead_zone:
            sy = 0.0


        if is_key_down(KeyboardKey.KEY_LEFT):
            sx = -1.0
        if is_key_down(KeyboardKey.KEY_RIGHT):
            sx = 1.0
        if is_key_down(KeyboardKey.KEY_UP):
            sy = -1.0
        if is_key_down(KeyboardKey.KEY_DOWN):
            sy = 1.0

        self.stick_x = sx
        self.stick_y = sy

    # ------------------------------------------------------------------ #
    def _read_roll(self) -> None:
        """Roll: A - left (+1), D - right (-1)."""
        roll = 0.0
        if is_key_down(KeyboardKey.KEY_A):
            roll += 1.0
        if is_key_down(KeyboardKey.KEY_D):
            roll -= 1.0
        self.roll_dir = roll

    # ------------------------------------------------------------------ #
    def _read_throttle(self) -> None:
        """Traction axis (W/S), impulse from the wheel and brake (Space)."""
        axis = 0.0
        if is_key_down(KeyboardKey.KEY_W):
            axis += 1.0
        if is_key_down(KeyboardKey.KEY_S):
            axis -= 1.0
        self.throttle_axis = axis

        # Mouse wheel - “instant” momentum accumulated per frame.
        self.throttle_wheel = get_mouse_wheel_move()

        # We leave the brake as a separate flag: in game logic it
        # subtracts faster than a regular pull and works in conjunction with W/S.
        self.brake = is_key_down(KeyboardKey.KEY_SPACE)

    # ------------------------------------------------------------------ #
    def _read_modifiers(self) -> None:
        """Boost and system keys."""
        self.boost = (is_key_down(KeyboardKey.KEY_LEFT_SHIFT)
                      or is_key_down(KeyboardKey.KEY_RIGHT_SHIFT))
        self.wants_quit = is_key_pressed(KeyboardKey.KEY_ESCAPE)