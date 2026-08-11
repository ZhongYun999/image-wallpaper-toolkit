from upscaler.sizing import (
    fit_inside,
    from_long_edge,
    from_scale,
    ipad_pro_13,
)


def test_double_scale():
    result = from_scale(1086, 1448, 2)
    assert (result.width, result.height) == (2172, 2896)


def test_ipad_pro_13_exact_ratio():
    result = ipad_pro_13(1086, 1448)
    assert (result.width, result.height) == (2064, 2752)


def test_fit_inside_does_not_crop():
    result = fit_inside(1920, 1080, 1000, 1000)
    assert result.width == 1000
    assert result.height == 562


def test_long_edge():
    result = from_long_edge(1086, 1448, 3840)
    assert result.height == 3840
    assert result.width == 2880
