from PIL import Image

from upscaler.wallpaper import (
    WallpaperOptions,
    calculate_fit_info,
    fit_source_to_content,
    render_wallpaper,
)


def test_cover_fit_reference_geometry():
    # Reference-like case:
    # 2048x1152 source, 944x2048 final, 531px top extension.
    # Sharp content region is therefore 944x1517.
    info = calculate_fit_info(
        source_width=2048,
        source_height=1152,
        content_width=944,
        content_height=1517,
    )

    assert abs(info.scale - (1517 / 1152)) < 0.002
    assert info.resized_height == 1517
    assert info.resized_width > 2600


def test_sharp_content_exact_size():
    source = Image.new("RGB", (2048, 1152), (20, 30, 40))

    sharp, _ = fit_source_to_content(
        source,
        944,
        1517,
    )

    assert sharp.size == (944, 1517)


def test_top_only_extension_canvas_size():
    source = Image.new("RGB", (2048, 1152), (20, 30, 40))

    result, _ = render_wallpaper(
        source,
        WallpaperOptions(
            canvas_width=944,
            canvas_height=2048,
            extend_top=531,
            blur_radius=48,
        ),
    )

    assert result.size == (944, 2048)


def test_content_region_is_pasted_sharp():
    # Use a simple gradient so we can verify that the sharp region is
    # exactly the fitted source, not a blurred copy.
    source = Image.new("RGB", (200, 100))
    px = source.load()

    for y in range(100):
        for x in range(200):
            px[x, y] = (x % 256, y % 256, 100)

    options = WallpaperOptions(
        canvas_width=120,
        canvas_height=200,
        extend_top=40,
        blur_radius=20,
    )

    expected, _ = fit_source_to_content(
        source,
        options.content_width,
        options.content_height,
    )

    result, _ = render_wallpaper(source, options)

    sharp_region = result.crop(
        (
            options.extend_left,
            options.extend_top,
            options.extend_left + options.content_width,
            options.extend_top + options.content_height,
        )
    )

    assert list(sharp_region.getdata()) == list(expected.getdata())
