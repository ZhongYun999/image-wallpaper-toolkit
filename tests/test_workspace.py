import numpy as np
from PIL import Image

from upscaler.workspace import (
    WorkspaceOptions,
    apply_display_calibration,
    calculate_placement,
    make_seam_alpha_mask,
    render_workspace,
    resize_source,
)


def test_same_ratio_100_percent_fills_canvas():
    options = WorkspaceOptions(canvas_width=2064, canvas_height=2752, scale=1.0)
    placement = calculate_placement(1086, 1448, options)
    assert placement.image_width == 2064
    assert placement.image_height == 2752
    assert placement.x == 0
    assert placement.y == 0


def test_80_percent_creates_symmetric_margin():
    options = WorkspaceOptions(canvas_width=1000, canvas_height=1000, scale=0.8)
    placement = calculate_placement(1000, 1000, options)
    assert placement.image_width == 800
    assert placement.image_height == 800
    assert placement.x == 100
    assert placement.y == 100
    assert placement.exposed_left == 100
    assert placement.exposed_right == 100


def test_offset_moves_image():
    options = WorkspaceOptions(
        canvas_width=1000,
        canvas_height=1000,
        scale=0.8,
        offset_x=75,
        offset_y=-40,
    )
    placement = calculate_placement(1000, 1000, options)
    assert placement.x == 175
    assert placement.y == 60


def test_sharp_visible_region_is_preserved_when_seam_disabled():
    array = np.zeros((40, 60, 3), dtype=np.uint8)
    for y in range(40):
        for x in range(60):
            array[y, x] = (x * 4 % 256, y * 6 % 256, (x + y) * 3 % 256)

    source = Image.fromarray(array, "RGB")
    options = WorkspaceOptions(
        canvas_width=120,
        canvas_height=120,
        scale=0.75,
        offset_x=12,
        offset_y=-8,
        blur_radius=8,
        seam_blend_px=0,
    )
    result, placement = render_workspace(source, options)
    scaled = resize_source(source, placement)

    crop_left = placement.visible_left - placement.x
    crop_top = placement.visible_top - placement.y
    expected = scaled.crop((
        crop_left,
        crop_top,
        crop_left + placement.visible_width,
        crop_top + placement.visible_height,
    ))
    actual = result.crop((
        placement.visible_left,
        placement.visible_top,
        placement.visible_right,
        placement.visible_bottom,
    ))
    assert list(actual.getdata()) == list(expected.getdata())


def test_seam_mask_softens_only_exposed_edges():
    options = WorkspaceOptions(
        canvas_width=120,
        canvas_height=120,
        scale=0.75,
        offset_x=12,
        offset_y=-8,
        seam_blend_px=16,
    )
    placement = calculate_placement(60, 40, options)
    mask = make_seam_alpha_mask(placement, seam_blend_px=16, seam_curve="smoothstep")
    assert mask.size == (placement.visible_width, placement.visible_height)
    left_mid = mask.getpixel((0, placement.visible_height // 2))
    center = mask.getpixel((placement.visible_width // 2, placement.visible_height // 2))
    assert left_mid < center
    assert center == 255


def test_display_calibration_identity_is_noop():
    source = Image.new("RGB", (8, 8), (32, 64, 128))
    out = apply_display_calibration(source, 1.0, 1.0, 1.0, 1.0)
    assert list(out.getdata()) == list(source.getdata())


def test_display_calibration_changes_output():
    source = Image.new("RGB", (8, 8), (64, 96, 160))
    out = apply_display_calibration(source, 0.95, 0.90, 0.90, 1.05)
    assert list(out.getdata()) != list(source.getdata())


def test_gamma_above_one_darkens_midtones():
    source = Image.new("RGB", (4, 4), (128, 128, 128))
    out = apply_display_calibration(source, gamma=1.10)
    assert out.getpixel((0, 0))[0] < 128
