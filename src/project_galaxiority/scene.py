"""Загрузка моделей, текстур и скайбокса."""
from raylibpy import (MATERIAL_MAP_DIFFUSE, TEXTURE_FILTER_BILINEAR,
                      gen_texture_mipmaps, load_model, load_model_from_mesh,
                      load_texture, set_texture_filter)

from .skybox import create_skybox
from .stars import gen_mesh_sphere


class SceneAssets:
    __slots__ = ("sphere_model", "asteroid_model", "ship_model",
                 "sky", "sky_shader")

    def __init__(self) -> None:
        # Универсальный шар — для звёзд, частиц, пламени
        self.sphere_model = load_model_from_mesh(gen_mesh_sphere(1.0, 4, 6))

        # Астероид
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

        # Корабль
        self.ship_model = load_model(
            "assets/models/ships/Striker/glTF/Striker.gltf"
        )

        # Скайбокс
        self.sky, self.sky_shader = create_skybox()