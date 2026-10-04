from raylibpy import *


def create_skybox():
    cubemap = load_texture_cubemap(
        load_image("assets/textures/skyboxes/Blue Nebula 2 - 1024x1024_cubemap.png"),
        CubemapLayout.CUBEMAP_LAYOUT_AUTO_DETECT,
    )

    shader = load_shader("assets/shaders/skybox.vs", "assets/shaders/skybox.fs")
    if not is_shader_valid(shader):
        raise RuntimeError("Skybox shader failed to compile")

    shader.locs[ShaderLocationIndex.SHADER_LOC_MAP_CUBEMAP] = \
        get_shader_location(shader, "environmentMap")

    mesh = gen_mesh_cube(1.0, 1.0, 1.0)
    model = load_model_from_mesh(mesh)
    model.materials[0].shader = shader

    model.materials[0].maps[MaterialMapIndex.MATERIAL_MAP_CUBEMAP].texture = cubemap

    return model, shader
