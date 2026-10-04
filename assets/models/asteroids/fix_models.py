"""
fix_model.py — универсальный фиксер 3D-моделей для raylib-py.
Исправленная версия с учётом нового API trimesh (nondegenerate_faces / unique_faces).
"""

import sys
import shutil
from pathlib import Path

import numpy as np
import trimesh


# ============================================================
# Утилиты
# ============================================================

def log(msg: str, level: str = "INFO"):
    prefix = {
        "INFO":    "[*]",
        "OK":      "[+]",
        "WARN":    "[!]",
        "ERROR":   "[x]",
        "STEP":    "[>]",
    }.get(level, "[*]")
    print(f"{prefix} {msg}")


# ============================================================
# 1. Загрузка
# ============================================================

def load_mesh(path: Path) -> trimesh.Trimesh:
    """Загружает любой формат и приводит к единому Trimesh."""
    log(f"Загружаю: {path.name}", "STEP")
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    loaded = trimesh.load(str(path), force=None, process=False)

    if isinstance(loaded, trimesh.Scene):
        log(f"Загружена сцена, геометрий: {len(loaded.geometry)}")
        meshes = []
        for name, geom in loaded.geometry.items():
            if isinstance(geom, trimesh.Trimesh):
                meshes.append(geom)
                log(f"  · {name}: {len(geom.vertices)} v, {len(geom.faces)} f")
        if not meshes:
            raise ValueError("В сцене нет ни одного меша")
        mesh = trimesh.util.concatenate(meshes)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Неизвестный тип: {type(loaded)}")

    log(f"Итоговый меш: {len(mesh.vertices)} вершин, {len(mesh.faces)} граней", "OK")
    return mesh


# ============================================================
# 2. Очистка
# ============================================================

def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    log("Чищу меш...", "STEP")

    # 2.1. Триангуляция (raylib не любит n-gon'ы и квады)
    if mesh.faces.shape[1] != 3:
        log("  · не треугольный — пытаюсь разбить грани")
        try:
            mesh = mesh.subdivide()
            log("  · разбиение выполнено")
        except Exception as e:
            log(f"  · не удалось разбить грани: {e}", "WARN")
    else:
        log("  · уже треугольный")

    # 2.2. Удаление NaN / inf в вершинах
    v = np.asarray(mesh.vertices, dtype=np.float64)
    bad = ~np.isfinite(v).all(axis=1)
    if bad.any():
        log(f"  · найдено {bad.sum()} битых вершин — чищу", "WARN")
        mesh.update_vertices(~bad)

    # 2.3. Вырожденные и дублирующиеся грани (НОВЫЙ API trimesh)
    before = len(mesh.faces)
    # nondegenerate_faces() -> маска для удаления вырожденных граней
    # unique_faces() -> маска для удаления дублирующихся граней
    # update_faces() применяет маску (in-place)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    removed = before - len(mesh.faces)
    if removed:
        log(f"  · удалено {removed} вырожденных/дублирующихся граней")
    else:
        log("  · вырожденных и дублирующихся граней не найдено")

    # 2.4. Вершинные цвета — в топку
    try:
        vc = getattr(mesh.visual, "vertex_colors", None)
        if vc is not None:
            mesh.visual.vertex_colors = None
            log("  · вершинные цвета удалены")
    except Exception as e:
        log(f"  · vertex_colors: {e}", "WARN")

    # 2.5. Нормали — гарантируем наличие
    if mesh.vertex_normals is None or len(mesh.vertex_normals) != len(mesh.vertices):
        log("  · генерирую нормали")
        _ = mesh.vertex_normals

    # 2.6. UV — если нет, генерируем простую сферическую развёртку
    if not hasattr(mesh.visual, "uv") or mesh.visual.uv is None \
            or len(mesh.visual.uv) != len(mesh.vertices):
        log("  · генерирую UV (сферическая развёртка)")
        mesh.visual.uv = _spherical_uv(mesh.vertices)

    log(f"После очистки: {len(mesh.vertices)} v, {len(mesh.faces)} f", "OK")
    return mesh


def _spherical_uv(vertices: np.ndarray) -> np.ndarray:
    """Простая сферическая UV-развёртка — на случай, если UV потеряны."""
    v = vertices - vertices.mean(axis=0)
    r = np.linalg.norm(v, axis=1, keepdims=True)
    r[r == 0] = 1.0
    n = v / r
    u = 0.5 + np.arctan2(n[:, 2], n[:, 0]) / (2.0 * np.pi)
    w = 0.5 - np.arcsin(np.clip(n[:, 1], -1.0, 1.0)) / np.pi
    return np.column_stack([u, w]).astype(np.float32)


# ============================================================
# 3. Экспорт: безопасный OBJ (без материалов)
# ============================================================

def export_safe_obj(mesh: trimesh.Trimesh, out_path: Path):
    """
    Пишем OBJ вручную. Никаких mtllib/usemtl/groups/smoothing.
    Только: v, vt, vn, f — то, что гарантированно ест tinyobjloader.
    """
    log(f"Экспорт безопасного OBJ: {out_path.name}", "STEP")

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    uvs = np.asarray(mesh.visual.uv, dtype=np.float64)
    norms = np.asarray(mesh.vertex_normals, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)

    if len(uvs) != len(verts):
        uvs = np.zeros((len(verts), 2), dtype=np.float64)
    if len(norms) != len(verts):
        norms = np.zeros((len(verts), 3), dtype=np.float64)

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# raylib-safe OBJ generated by fix_model.py\n")
        f.write(f"# vertices={len(verts)} faces={len(faces)}\n")

        for x, y, z in verts:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")

        for u, w in uvs:
            f.write(f"vt {u:.6f} {w:.6f}\n")

        for nx, ny, nz in norms:
            f.write(f"vn {nx:.6f} {ny:.6f} {nz:.6f}\n")

        for a, b, c in faces:
            ia, ib, ic = a + 1, b + 1, c + 1
            f.write(f"f {ia}/{ia}/{ia} {ib}/{ib}/{ib} {ic}/{ic}/{ic}\n")

    size_kb = out_path.stat().st_size / 1024
    log(f"  · записано {len(verts)} v, {len(faces)} f, {size_kb:.1f} KB", "OK")


# ============================================================
# 4. Экспорт: безопасный GLB
# ============================================================

def export_safe_glb(mesh: trimesh.Trimesh, out_path: Path):
    """GLB без материалов, только геометрия + UV + нормали."""
    log(f"Экспорт безопасного GLB: {out_path.name}", "STEP")

    export_mesh = trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices),
        faces=np.asarray(mesh.faces),
        vertex_normals=np.asarray(mesh.vertex_normals),
        process=False,
    )
    export_mesh.visual = trimesh.visual.TextureVisuals(
        uv=np.asarray(mesh.visual.uv)
    )

    export_mesh.export(str(out_path), file_type="glb")
    size_kb = out_path.stat().st_size / 1024
    log(f"  · записано, {size_kb:.1f} KB", "OK")


# ============================================================
# 5. Минимальный тестовый OBJ
# ============================================================

def write_minimal_obj(out_dir: Path):
    """Треугольник для диагностики: если raylib падает и на нём — дело не в модели."""
    p = out_dir / "minimal_test.obj"
    p.write_text(
        "# minimal triangle for raylib diagnostics\n"
        "v 0.0 0.0 0.0\n"
        "v 1.0 0.0 0.0\n"
        "v 0.0 1.0 0.0\n"
        "vt 0.0 0.0\n"
        "vt 1.0 0.0\n"
        "vt 0.0 1.0\n"
        "vn 0.0 0.0 1.0\n"
        "vn 0.0 0.0 1.0\n"
        "vn 0.0 0.0 1.0\n"
        "f 1/1/1 2/2/2 3/3/3\n",
        encoding="utf-8",
    )
    log(f"Тестовый треугольник: {p.name}", "OK")


# ============================================================
# main
# ============================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = Path(sys.argv[1]).resolve()
    out_dir = (Path(sys.argv[2]).resolve() if len(sys.argv) > 2
               else src.parent / f"{src.stem}_fixed")
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"Вход:  {src}")
    log(f"Выход: {out_dir}")
    print("-" * 64)

    try:
        raw = load_mesh(src)
        clean = clean_mesh(raw)
        export_safe_obj(clean, out_dir / f"{src.stem}.obj")
        try:
            export_safe_glb(clean, out_dir / f"{src.stem}.glb")
        except Exception as e:
            log(f"GLB пропущен: {e}", "WARN")
        write_minimal_obj(out_dir)
    except Exception as e:
        log(f"КРАХ: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("-" * 64)
    log(f"Готово: {out_dir}", "OK")
    print()
  
if __name__ == "__main__":
    main()