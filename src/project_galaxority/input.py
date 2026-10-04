from raylibpy import *


class Input:
    """Reads keyboard, mouse and gamepad input and outputs normalized signals."""

    def __init__(self, screen_width: int, screen_height: int,
                 dead_zone: float = 0.07,
                 gamepad: int = 0):  # 0 = первый геймпад
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dead_zone = dead_zone

        # Номер геймпада — просто целое число (0, 1, 2, 3)
        self.gamepad = gamepad
        self.gamepad_active = False

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
        # Проверка доступности геймпада по его номеру
        self.gamepad_active = is_gamepad_available(self.gamepad)

        self._read_stick()
        self._read_roll()
        self._read_throttle()
        self._read_modifiers()

    # ------------------------------------------------------------------ #
    # def _read_stick(self) -> None:
    #     """Mouse as a virtual stick + arrows + gamepad left stick."""
    #     self.mouse = get_mouse_position()
    #
    #     sx = clamp((self.mouse.x - self.screen_width * 0.5)
    #                / (self.screen_width * 0.5), -1.0, 1.0)
    #     sy = clamp((self.mouse.y - self.screen_height * 0.5)
    #                / (self.screen_height * 0.5), -1.0, 1.0)
    #
    #     if abs(sx) < self.dead_zone:
    #         sx = 0.0
    #     if abs(sy) < self.dead_zone:
    #         sy = 0.0
    #
    #     if is_key_down(KeyboardKey.KEY_LEFT):
    #         sx = -1.0
    #     if is_key_down(KeyboardKey.KEY_RIGHT):
    #         sx = 1.0
    #     if is_key_down(KeyboardKey.KEY_UP):
    #         sy = -1.0
    #     if is_key_down(KeyboardKey.KEY_DOWN):
    #         sy = 1.0
    #
    #     # Gamepad left stick overrides keyboard/mouse when actually moved.
    #     if self.gamepad_active:
    #         # Передаём self.gamepad (целое число) вместо GamepadNumber
    #         gx = get_gamepad_axis_movement(
    #             self.gamepad, GamepadAxis.GAMEPAD_AXIS_LEFT_X)
    #         gy = get_gamepad_axis_movement(
    #             self.gamepad, GamepadAxis.GAMEPAD_AXIS_LEFT_Y)
    #
    #         if abs(gx) < self.dead_zone:
    #             gx = 0.0
    #         if abs(gy) < self.dead_zone:
    #             gy = 0.0
    #
    #         if gx != 0.0:
    #             sx = gx
    #         if gy != 0.0:
    #             sy = gy
    #
    #     self.stick_x = sx
    #     self.stick_y = sy
    def _read_stick(self) -> None:
        """Mouse as a virtual stick + arrows + gamepad left stick."""
        # позицию мыши всё равно обновляем — её могут читать другие системы
        self.mouse = get_mouse_position()

        if self.gamepad_active:
            gx = get_gamepad_axis_movement(
                self.gamepad, GamepadAxis.GAMEPAD_AXIS_LEFT_X)
            gy = get_gamepad_axis_movement(
                self.gamepad, GamepadAxis.GAMEPAD_AXIS_LEFT_Y)

            if abs(gx) < self.dead_zone:
                gx = 0.0
            if abs(gy) < self.dead_zone:
                gy = 0.0

            sx, sy = gx, gy
        else:
            sx = clamp((self.mouse.x - self.screen_width * 0.5)
                       / (self.screen_width * 0.5), -1.0, 1.0)
            sy = clamp((self.mouse.y - self.screen_height * 0.5)
                       / (self.screen_height * 0.5), -1.0, 1.0)

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
        """Roll: A = left (+1), D = right (-1), right stick X = right (+)."""
        roll = 0.0
        if is_key_down(KeyboardKey.KEY_A):
            roll += 1.0
        if is_key_down(KeyboardKey.KEY_D):
            roll -= 1.0

        if self.gamepad_active:
            rx = get_gamepad_axis_movement(
                self.gamepad, GamepadAxis.GAMEPAD_AXIS_RIGHT_X)
            if abs(rx) < self.dead_zone:
                rx = 0.0
            if rx != 0.0:
                roll = -rx

        self.roll_dir = roll

    # ------------------------------------------------------------------ #
    def _read_throttle(self) -> None:
        """Thrust axis (W/S + RT/LT), wheel impulse and brake."""
        axis = 0.0
        if is_key_down(KeyboardKey.KEY_W):
            axis += 1.0
        if is_key_down(KeyboardKey.KEY_S):
            axis -= 1.0

        if self.gamepad_active:
            rt = get_gamepad_axis_movement(
                self.gamepad, GamepadAxis.GAMEPAD_AXIS_RIGHT_TRIGGER)
            lt = get_gamepad_axis_movement(
                self.gamepad, GamepadAxis.GAMEPAD_AXIS_LEFT_TRIGGER)
            if rt > self.dead_zone:
                axis += rt
            if lt > self.dead_zone:
                axis -= lt
            axis = clamp(axis, -1.0, 1.0)

        self.throttle_axis = axis
        self.throttle_wheel = get_mouse_wheel_move()

        brake = is_key_down(KeyboardKey.KEY_SPACE)
        if self.gamepad_active and is_gamepad_button_down(
                self.gamepad, GamepadButton.GAMEPAD_BUTTON_RIGHT_FACE_RIGHT):
            brake = True
        self.brake = brake

    # ------------------------------------------------------------------ #
    def _read_modifiers(self) -> None:
        """Boost, quit."""
        self.boost = (is_key_down(KeyboardKey.KEY_LEFT_SHIFT)
                      or is_key_down(KeyboardKey.KEY_RIGHT_SHIFT))
        self.wants_quit = is_key_pressed(KeyboardKey.KEY_ESCAPE)

        if self.gamepad_active:
            if is_gamepad_button_down(
                    self.gamepad, GamepadButton.GAMEPAD_BUTTON_RIGHT_FACE_DOWN):
                self.boost = True

            if is_gamepad_button_pressed(
                    self.gamepad, GamepadButton.GAMEPAD_BUTTON_MIDDLE_RIGHT):
                self.wants_quit = True