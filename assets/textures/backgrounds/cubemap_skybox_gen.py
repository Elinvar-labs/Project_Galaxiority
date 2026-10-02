#!/usr/bin/env python3
"""
Генератор кубмап-скайбоксов в формате развёртки (горизонтальный крест 4x3)
из одной бесшовной квадратной текстуры.

Текстура проецируется на сферу методом triplanar: каждая точка сферы
берёт цвет из текстуры по трём ортогональным проекциям, смешанным по
нормали. Это даёт:
  * отсутствие швов на границах граней;
  * одинаково корректную ориентацию всех шести граней;
  * отсутствие пинч-эффекта на полюсах.

Примеры:
    python make_cubemap.py texture.png
    python make_cubemap.py textures/ -r -s 512 -t 2
    python make_cubemap.py textures/ -r -o out/ --suffix _sky
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


# --- геометрия развёртки ---------------------------------------------------
CROSS_W, CROSS_H = 4, 3

# (имя грани, колонка, строка). Схема — горизонтальный крест.
CROSS_FACES = [
    ("px", 2, 1),  # +X — right
    ("nx", 0, 1),  # -X — left
    ("py", 1, 0),  # +Y — up
    ("ny", 1, 2),  # -Y — down
    ("pz", 1, 1),  # +Z — front
    ("nz", 3, 1),  # -Z — back
]

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tga",
                 ".webp", ".tif", ".tiff", ".gif"}


# --- утилиты ---------------------------------------------------------------

def to_square(img: Image.Image) -> Image.Image:
    """Обрезает изображение по центру до квадрата."""
    if img.width == img.height:
        return img
    s = min(img.width, img.height)
    l = (img.width - s) // 2
    t = (img.height - s) // 2
    return img.crop((l, t, l + s, t + s))


def _sample_bilinear_wrap(tex: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Билинейная выборка из tex формы (H, W, C) с заворотом координат.
    u, v — вещественные массивы той же формы, что и результат;
    координаты заданы в единицах текстуры: 0..1 = один период текстуры,
    значения вне [0, 1] заворачиваются.
    """
    H, W = tex.shape[:2]

    x = u * W - 0.5
    y = v * H - 0.5

    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    wx = (x - x0)[..., None]
    wy = (y - y0)[..., None]

    x0m = x0 % W
    x1m = (x0 + 1) % W
    y0m = y0 % H
    y1m = (y0 + 1) % H

    c00 = tex[y0m, x0m]
    c01 = tex[y0m, x1m]
    c10 = tex[y1m, x0m]
    c11 = tex[y1m, x1m]

    top = c00 * (1.0 - wx) + c01 * wx
    bot = c10 * (1.0 - wx) + c11 * wx
    return top * (1.0 - wy) + bot * wy


def _sphere_directions(face_size: int) -> dict[str, np.ndarray]:
    """
    Для каждой из 6 граней возвращает массив (S, S, 3) единичных векторов
    направлений, соответствующих центрам пикселей грани.
    Конвенция — как у OpenGL cubemap.
    """
    s = (np.arange(face_size, dtype=np.float64) + 0.5) / face_size * 2.0 - 1.0
    u, v = np.meshgrid(s, s)          # v направлен вниз, как в изображении
    o = np.ones_like(u)

    dirs = {
        "px": np.stack([ o, -v, -u], axis=-1),
        "nx": np.stack([-o, -v,  u], axis=-1),
        "py": np.stack([ u,  o,  v], axis=-1),
        "ny": np.stack([ u, -o, -v], axis=-1),
        "pz": np.stack([ u, -v,  o], axis=-1),
        "nz": np.stack([-u, -v, -o], axis=-1),
    }
    for k in dirs:
        n = np.linalg.norm(dirs[k], axis=-1, keepdims=True)
        dirs[k] = dirs[k] / n
    return dirs


def _triplanar_face(tex: np.ndarray,
                    dirs: np.ndarray,
                    tiles: int,
                    blend_power: float) -> np.ndarray:
    """
    Triplanar-выборка текстуры по массиву направлений (S, S, 3).
    Возвращает (S, S, 3) float32.
    """
    x = dirs[..., 0]
    y = dirs[..., 1]
    z = dirs[..., 2]

    def to_uv(a: np.ndarray) -> np.ndarray:
        # [-1, 1] -> [0, tiles] — единицы текстуры
        return (a * 0.5 + 0.5) * tiles

    # три ортогональные проекции
    c_xy = _sample_bilinear_wrap(tex, to_uv(x), to_uv(y))  # проекция вдоль Z
    c_yz = _sample_bilinear_wrap(tex, to_uv(y), to_uv(z))  # проекция вдоль X
    c_zx = _sample_bilinear_wrap(tex, to_uv(z), to_uv(x))  # проекция вдоль Y

    # веса по нормали
    wx = np.abs(x) ** blend_power
    wy = np.abs(y) ** blend_power
    wz = np.abs(z) ** blend_power
    wsum = wx + wy + wz + 1e-9
    wx = (wx / wsum)[..., None]
    wy = (wy / wsum)[..., None]
    wz = (wz / wsum)[..., None]

    return c_yz * wx + c_zx * wy + c_xy * wz


def make_cubemap(texture: Image.Image,
                 face_size: int,
                 tiles: int,
                 blend_power: float = 4.0) -> Image.Image:
    """Собирает крестовую развёртку кубмапы из бесшовной текстуры."""
    tex = np.asarray(texture.convert("RGB"), dtype=np.float32)
    dirs = _sphere_directions(face_size)

    cross = Image.new(
        "RGB",
        (face_size * CROSS_W, face_size * CROSS_H),
        (0, 0, 0),
    )
    for name, col, row in CROSS_FACES:
        face = _triplanar_face(tex, dirs[name], tiles, blend_power)
        face = np.clip(face, 0, 255).astype(np.uint8)
        cross.paste(Image.fromarray(face, "RGB"),
                    (col * face_size, row * face_size))
    return cross


# --- обработка файлов ------------------------------------------------------

def process_file(path: Path,
                 out_dir: Path | None,
                 face_size: int,
                 tiles: int,
                 suffix: str,
                 blend_power: float) -> None:
    try:
        img = Image.open(path)
        img.load()
        img = img.convert("RGB")
    except Exception as e:  # noqa: BLE001
        print(f"  ! пропуск {path.name}: {e}")
        return

    img = to_square(img)
    cubemap = make_cubemap(img, face_size, tiles, blend_power)

    if out_dir is not None:
        out_path = out_dir / (path.stem + suffix + ".png")
    else:
        out_path = path.with_name(path.stem + suffix + ".png")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cubemap.save(out_path, "PNG")
    print(f"  -> {out_path}")


def iter_files(root: Path, recursive: bool):
    if root.is_file():
        yield root
        return
    pattern = "**/*" if recursive else "*"
    for p in root.glob(pattern):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
            yield p


# --- CLI -------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", type=Path,
                    help="Входной файл или папка с текстурами")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Папка для результата (по умолчанию рядом с исходником)")
    ap.add_argument("-s", "--face-size", type=int, default=512,
                    help="Размер одной грани в пикселях (по умолчанию 512)")
    ap.add_argument("-t", "--tiles", type=int, default=1,
                    help="Сколько раз повторять текстуру (по умолчанию 1)")
    ap.add_argument("--suffix", default="_cubemap",
                    help="Суффикс выходных файлов (по умолчанию _cubemap)")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="Рекурсивно обходить подпапки")
    ap.add_argument("--blend-power", type=float, default=4.0,
                    help="Резкость смешивания triplanar-проекций "
                         "(2 — мягко, 4 — по умолчанию, 8 — почти как "
                         "грани куба)")

    args = ap.parse_args()

    if not args.input.exists():
        print(f"Входной путь не найден: {args.input}")
        return 1

    files = list(iter_files(args.input, args.recursive))
    if not files:
        print("Не найдено подходящих изображений.")
        return 1

    for f in files:
        print(f"Обработка: {f}")
        process_file(f, args.output, args.face_size, args.tiles,
                     args.suffix, args.blend_power)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())