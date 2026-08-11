from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass(frozen=True)
class WorkspaceOptions:
    """
    可供 iPad 壁纸界面继续缩放 / 平移的“母版工作画布”。

    scale:
        相对于 contain-fit 的倍率。
        1.0 = 完整原图刚好放入画布。
        < 1.0 = 缩小原图，四周留下更多可操作空间。
        > 1.0 = 放大原图，可能有一部分超出画布。

    offset_x / offset_y:
        相对于居中位置的像素位移。
        offset_x > 0 向右移动。
        offset_y > 0 向下移动。

    extension_mode:
        "reflect" = 镜像延展，默认，通常最自然。
        "edge" = 复制最邻近边缘像素，再模糊。

    seam_blend_px:
        清晰原图与模糊扩展区之间的过渡带宽度。
        只在真正与扩展区接壤的边缘生效。
        0 = 不做融合，边缘会更利落，但更容易看到接缝。

    display calibration:
        在整张最终壁纸导出前施加基础显示校准，
        主要用于让 iPad OLED 上的实际观感更接近预期。
    """

    canvas_width: int
    canvas_height: int

    scale: float = 0.85
    offset_x: int = 0
    offset_y: int = 0

    blur_radius: float = 64.0
    background_brightness: float = 1.0
    extension_mode: str = "reflect"
    seam_blend_px: int = 64
    seam_curve: str = "smoothstep"

    output_brightness: float = 1.0
    output_contrast: float = 1.0
    output_saturation: float = 1.0
    output_gamma: float = 1.0

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
            raise ValueError(
                "extension_mode 仅支持 'reflect' 或 'edge'。"
            )

        if self.seam_blend_px < 0:
            raise ValueError("seam_blend_px 不能小于 0。")

        if self.seam_curve not in {"linear", "smoothstep"}:
            raise ValueError(
                "seam_curve 仅支持 'linear' 或 'smoothstep'。"
            )

        for name, value in {
            "output_brightness": self.output_brightness,
            "output_contrast": self.output_contrast,
            "output_saturation": self.output_saturation,
            "output_gamma": self.output_gamma,
        }.items():
            if value <= 0:
                raise ValueError(f"{name} 必须大于 0。")


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
        return max(
            0,
            self.canvas_width - (self.x + self.image_width),
        )

    @property
    def exposed_bottom(self) -> int:
        return max(
            0,
            self.canvas_height - (self.y + self.image_height),
        )


def open_workspace_source(path: Path) -> tuple[Image.Image, bytes | None]:
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
    options.validate()

    contain_scale = min(
        options.canvas_width / source_width,
        options.canvas_height / source_height,
    )
    effective_scale = contain_scale * options.scale

    image_width = max(1, round(source_width * effective_scale))
    image_height = max(1, round(source_height * effective_scale))

    centered_x = round((options.canvas_width - image_width) / 2)
    centered_y = round((options.canvas_height - image_height) / 2)

    x = centered_x + options.offset_x
    y = centered_y + options.offset_y

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
    array = np.asarray(scaled_source.convert("RGB"), dtype=np.uint8)

    local_x = np.arange(options.canvas_width, dtype=np.int64) - placement.x
    local_y = np.arange(options.canvas_height, dtype=np.int64) - placement.y

    if options.extension_mode == "reflect":
        x_index = _reflect_indices(local_x, placement.image_width)
        y_index = _reflect_indices(local_y, placement.image_height)
    else:
        x_index = _edge_indices(local_x, placement.image_width)
        y_index = _edge_indices(local_y, placement.image_height)

    background_array = array[y_index[:, None], x_index[None, :]]
    background = Image.fromarray(background_array, mode="RGB")

    if options.blur_radius > 0:
        background = background.filter(ImageFilter.GaussianBlur(options.blur_radius))

    if options.background_brightness != 1.0:
        background = ImageEnhance.Brightness(background).enhance(options.background_brightness)

    return background


def _smoothstep(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def _apply_curve(values: np.ndarray, curve: str) -> np.ndarray:
    if curve == "linear":
        return np.clip(values, 0.0, 1.0)
    return _smoothstep(values)


def make_seam_alpha_mask(
    placement: Placement,
    seam_blend_px: int,
    seam_curve: str = "smoothstep",
) -> Image.Image:
    width = placement.visible_width
    height = placement.visible_height

    if seam_blend_px <= 0:
        return Image.new("L", (width, height), 255)

    alpha = np.ones((height, width), dtype=np.float32)

    if placement.exposed_left > 0:
        edge_width = min(seam_blend_px, width)
        x = np.arange(width, dtype=np.float32)
        t = _apply_curve(x / float(edge_width), seam_curve)
        alpha = np.minimum(alpha, t[None, :])

    if placement.exposed_right > 0:
        edge_width = min(seam_blend_px, width)
        x = np.arange(width, dtype=np.float32)[::-1]
        t = _apply_curve(x / float(edge_width), seam_curve)
        alpha = np.minimum(alpha, t[None, :])

    if placement.exposed_top > 0:
        edge_height = min(seam_blend_px, height)
        y = np.arange(height, dtype=np.float32)
        t = _apply_curve(y / float(edge_height), seam_curve)
        alpha = np.minimum(alpha, t[:, None])

    if placement.exposed_bottom > 0:
        edge_height = min(seam_blend_px, height)
        y = np.arange(height, dtype=np.float32)[::-1]
        t = _apply_curve(y / float(edge_height), seam_curve)
        alpha = np.minimum(alpha, t[:, None])

    alpha = np.rint(alpha * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(alpha, mode="L")


def composite_visible_sharp_region(
    canvas: Image.Image,
    scaled_source: Image.Image,
    placement: Placement,
    seam_blend_px: int,
    seam_curve: str = "smoothstep",
) -> Image.Image:
    crop_left = placement.visible_left - placement.x
    crop_top = placement.visible_top - placement.y
    crop_right = crop_left + placement.visible_width
    crop_bottom = crop_top + placement.visible_height

    visible_source = scaled_source.crop(
        (crop_left, crop_top, crop_right, crop_bottom)
    ).convert("RGBA")

    alpha_mask = make_seam_alpha_mask(
        placement=placement,
        seam_blend_px=seam_blend_px,
        seam_curve=seam_curve,
    )
    visible_source.putalpha(alpha_mask)

    base = canvas.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay.alpha_composite(
        visible_source,
        dest=(placement.visible_left, placement.visible_top),
    )
    base.alpha_composite(overlay)
    return base.convert("RGB")


def apply_display_calibration(
    image: Image.Image,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    gamma: float = 1.0,
) -> Image.Image:
    """
    在最终输出阶段施加基础显示校准。

    - brightness: 整体亮度
    - contrast: 对比度
    - saturation: 饱和度（Pillow 的 Color）
    - gamma: 中间调校正；>1 会压暗中间调，<1 会提亮中间调
    """
    result = image.convert("RGB")

    if brightness != 1.0:
        result = ImageEnhance.Brightness(result).enhance(brightness)

    if contrast != 1.0:
        result = ImageEnhance.Contrast(result).enhance(contrast)

    if saturation != 1.0:
        result = ImageEnhance.Color(result).enhance(saturation)

    if gamma != 1.0:
        table = [
            max(0, min(255, round(((i / 255.0) ** gamma) * 255.0)))
            for i in range(256)
        ]
        result = result.point(table * 3)

    return result


def render_workspace(
    source: Image.Image,
    options: WorkspaceOptions,
) -> tuple[Image.Image, Placement]:
    placement = calculate_placement(source.width, source.height, options)
    scaled_source = resize_source(source, placement)

    canvas = make_workspace_background(scaled_source, placement, options)
    canvas = composite_visible_sharp_region(
        canvas,
        scaled_source,
        placement,
        seam_blend_px=options.seam_blend_px,
        seam_curve=options.seam_curve,
    )

    canvas = apply_display_calibration(
        canvas,
        brightness=options.output_brightness,
        contrast=options.output_contrast,
        saturation=options.output_saturation,
        gamma=options.output_gamma,
    )

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
