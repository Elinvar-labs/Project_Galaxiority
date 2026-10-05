from raylibpy import *


class Input:
    """Reads keyboard, mouse and gamepad input and outputs normalized signals."""

    def __init__(self, screen_width: int, screen_height: int,
                 dead_zone: float = 0.07,
                 gamepad: int = 0):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dead_zone = dead_zone
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

        # --- НОВОЕ: каналы стрельбы (непрерывные, читаются как "зажато") ---
        self.fire_primary = False     # лёгкие лазеры
        self.fire_secondary = False   # ракеты / тяжёлое оружие
        # Разовые события — удобно для запуска ракет "по нажатию", а не зажатию
        self.fire_primary_pressed = False
        self.fire_secondary_pressed = False

    # ------------------------------------------------------------------ #
    def update(self) -> None:
        """Count all input as current frame. Call once per frame."""
        self.gamepad_active = is_gamepad_available(self.gamepad)

        self._read_stick()
        self._read_roll()
        self._read_throttle()
        self._read_modifiers()
        self._read_weapons()          # <-- НОВОЕ

    # ------------------------------------------------------------------ #
    def _read_stick(self) -> None:
        """Mouse as a virtual stick + arrows + gamepad left stick."""
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

    # ------------------------------------------------------------------ #
    #  НОВОЕ: оружие
    # ------------------------------------------------------------------ #
    def _read_weapons(self) -> None:
        """
        Основное оружие:
          - ЛКМ
          - Ctrl (левый или правый)
          - RB на геймпаде
        Вторичное оружие:
          - ПКМ
          - Alt (левый или правый)
          - LB на геймпаде
        """
        primary = is_mouse_button_down(MouseButton.MOUSE_BUTTON_LEFT)
        if (is_key_down(KeyboardKey.KEY_LEFT_CONTROL)
                or is_key_down(KeyboardKey.KEY_RIGHT_CONTROL)):
            primary = True

        secondary = is_mouse_button_down(MouseButton.MOUSE_BUTTON_RIGHT)
        if (is_key_down(KeyboardKey.KEY_LEFT_ALT)
                or is_key_down(KeyboardKey.KEY_RIGHT_ALT)):
            secondary = True

        if self.gamepad_active:
            # TRIGGER_1 = бампер (LB/RB), TRIGGER_2 = аналоговый триггер
            if is_gamepad_button_down(
                    self.gamepad, GamepadButton.GAMEPAD_BUTTON_RIGHT_TRIGGER_1):
                primary = True
            if is_gamepad_button_down(
                    self.gamepad, GamepadButton.GAMEPAD_BUTTON_LEFT_TRIGGER_1):
                secondary = True

        # Разовые события для оружия с "по нажатию" (например, запуск ракеты)
        self.fire_primary_pressed   = primary   and not self.fire_primary
        self.fire_secondary_pressed = secondary and not self.fire_secondary

        self.fire_primary   = primary
        self.fire_secondary = secondary
