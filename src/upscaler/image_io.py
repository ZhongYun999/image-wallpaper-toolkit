from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class LoadedImage:
    path: Path
    rgb: np.ndarray
    alpha: Image.Image | None
    width: int
    height: int
    original_mode: str
    icc_profile: bytes | None


def clean_path_text(text: str) -> str:
    text = text.strip()

    if (
        len(text) >= 2
        and text[0] == text[-1]
        and text[0] in ("'", '"')
    ):
        text = text[1:-1]

    return text.strip()


def select_image_interactively() -> Path:
    print("\n请选择输入图片：")
    print("  - 可把图片拖入控制台后按 Enter")
    print("  - 也可输入完整路径")
    print("  - 直接按 Enter：尝试打开文件选择窗口")

    raw = input("\n图片路径 > ").strip()

    if raw:
        path = Path(clean_path_text(raw))
    else:
        path = _select_with_tkinter()

    path = path.expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"找不到图片：{path}")

    return path


def _select_with_tkinter() -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()

        filename = filedialog.askopenfilename(
            title="选择需要超分的图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                ("所有文件", "*.*"),
            ],
        )

        root.destroy()

        if not filename:
            raise RuntimeError("未选择图片。")

        return Path(filename)

    except Exception as exc:
        print(f"文件选择窗口不可用：{exc}")
        raw = input("请手动输入图片完整路径 > ")
        return Path(clean_path_text(raw))


def load_image(path: Path) -> LoadedImage:
    with Image.open(path) as image:
        width, height = image.size
        original_mode = image.mode
        icc_profile = image.info.get("icc_profile")

        alpha = image.getchannel("A").copy() if "A" in image.getbands() else None
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()

    return LoadedImage(
        path=path,
        rgb=rgb,
        alpha=alpha,
        width=width,
        height=height,
        original_mode=original_mode,
        icc_profile=icc_profile,
    )


def save_png(
    rgb: np.ndarray,
    alpha: Image.Image | None,
    target_width: int,
    target_height: int,
    source_path: Path,
    icc_profile: bytes | None,
) -> Path:
    image = Image.fromarray(rgb, mode="RGB")

    if image.size != (target_width, target_height):
        print(
            f"\n最终尺寸调整：{image.width}×{image.height}"
            f" -> {target_width}×{target_height}（Lanczos）"
        )
        image = image.resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS,
        )

    if alpha is not None:
        alpha = alpha.resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS,
        )
        image = image.convert("RGBA")
        image.putalpha(alpha)

    output_path = source_path.with_name(
        f"{source_path.stem}_SR_{target_width}x{target_height}.png"
    )

    save_kwargs = {"compress_level": 6}
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    image.save(output_path, "PNG", **save_kwargs)

    return output_path


def reveal_in_file_manager(path: Path) -> None:
    if os.name == "nt":
        try:
            os.startfile(path.parent)
        except Exception:
            pass
