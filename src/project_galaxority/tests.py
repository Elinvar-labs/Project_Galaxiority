import pytest
from raylibpy import Vector3

from project_galaxority.camera import ChaseCamera
from project_galaxority.input import Input
from project_galaxority.utils import clamp

@pytest.mark.parametrize("value, expected", [
    (0, 0),
    (-10, 0),
    (10, 10),
    (15, 10)
])
def test_clamp(value, expected):
    assert clamp(value, 0, 10) == expected

def test_input():
    """Test the input class."""
    input_instance = Input(screen_width=100, screen_height=100)
    assert input_instance.stick_x == 0.0
    assert input_instance.stick_y == 0.0
    assert input_instance.roll_dir == 0.0
    assert input_instance.throttle_axis == 0.0
    assert input_instance.throttle_wheel == 0.0
    assert input_instance.brake == False
    assert input_instance.boost == False
    assert input_instance.wants_quit == False



@pytest.fixture
def camera():
    return ChaseCamera()


def test_chase_camera(camera):
    ship_position = Vector3(0, 0, 0)
    forward = Vector3(1, 0, 0)
    up = Vector3(0, 1, 0)

    # Update the camera with a ship position and forward vector.
    camera.update(0.1, ship_position, forward, up)

    # Assert that the camera's position is updated correctly.
    assert camera.camera.target == Vector3(20.00, 0.0, 0.0)
    assert camera.camera.up == Vector3(0, 1, 0)

def test_input():
    """Test the input class."""
    input_instance = Input(screen_width=100, screen_height=100)
    assert input_instance.stick_x == 0.0
    assert input_instance.stick_y == 0.0
    assert input_instance.roll_dir == 0.0
    assert input_instance.throttle_axis == 0.0
    assert input_instance.throttle_wheel == 0.0
    assert input_instance.brake == False
    assert input_instance.boost == False
    assert input_instance.wants_quit == False



@pytest.fixture
def center():
    return Vector3(0, 0, 0)


def test_make_star(center):
    from project_galaxority.stars import make_star
    star = make_star(center)
    assert isinstance(star, dict)
    assert star["pos"] is not None
    assert star["radius"] >= 0.25
    assert star["color"].r >= 150 and star["color"].r <= 255
    assert star["color"].g >= 150 and star["color"].g <= 255
    assert star["color"].b >= 150 and star["color"].b <= 255

def test_make_asteroid(center):
    from project_galaxority import make_asteroid
    star = make_asteroid(center)
    assert isinstance(star, dict)
    assert star["pos"] is not None
    assert star["color"].r >= 150 and star["color"].r <= 255
    assert star["color"].g >= 150 and star["color"].g <= 255
    assert star["color"].b >= 150 and star["color"].b <= 255

