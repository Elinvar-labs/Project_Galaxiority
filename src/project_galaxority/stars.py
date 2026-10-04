import math
import random

from project_galaxority.settings import *
from raylibpy import *



def random_star_position(center):
    """Random point on a sphere of radius ~FIELD_RADIUS around the center."""
    theta = random.uniform(0.0, 2.0 * math.pi)
    z = random.uniform(-1.0, 1.0)
    r_xy = math.sqrt(max(0.0, 1.0 - z * z))
    dist = random.uniform(FIELD_RADIUS * 0.45, FIELD_RADIUS)
    return Vector3(
        center.x + dist * r_xy * math.cos(theta),
        center.y + dist * r_xy * math.sin(theta),
        center.z + dist * z,
        )


def random_asteroid_position(center):
    """Random point on a sphere of radius ~FIELD_RADIUS around the center."""
    theta = random.uniform(0.0, 2.0 * math.pi)
    z = random.uniform(-1.0, 1.0)
    r_xy = math.sqrt(max(0.0, 1.0 - z * z))
    dist = random.uniform(FIELD_RADIUS * 0.45, FIELD_RADIUS)
    return Vector3(
        center.x + dist * r_xy * math.cos(theta),
        center.y + dist * r_xy * math.sin(theta),
        center.z + dist * z,
        )

def make_star(center):
    shade = random.randint(150, 255)
    blue = min(255, shade + random.randint(0, 40))
    return {
        "pos": random_star_position(center),
        "radius": random.uniform(0.25, 0.85),
        "color": Color(shade, shade, blue, 255),
    }

def make_asteroid(center):
    shade = random.randint(150, 255)
    blue = min(255, shade + random.randint(0, 40))
    return {
        "pos": random_asteroid_position(center),
        "radius": random.uniform(7, 14),
        "color": Color(shade, shade, blue, 255),
    }

