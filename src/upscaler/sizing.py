from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetSize:
    width: int
    height: int
    scale: float
    label: str


def fit_inside(src_w: int, src_h: int, box_w: int, box_h: int) -> TargetSize:
    """保持宽高比，把原图完整放入目标框，不裁切、不拉伸。"""
    scale = min(box_w / src_w, box_h / src_h)
    return TargetSize(
        width=max(1, round(src_w * scale)),
        height=max(1, round(src_h * scale)),
        scale=scale,
        label=f"目标框 {box_w}×{box_h}",
    )


def from_scale(src_w: int, src_h: int, scale: float, label: str | None = None) -> TargetSize:
    if scale <= 0:
        raise ValueError("scale 必须大于 0")

    return TargetSize(
        width=max(1, round(src_w * scale)),
        height=max(1, round(src_h * scale)),
        scale=scale,
        label=label or f"{scale:g}x",
    )


def from_long_edge(src_w: int, src_h: int, long_edge: int, label: str | None = None) -> TargetSize:
    if long_edge <= 0:
        raise ValueError("long_edge 必须大于 0")

    scale = long_edge / max(src_w, src_h)
    return TargetSize(
        width=max(1, round(src_w * scale)),
        height=max(1, round(src_h * scale)),
        scale=scale,
        label=label or f"长边 {long_edge}",
    )


def ipad_pro_13(src_w: int, src_h: int) -> TargetSize:
    # 竖图 2064×2752；横图交换。
    box = (2064, 2752) if src_h >= src_w else (2752, 2064)
    result = fit_inside(src_w, src_h, *box)
    return TargetSize(result.width, result.height, result.scale, 'iPad Pro 13"')


def ipad_pro_11(src_w: int, src_h: int) -> TargetSize:
    box = (1668, 2420) if src_h >= src_w else (2420, 1668)
    result = fit_inside(src_w, src_h, *box)
    return TargetSize(result.width, result.height, result.scale, 'iPad Pro 11"')
