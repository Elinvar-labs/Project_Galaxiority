"""
fix_model.py — универсальный фиксер 3D-моделей для raylib-py.
Версия с ремешингом и децимацией до заданного числа полигонов.
"""

import sys
import argparse
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

    # 2.1. Триангуляция — raylib жрёт только треугольники
    if mesh.faces.shape[1] != 3:
        log(f"  · не треугольный ({mesh.faces.shape[1]}-gon) — триангулирую")
        try:
            mesh = mesh.triangulate()
        except Exception as e:
            log(f"  · триангуляция не удалась: {e}", "WARN")
    else:
        log("  · уже треугольный")

    # 2.2. Удаление NaN / inf в вершинах
    v = np.asarray(mesh.vertices, dtype=np.float64)
    bad = ~np.isfinite(v).all(axis=1)
    if bad.any():
        log(f"  · найдено {bad.sum()} битых вершин — чищу", "WARN")
        mesh.update_vertices(~bad)

    # 2.3. Вырожденные и дублирующиеся грани
    before = len(mesh.faces)
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

    log(f"После очистки: {len(mesh.vertices)} v, {len(mesh.faces)} f", "OK")
    return mesh


# ============================================================
# 2b. Ремешинг
# ============================================================

def remesh_isotropic(mesh: trimesh.Trimesh,
                     target_edge_length: float | None = None,
                     iterations: int = 5) -> trimesh.Trimesh:
    """
    Качественный изотропный ремешинг через pymeshlab.
    Даёт равномерную сетку с хорошей топологией.
    """
    try:
        import pymeshlab
    except ImportError:
        log("pymeshlab не установлен — падаю в voxel-ремеш", "WARN")
        return remesh_voxel(mesh)

    log("Изотропный ремешинг (pymeshlab)...", "STEP")

    # Автооценка длины ребра, если не задана
    if target_edge_length is None:
        el = mesh.edges_unique_length
        if len(el):
            target_edge_length = float(np.median(el))
        else:
            bbox = mesh.bounds
            target_edge_length = float(np.linalg.norm(bbox[1] - bbox[0]) / 100.0)

    log(f"  · target edge length = {target_edge_length:.5f}")
    log(f"  · было: {len(mesh.vertices)} v, {len(mesh.faces)} f")

    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(
        vertex_matrix=np.asarray(mesh.vertices, dtype=np.float64),
        face_matrix=np.asarray(mesh.faces, dtype=np.int32),
    ))

    # API pymeshlab слегка плавает между версиями — пробуем разные варианты
    tried = False
    for kwargs in (
            dict(targetlen=pymeshlab.PureValue(float(target_edge_length)),
                 iterations=iterations),
            dict(targetLen=pymeshlab.PureValue(float(target_edge_length)),
                 iterations=iterations),
            dict(targetlen=float(target_edge_length), iterations=iterations),
    ):
        try:
            ms.meshing_isotropic_explicit_remeshing(**kwargs)
            tried = True
            break
        except Exception as e:
            last_err = e
            continue
    if not tried:
        log(f"  · isotropic_remeshing упал: {last_err} — падаю в voxel", "WARN")
        return remesh_voxel(mesh)

    out = ms.current_mesh()
    new_mesh = trimesh.Trimesh(
        vertices=np.asarray(out.vertex_matrix(), dtype=np.float64),
        faces=np.asarray(out.face_matrix(), dtype=np.int64),
        process=False,
    )
    log(f"  · стало: {len(new_mesh.vertices)} v, {len(new_mesh.faces)} f", "OK")
    return new_mesh


def remesh_voxel(mesh: trimesh.Trimesh,
                 voxel_size: float | None = None) -> trimesh.Trimesh:
    """
    Voxel-based ремешинг: даёт водонепроницаемую равномерную сетку.
    Хорош для «грязных» сканов / STL. Плох для тонких деталей.
    """
    log("Voxel-ремешинг...", "STEP")

    if voxel_size is None:
        bbox = mesh.bounds
        diag = float(np.linalg.norm(bbox[1] - bbox[0]))
        voxel_size = diag / 120.0
        log(f"  · авто voxel size = {voxel_size:.5f}")

    try:
        vox = mesh.voxelized(pitch=voxel_size)
        new_mesh = vox.marching_cubes
    except Exception as e:
        log(f"  · voxel remesh упал: {e} — fallback subdivide+smooth", "WARN")
        return remesh_fallback(mesh)

    log(f"  · стало: {len(new_mesh.vertices)} v, {len(new_mesh.faces)} f", "OK")
    return new_mesh


def remesh_fallback(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Subdivide + Taubin smoothing. Кривовато, но лучше чем ничего."""
    log("Fallback ремешинг: subdivide + Taubin smooth", "STEP")
    m = mesh.copy()
    try:
        m = m.subdivide()
    except Exception as e:
        log(f"  · subdivide: {e}", "WARN")
    try:
        trimesh.smoothing.filter_taubin(m, lamb=0.5, nu=-0.53, iterations=5)
        log("  · сглажено Таубином")
    except Exception as e:
        log(f"  · taubin smooth: {e}", "WARN")
    return m


def do_remesh(mesh: trimesh.Trimesh, mode: str,
              voxel_size: float | None = None,
              edge_length: float | None = None) -> trimesh.Trimesh:
    if mode == "none":
        return mesh
    if mode == "isotropic":
        return remesh_isotropic(mesh, target_edge_length=edge_length)
    if mode == "voxel":
        return remesh_voxel(mesh, voxel_size=voxel_size)
    raise ValueError(f"Неизвестный режим ремешинга: {mode}")


# ============================================================
# 2c. Децимация (урезка полигонов)
# ============================================================

def decimate_mesh(mesh: trimesh.Trimesh, target_faces: int) -> trimesh.Trimesh:
    """
    Урезает количество граней до target_faces через quadric decimation.
    Сохраняет форму заметно лучше, чем простое прореживание.
    """
    log(f"Децимация до {target_faces} граней...", "STEP")
    if len(mesh.faces) <= target_faces:
        log(f"  · уже {len(mesh.faces)} ≤ {target_faces} — пропуск")
        return mesh

    log(f"  · было: {len(mesh.vertices)} v, {len(mesh.faces)} f")

    # 1) штатный путь trimesh (внутри требует fast-simplification)
    try:
        simplified = mesh.simplify_quadric_decimation(face_count=target_faces)
        log(f"  · стало: {len(simplified.vertices)} v, "
            f"{len(simplified.faces)} f", "OK")
        return simplified
    except Exception as e:
        log(f"  · simplify_quadric_decimation: {e}", "WARN")

    # 2) прямой вызов fast_simplification
    try:
        import fast_simplification
        v, f = fast_simplification.simplify(
            np.asarray(mesh.vertices, dtype=np.float64),
            np.asarray(mesh.faces, dtype=np.int64),
            target_count=int(target_faces),
        )
        simplified = trimesh.Trimesh(vertices=v, faces=f, process=False)
        log(f"  · стало (fast-simplification): "
            f"{len(simplified.vertices)} v, {len(simplified.faces)} f", "OK")
        return simplified
    except Exception as e:
        log(f"  · fast_simplification тоже не сработал: {e}", "ERROR")
        raise


# ============================================================
# 2d. Финализация нормалей / UV
# ============================================================

def finalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Гарантирует наличие вершинных нормалей и UV-развёртки."""
    # Нормали
    try:
        n = mesh.vertex_normals
        if n is None or len(n) != len(mesh.vertices):
            log("  · генерирую нормали")
            _ = mesh.vertex_normals
    except Exception as e:
        log(f"  · нормали: {e}", "WARN")

    # UV
    try:
        uv = getattr(mesh.visual, "uv", None)
        if uv is None or len(uv) != len(mesh.vertices):
            log("  · генерирую UV (сферическая развёртка)")
            mesh.visual.uv = _spherical_uv(mesh.vertices)
    except Exception as e:
        log(f"  · UV: {e}", "WARN")

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
    uvs = np.asarray(getattr(mesh.visual, "uv", None), dtype=np.float64) \
        if getattr(mesh.visual, "uv", None) is not None \
        else np.zeros((len(verts), 2), dtype=np.float64)
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
    uv = getattr(mesh.visual, "uv", None)
    if uv is not None:
        export_mesh.visual = trimesh.visual.TextureVisuals(uv=np.asarray(uv))

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
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Универсальный фиксер 3D-моделей для raylib-py "
                    "(чистка + ремешинг + децимация).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", type=Path, help="Исходная модель (любой формат trimesh)")
    p.add_argument("output", type=Path, nargs="?", default=None,
                   help="Папка вывода (по умолчанию <stem>_fixed рядом с исходником)")
    p.add_argument("--remesh", choices=["none", "isotropic", "voxel"],
                   default="none",
                   help="Тип ремешинга (по умолчанию none). "
                        "isotropic — pymeshlab, voxel — trimesh marching cubes")
    p.add_argument("--voxel-size", type=float, default=None,
                   help="Размер вокселя для --remesh voxel (по умолчанию авто)")
    p.add_argument("--edge-length", type=float, default=None,
                   help="Целевая длина ребра для --remesh isotropic (по умолчанию авто)")
    p.add_argument("--target-faces", type=int, default=None,
                   help="Целевое число граней (децимация quadric decimation)")
    p.add_argument("--no-glb", action="store_true",
                   help="Не экспортировать GLB")
    return p.parse_args()


# ============================================================
# main
# ============================================================

def main():
    args = parse_args()
    src: Path = args.input.resolve()
    out_dir: Path = (args.output.resolve() if args.output
                     else src.parent / f"{src.stem}_fixed")
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"Вход:  {src}")
    log(f"Выход: {out_dir}")
    if args.remesh != "none":
        log(f"Ремешинг: {args.remesh}")
    if args.target_faces:
        log(f"Целевое число полигонов: {args.target_faces}")
    print("-" * 64)

    try:
        mesh = load_mesh(src)

        # 1) Чистка исходника
        mesh = clean_mesh(mesh)

        # 2) Ремешинг (если просили)
        if args.remesh != "none":
            mesh = do_remesh(
                mesh,
                mode=args.remesh,
                voxel_size=args.voxel_size,
                edge_length=args.edge_length,
            )
            # после ремешинга топология новая — перечищаем
            mesh = clean_mesh(mesh)

        # 3) Децимация (если просили)
        if args.target_faces:
            mesh = decimate_mesh(mesh, args.target_faces)
            mesh = clean_mesh(mesh)

        # 4) Нормали + UV перед экспортом
        mesh = finalize_mesh(mesh)

        # 5) Экспорт
        export_safe_obj(mesh, out_dir / f"{src.stem}.obj")
        if not args.no_glb:
            try:
                export_safe_glb(mesh, out_dir / f"{src.stem}.glb")
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