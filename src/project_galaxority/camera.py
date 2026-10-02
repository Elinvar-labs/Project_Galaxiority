import math
from raylibpy import *

from settings import CAM_HEIGHT, CAM_DISTANCE, CAM_LOOK_AHEAD


class ChaseCamera:
    """A camera that follows the ship and rolls with it.

    The position is smoothed exponentially to prevent the camera from “jerking.”
    """
    def __init__(self,
                 height: float = CAM_HEIGHT,
                 distance: float = CAM_DISTANCE,
                 look_ahead: float = CAM_LOOK_AHEAD,
                 fovy: float = 60.0,
                 smoothing: float = 14.0):
        self.height = height # upward offset from the ship
        self.distance = distance # lag behind the ship
        self.look_ahead = look_ahead # how far to look ahead of the ship
        self.smoothing = smoothing # exponential smoothing factor (1/s)

        self.camera = Camera3D()
        self.camera.position = Vector3(0.0, self.height, self.distance)
        self.camera.target = Vector3(0.0, 0.0, -self.look_ahead)
        self.camera.up = Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = fovy
        self.camera.projection = CameraProjection.CAMERA_PERSPECTIVE

    # ------------------------------------------------------------------ #
    def update(self, delta: float,
               ship_position: Vector3,
               forward: Vector3,
               up: Vector3) -> Camera3D:
        """Update the camera to the current state of the ship.

        ship_position — world position of the ship
        forward — forward vector of the ship
        up — the “up” vector of the ship (the camera rolls with it)
        """
        # Desired position: behind and above the ship in its local system.
        desired_x = ship_position.x - forward.x * self.distance + up.x * self.height
        desired_y = ship_position.y - forward.y * self.distance + up.y * self.height
        desired_z = ship_position.z - forward.z * self.distance + up.z * self.height

        # Exponential smoothing, independent of FPS.
        k = 1.0 - math.exp(-self.smoothing * delta)
        self.camera.position.x += (desired_x - self.camera.position.x) * k
        self.camera.position.y += (desired_y - self.camera.position.y) * k
        self.camera.position.z += (desired_z - self.camera.position.z) * k

        # The point of view is slightly ahead of the ship.
        self.camera.target = Vector3(
            ship_position.x + forward.x * self.look_ahead,
            ship_position.y + forward.y * self.look_ahead,
            ship_position.z + forward.z * self.look_ahead,
            )

        # The camera rolls along with the ship.
        self.camera.up = up
        return self.camera

    # ------------------------------------------------------------------ #
    def snap_to(self, ship_position: Vector3,
                forward: Vector3,
                up: Vector3) -> None:
        """Instantly place the camera in the right place, without smoothing.

        Useful when spawning/teleporting a ship so that the camera does not “catch up”.
        """
        self.camera.position = Vector3(
            ship_position.x - forward.x * self.distance + up.x * self.height,
            ship_position.y - forward.y * self.distance + up.y * self.height,
            ship_position.z - forward.z * self.distance + up.z * self.height,
            )
        self.camera.target = Vector3(
            ship_position.x + forward.x * self.look_ahead,
            ship_position.y + forward.y * self.look_ahead,
            ship_position.z + forward.z * self.look_ahead,
            )
        self.camera.up = up