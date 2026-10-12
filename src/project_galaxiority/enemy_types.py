"""Конфигурации типов врагов: лёгкий, средний, тяжёлый, босс."""
from dataclasses import dataclass

from raylibpy import Color, MAGENTA, ORANGE, RED, YELLOW


@dataclass(frozen=True)
class EnemyType:
    name: str
    max_hp: int
    speed: float
    turn_rate: float
    fire_rate: float
    bullet_speed: float
    bullet_life: float
    bullet_damage: int
    bullet_radius: float
    bullet_color: Color
    preferred_dist: float
    dist_band: float
    fire_cone: float
    fire_range: float
    strafe_factor: float
    hit_radius: float
    model_scale: float
    muzzle_offset: float
    muzzle_count: int
    spread: float
    score: int
    is_boss: bool = False
    model_file: str = ""


# --- Лёгкий: быстрый, слабый, одиночные выстрелы ---
LIGHT = EnemyType(
    name="Лёгкий",
    max_hp=30, speed=30.0, turn_rate=0.9,
    fire_rate=1.3, bullet_speed=42.0, bullet_life=3.5,
    bullet_damage=4, bullet_radius=0.08, bullet_color=MAGENTA,
    preferred_dist=70.0, dist_band=25.0,
    fire_cone=0.94, fire_range=220.0,
    strafe_factor=0.25, hit_radius=1.4,
    model_scale=1.0, muzzle_offset=1.6,
    muzzle_count=1, spread=0.04,
    score=100,
    model_file="Striker.gltf",
)

# --- Средний: баланс, двойной залп ---
MEDIUM = EnemyType(
    name="Средний",
    max_hp=90, speed=24.0, turn_rate=0.7,
    fire_rate=1.8, bullet_speed=50.0, bullet_life=4.0,
    bullet_damage=6, bullet_radius=0.10, bullet_color=ORANGE,
    preferred_dist=90.0, dist_band=30.0,
    fire_cone=0.95, fire_range=260.0,
    strafe_factor=0.30, hit_radius=1.7,
    model_scale=1.5, muzzle_offset=1.9,
    muzzle_count=2, spread=0.05,
    score=250,
    model_file="Insurgent.gltf",
)

# --- Тяжёлый: медленный, крепкий, веерный огонь ---
HEAVY = EnemyType(
    name="Тяжёлый",
    max_hp=240, speed=18.0, turn_rate=0.5,
    fire_rate=1.0, bullet_speed=38.0, bullet_life=4.5,
    bullet_damage=10, bullet_radius=0.16, bullet_color=RED,
    preferred_dist=110.0, dist_band=35.0,
    fire_cone=0.96, fire_range=300.0,
    strafe_factor=0.15, hit_radius=2.3,
    model_scale=2.2, muzzle_offset=2.2,
    muzzle_count=3, spread=0.08,
    score=600,
    model_file="Dispatcher.gltf",
)

# --- Босс-гигант: очень крепкий, широкий веер ---
BOSS = EnemyType(
    name="Босс-гигант",
    max_hp=1800, speed=12.0, turn_rate=0.35,
    fire_rate=2.5, bullet_speed=45.0, bullet_life=5.0,
    bullet_damage=12, bullet_radius=0.20, bullet_color=YELLOW,
    preferred_dist=140.0, dist_band=50.0,
    fire_cone=0.97, fire_range=420.0,
    strafe_factor=0.10, hit_radius=4.5,
    model_scale=5.0, muzzle_offset=3.5,
    muzzle_count=5, spread=0.18,
    score=5000, is_boss=True,
    model_file="Zenith.gltf",
)