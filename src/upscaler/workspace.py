from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass(frozen=True)
class WorkspaceOptions:
    """Wallpaper workspace options.

    ``scale`` is relative to a contain-fit image. ``offset_x``/``offset_y``
    move the clear image from its centered position. ``seam_blend_px`` controls
    a narrow transition band between the clear image and blurred extension.
    """

    canvas_width: int
    canvas_height: int
    scale: float = 0.85
    offset_x: int = 0
    offset_y: int = 0
    blur_radius: float = 64.0
    background_brightness: float = 1.0
    extension_mode: str = "reflect"
    seam_blend_px: int = 40
    seam_curve: str = "smoothstep"

    def validate(self) -> None:
        if self.canvas_width <= 0 or self.canvas_height <= 0:
            raise ValueError("画布尺寸必须大于 0。")
        if self.scale <= 0:
            raise ValueError("scale 必须大于 0。")
        if self.blur_radius < 0:
            raise ValueError("blur_radius 不能小于 0。")
        if self.background_brightness <= 0:
            raise ValueError("background_brightness 必须大于 0。")
        if self.extension_mode not in {"reflect", "edge"}:
            raise ValueError("extension_mode 仅支持 'reflect' 或 'edge'。")
        if self.seam_blend_px < 0:
            raise ValueError("seam_blend_px 不能小于 0。")
        if self.seam_curve not in {"linear", "smoothstep"}:
            raise ValueError("seam_curve 仅支持 'linear' 或 'smoothstep'。")


@dataclass(frozen=True)
class Placement:
    source_width: int
    source_height: int
    contain_scale: float
    user_scale: float
    effective_scale: float
    image_width: int
    image_height: int
    x: int
    y: int
    visible_left: int
    visible_top: int
    visible_right: int
    visible_bottom: int
    canvas_width: int
    canvas_height: int

    @property
    def visible_width(self) -> int:
        return max(0, self.visible_right - self.visible_left)

    @property
    def visible_height(self) -> int:
        return max(0, self.visible_bottom - self.visible_top)

    @property
    def exposed_left(self) -> int:
        return max(0, self.x)

    @property
    def exposed_top(self) -> int:
        return max(0, self.y)

    @property
    def exposed_right(self) -> int:
        return max(0, self.canvas_width - (self.x + self.image_width))

    @property
    def exposed_bottom(self) -> int:
        return max(0, self.canvas_height - (self.y + self.image_height))


def open_workspace_source(path: Path) -> tuple[Image.Image, bytes | None]:
    """读取工作画布源图，处理 EXIF 方向并统一转为 RGB。"""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        icc_profile = image.info.get("icc_profile")
        rgb = image.convert("RGB")
    return rgb, icc_profile


def calculate_placement(
    source_width: int,
    source_height: int,
    options: WorkspaceOptions,
) -> Placement:
    """计算清晰原图在工作画布中的实际尺寸和位置。"""
    options.validate()
    contain_scale = min(
        options.canvas_width / source_width,
        options.canvas_height / source_height,
    )
    effective_scale = contain_scale * options.scale
    image_width = max(1, round(source_width * effective_scale))
    image_height = max(1, round(source_height * effective_scale))
    x = round((options.canvas_width - image_width) / 2) + options.offset_x
    y = round((options.canvas_height - image_height) / 2) + options.offset_y

    visible_left = max(0, x)
    visible_top = max(0, y)
    visible_right = min(options.canvas_width, x + image_width)
    visible_bottom = min(options.canvas_height, y + image_height)
    if visible_right <= visible_left or visible_bottom <= visible_top:
        raise ValueError("当前缩放 / 位移让清晰原图完全移出了画布。")

    return Placement(
        source_width=source_width,
        source_height=source_height,
        contain_scale=contain_scale,
        user_scale=options.scale,
        effective_scale=effective_scale,
        image_width=image_width,
        image_height=image_height,
        x=x,
        y=y,
        visible_left=visible_left,
        visible_top=visible_top,
        visible_right=visible_right,
        visible_bottom=visible_bottom,
        canvas_width=options.canvas_width,
        canvas_height=options.canvas_height,
    )


def resize_source(source: Image.Image, placement: Placement) -> Image.Image:
    """只对清晰原图做普通几何缩放，不使用生成式 AI。"""
    target_size = (placement.image_width, placement.image_height)
    if source.size == target_size:
        return source.copy()
    return source.resize(target_size, Image.Resampling.LANCZOS)


def _reflect_indices(coordinates: np.ndarray, size: int) -> np.ndarray:
    if size <= 1:
        return np.zeros_like(coordinates, dtype=np.int64)
    period = 2 * (size - 1)
    folded = np.mod(coordinates, period)
    return np.where(folded < size, folded, period - folded).astype(np.int64)


def _edge_indices(coordinates: np.ndarray, size: int) -> np.ndarray:
    if size <= 1:
        return np.zeros_like(coordinates, dtype=np.int64)
    return np.clip(coordinates, 0, size - 1).astype(np.int64)


def make_workspace_background(
    scaled_source: Image.Image,
    placement: Placement,
    options: WorkspaceOptions,
) -> Image.Image:
    """根据当前摆放位置自动延展并模糊所有暴露区域。"""
    array = np.asarray(scaled_source.convert("RGB"), dtype=np.uint8)
    local_x = np.arange(options.canvas_width, dtype=np.int64) - placement.x
    local_y = np.arange(options.canvas_height, dtype=np.int64) - placement.y

    if options.extension_mode == "reflect":
        x_index = _reflect_indices(local_x, placement.image_width)
        y_index = _reflect_indices(local_y, placement.image_height)
    else:
        x_index = _edge_indices(local_x, placement.image_width)
        y_index = _edge_indices(local_y, placement.image_height)

    background = Image.fromarray(array[y_index[:, None], x_index[None, :]], mode="RGB")
    if options.blur_radius > 0:
        background = background.filter(ImageFilter.GaussianBlur(options.blur_radius))
    if options.background_brightness != 1.0:
        background = ImageEnhance.Brightness(background).enhance(
            options.background_brightness
        )
    return background


def _apply_seam_curve(values: np.ndarray, curve: str) -> np.ndarray:
    values = np.clip(values, 0.0, 1.0)
    if curve == "linear":
        return values
    return values * values * (3.0 - 2.0 * values)


def make_seam_alpha_mask(
    placement: Placement,
    seam_blend_px: int,
    seam_curve: str = "smoothstep",
) -> Image.Image:
    """为清晰区域生成只作用于“真正暴露边”的窄幅融合蒙版。"""
    width, height = placement.visible_width, placement.visible_height
    if seam_blend_px <= 0:
        return Image.new("L", (width, height), 255)

    alpha = np.ones((height, width), dtype=np.float32)

    def blend_axis(length: int, reverse: bool = False) -> np.ndarray:
        band = max(1, min(seam_blend_px, length))
        axis = np.arange(length, dtype=np.float32)
        if reverse:
            axis = axis[::-1]
        return _apply_seam_curve(axis / float(band), seam_curve)

    if placement.exposed_left > 0:
        alpha = np.minimum(alpha, blend_axis(width)[None, :])
    if placement.exposed_right > 0:
        alpha = np.minimum(alpha, blend_axis(width, True)[None, :])
    if placement.exposed_top > 0:
        alpha = np.minimum(alpha, blend_axis(height)[:, None])
    if placement.exposed_bottom > 0:
        alpha = np.minimum(alpha, blend_axis(height, True)[:, None])

    return Image.fromarray(
        np.rint(alpha * 255.0).clip(0, 255).astype(np.uint8),
        mode="L",
    )


def composite_visible_sharp_region(
    canvas: Image.Image,
    scaled_source: Image.Image,
    placement: Placement,
    options: WorkspaceOptions,
) -> Image.Image:
    """用窄幅 alpha 过渡把清晰图贴回，消除清晰/模糊的硬接缝。"""
    crop_left = placement.visible_left - placement.x
    crop_top = placement.visible_top - placement.y
    visible_source = scaled_source.crop(
        (
            crop_left,
            crop_top,
            crop_left + placement.visible_width,
            crop_top + placement.visible_height,
        )
    ).convert("RGBA")
    visible_source.putalpha(
        make_seam_alpha_mask(
            placement,
            options.seam_blend_px,
            options.seam_curve,
        )
    )

    base = canvas.convert("RGBA")
    base.alpha_composite(
        visible_source,
        dest=(placement.visible_left, placement.visible_top),
    )
    return base.convert("RGB")


def render_workspace(
    source: Image.Image,
    options: WorkspaceOptions,
) -> tuple[Image.Image, Placement]:
    """生成可二次操作壁纸母版，并对清晰/模糊交界做局部融合。"""
    placement = calculate_placement(source.width, source.height, options)
    scaled_source = resize_source(source, placement)
    canvas = make_workspace_background(scaled_source, placement, options)
    canvas = composite_visible_sharp_region(canvas, scaled_source, placement, options)
    return canvas, placement


def save_workspace(
    image: Image.Image,
    source_path: Path,
    icc_profile: bytes | None,
) -> Path:
    output_path = source_path.with_name(
        f"{source_path.stem}_WORKSPACE_{image.width}x{image.height}.png"
    )
    kwargs: dict[str, object] = {"compress_level": 6}
    if icc_profile:
        kwargs["icc_profile"] = icc_profile
    image.save(output_path, format="PNG", **kwargs)
    return output_path
