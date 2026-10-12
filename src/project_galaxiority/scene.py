"""Загрузка моделей, текстур и скайбокса."""
import os

from raylibpy import (MATERIAL_MAP_DIFFUSE, TEXTURE_FILTER_BILINEAR,
                      gen_texture_mipmaps, load_model, load_model_from_mesh,
                      load_texture, set_texture_filter)

from .skybox import create_skybox
from .stars import gen_mesh_sphere


# --- Каталоги с моделями кораблей ---
_SHIPS_DIR = "assets/models/ships"

# Имена папок = имена .gltf-файлов (структура ships/<Name>/glTF/<Name>.gltf)
_ENEMY_MODEL_NAMES = (
    "Striker",      # LIGHT
    "Insurgent",    # MEDIUM
    "Dispatcher",   # HEAVY
    "Zenith",       # BOSS
)


def _ship_gltf_path(name: str) -> str:
    return os.path.join(_SHIPS_DIR, name, "glTF", f"{name}.gltf")


class SceneAssets:
    __slots__ = ("sphere_model", "asteroid_model", "ship_model",
                 "enemy_models",
                 "sky", "sky_shader")

    def __init__(self) -> None:
        # Универсальный шар — для звёзд, частиц, пламени
        self.sphere_model = load_model_from_mesh(gen_mesh_sphere(1.0, 4, 6))

        # --- Астероид ---
        self.asteroid_model = load_model(
            "assets/models/asteroids/remeshed/asteroid_1.glb"
        )
        rock_tex = load_texture(
            "assets/models/asteroids/fixed/asteroid_1_base.png"
        )
        set_texture_filter(rock_tex, TEXTURE_FILTER_BILINEAR)
        gen_texture_mipmaps(rock_tex)
        for i in range(self.asteroid_model.material_count):
            self.asteroid_model.materials[i].maps[MATERIAL_MAP_DIFFUSE].texture = rock_tex

        # --- Корабль игрока ---
        self.ship_model = load_model(_ship_gltf_path("Striker"))

        # --- Модели врагов ---
        # Ключ словаря — имя .gltf-файла (совпадает с EnemyType.model_file)
        self.enemy_models: dict = {}
        for name in _ENEMY_MODEL_NAMES:
            path = _ship_gltf_path(name)
            fname = f"{name}.gltf"
            try:
                if os.path.exists(path):
                    self.enemy_models[fname] = load_model(path)
                else:
                    # Фолбэк — модель игрока, чтобы не падать на отсутствующем файле
                    self.enemy_models[fname] = self.ship_model
            except Exception:
                self.enemy_models[fname] = self.ship_model

        # --- Скайбокс ---
        self.sky, self.sky_shader = create_skybox()