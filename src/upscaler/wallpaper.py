from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass(frozen=True)
class WallpaperOptions:
    """
    iOS-like edge extension parameters.

    Important difference from the old implementation:
    - The source image is NOT shrunk into a smaller "card".
    - The sharp source is resized/cropped to fill the non-extended content region.
    - Only the missing outer margins are synthesized from reflected edge pixels
      and blurred.
    """

    canvas_width: int
    canvas_height: int

    extend_top: int = 0
    extend_bottom: int = 0
    extend_left: int = 0
    extend_right: int = 0

    # Crop focus when fitting the source into the sharp content region.
    # 0 = left/top, 0.5 = center, 1 = right/bottom.
    focus_x: float = 0.5
    focus_y: float = 0.5

    blur_radius: float = 64.0
    background_brightness: float = 1.0

    def validate(self) -> None:
        if self.canvas_width <= 0 or self.canvas_height <= 0:
            raise ValueError("画布尺寸必须大于 0。")

        for name, value in {
            "extend_top": self.extend_top,
            "extend_bottom": self.extend_bottom,
            "extend_left": self.extend_left,
            "extend_right": self.extend_right,
        }.items():
            if value < 0:
                raise ValueError(f"{name} 不能小于 0。")

        content_w = (
            self.canvas_width
            - self.extend_left
            - self.extend_right
        )
        content_h = (
            self.canvas_height
            - self.extend_top
            - self.extend_bottom
        )

        if content_w <= 0 or content_h <= 0:
            raise ValueError("扩展边距过大，已经没有可显示原图的区域。")

        if not 0.0 <= self.focus_x <= 1.0:
            raise ValueError("focus_x 必须在 0~1。")

        if not 0.0 <= self.focus_y <= 1.0:
            raise ValueError("focus_y 必须在 0~1。")

        if self.blur_radius < 0:
            raise ValueError("blur_radius 不能小于 0。")

        if self.background_brightness <= 0:
            raise ValueError("background_brightness 必须大于 0。")

    @property
    def content_width(self) -> int:
        return (
            self.canvas_width
            - self.extend_left
            - self.extend_right
        )

    @property
    def content_height(self) -> int:
        return (
            self.canvas_height
            - self.extend_top
            - self.extend_bottom
        )


@dataclass(frozen=True)
class FitInfo:
    source_width: int
    source_height: int
    content_width: int
    content_height: int
    scale: float
    resized_width: int
    resized_height: int
    crop_left: int
    crop_top: int


def open_source_image(path: Path) -> tuple[Image.Image, bytes | None]:
    """Read the source and respect EXIF orientation."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        icc_profile = image.info.get("icc_profile")
        rgb = image.convert("RGB")

    return rgb, icc_profile


def calculate_fit_info(
    source_width: int,
    source_height: int,
    content_width: int,
    content_height: int,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
) -> FitInfo:
    """
    COVER fit.

    The sharp source fills the whole content region.
    If aspect ratios differ, the excess is cropped instead of leaving
    blurred bars around all four sides.

    This is the key behavior that makes the result look like iOS edge
    extension rather than "a small picture on a blurred background".
    """
    scale = max(
        content_width / source_width,
        content_height / source_height,
    )

    resized_w = max(1, round(source_width * scale))
    resized_h = max(1, round(source_height * scale))

    excess_x = max(0, resized_w - content_width)
    excess_y = max(0, resized_h - content_height)

    crop_left = round(excess_x * focus_x)
    crop_top = round(excess_y * focus_y)

    return FitInfo(
        source_width=source_width,
        source_height=source_height,
        content_width=content_width,
        content_height=content_height,
        scale=scale,
        resized_width=resized_w,
        resized_height=resized_h,
        crop_left=crop_left,
        crop_top=crop_top,
    )


def fit_source_to_content(
    source: Image.Image,
    content_width: int,
    content_height: int,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
) -> tuple[Image.Image, FitInfo]:
    """Resize and crop the source so it exactly fills the sharp region."""
    info = calculate_fit_info(
        source.width,
        source.height,
        content_width,
        content_height,
        focus_x,
        focus_y,
    )

    if (info.resized_width, info.resized_height) == source.size:
        resized = source.copy()
    else:
        resized = source.resize(
            (info.resized_width, info.resized_height),
            Image.Resampling.LANCZOS,
        )

    sharp = resized.crop(
        (
            info.crop_left,
            info.crop_top,
            info.crop_left + content_width,
            info.crop_top + content_height,
        )
    )

    return sharp, info


def _reflect_pad(
    content: Image.Image,
    top: int,
    bottom: int,
    left: int,
    right: int,
) -> Image.Image:
    """
    Extend only from pixels directly adjacent to the content edges.

    np.pad(mode="reflect") creates a mirrored continuation.
    After Gaussian blur the mirror is no longer visually obvious, but color,
    brightness and large shapes remain continuous at the boundary.
    """
    array = np.asarray(content.convert("RGB"), dtype=np.uint8)

    # np.pad(reflect) requires an axis with at least 2 pixels.
    mode = "reflect" if content.width > 1 and content.height > 1 else "edge"

    padded = np.pad(
        array,
        (
            (top, bottom),
            (left, right),
            (0, 0),
        ),
        mode=mode,
    )

    return Image.fromarray(padded, mode="RGB")


def make_extended_background(
    sharp_content: Image.Image,
    options: WallpaperOptions,
) -> Image.Image:
    """
    Build the blurred outer ring from the sharp content's own edge pixels.

    Unlike the old implementation, this does NOT create a full-screen blurred
    copy of the original and then place a smaller picture on top.
    """
    background = _reflect_pad(
        sharp_content,
        top=options.extend_top,
        bottom=options.extend_bottom,
        left=options.extend_left,
        right=options.extend_right,
    )

    if options.blur_radius > 0:
        background = background.filter(
            ImageFilter.GaussianBlur(options.blur_radius)
        )

    if options.background_brightness != 1.0:
        background = ImageEnhance.Brightness(background).enhance(
            options.background_brightness
        )

    return background


def render_wallpaper(
    source: Image.Image,
    options: WallpaperOptions,
) -> tuple[Image.Image, FitInfo]:
    """
    Render iOS-like edge extension.

    1. Define a sharp content rectangle inside the final canvas.
    2. COVER-fit the source into that rectangle.
    3. Reflect the sharp content's edge pixels into the missing margins.
    4. Blur the reflected margins.
    5. Paste the sharp content back unchanged over the center region.

    Final result:
        blurred extension only outside the content region,
        sharp image remains the dominant wallpaper itself.
    """
    options.validate()

    sharp, info = fit_source_to_content(
        source=source,
        content_width=options.content_width,
        content_height=options.content_height,
        focus_x=options.focus_x,
        focus_y=options.focus_y,
    )

    canvas = make_extended_background(sharp, options)

    # Paste the sharp region back exactly.
    # There is intentionally no feathering here: the source region itself
    # remains crisp; only the outside extension is blurred.
    canvas.paste(
        sharp,
        (options.extend_left, options.extend_top),
    )

    if canvas.size != (
        options.canvas_width,
        options.canvas_height,
    ):
        raise RuntimeError(
            "内部尺寸错误：最终画布与目标尺寸不一致。"
        )

    return canvas, info


def save_wallpaper(
    image: Image.Image,
    source_path: Path,
    icc_profile: bytes | None,
) -> Path:
    output_path = source_path.with_name(
        f"{source_path.stem}_EDGE_EXTEND_"
        f"{image.width}x{image.height}.png"
    )

    kwargs: dict[str, object] = {
        "compress_level": 6,
    }

    if icc_profile:
        kwargs["icc_profile"] = icc_profile

    image.save(
        output_path,
        format="PNG",
        **kwargs,
    )

    return output_path
