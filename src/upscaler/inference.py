from __future__ import annotations

import math

import numpy as np
import torch

from .config import DEFAULT_TILE_PAD, NATIVE_SCALE


def _to_tensor(
    tile_rgb: np.ndarray,
    device: torch.device,
    use_half: bool,
) -> torch.Tensor:
    array = np.ascontiguousarray(tile_rgb)

    tensor = (
        torch.from_numpy(array)
        .permute(2, 0, 1)
        .unsqueeze(0)
        .to(device=device, non_blocking=True)
        .float()
        .div_(255.0)
    )

    return tensor.half() if use_half else tensor


@torch.inference_mode()
def _run_tile(
    model: torch.nn.Module,
    tile_rgb: np.ndarray,
    device: torch.device,
    use_half: bool,
) -> np.ndarray:
    input_tensor = _to_tensor(tile_rgb, device, use_half)

    output = model(input_tensor)
    output = output.clamp_(0, 1)

    output = (
        output.squeeze(0)
        .permute(1, 2, 0)
        .float()
        .cpu()
        .numpy()
    )

    return np.rint(output * 255.0).clip(0, 255).astype(np.uint8)


def upscale_x4_tiled(
    model: torch.nn.Module,
    rgb: np.ndarray,
    device: torch.device,
    use_half: bool,
    tile: int,
    tile_pad: int = DEFAULT_TILE_PAD,
) -> np.ndarray:
    """
    真正的 x4 AI 超分。

    tile == 0:
        整张图一次送入 GPU。

    tile > 0:
        分块推理，并在每块周围额外取 tile_pad 像素，
        最后只保留中间区域，降低拼接边界。
    """
    height, width, _ = rgb.shape
    scale = NATIVE_SCALE

    if tile == 0:
        return _run_tile(model, rgb, device, use_half)

    output = np.empty(
        (height * scale, width * scale, 3),
        dtype=np.uint8,
    )

    tiles_x = math.ceil(width / tile)
    tiles_y = math.ceil(height / tile)
    total_tiles = tiles_x * tiles_y
    index = 0

    for y0 in range(0, height, tile):
        y1 = min(y0 + tile, height)

        for x0 in range(0, width, tile):
            x1 = min(x0 + tile, width)

            padded_x0 = max(x0 - tile_pad, 0)
            padded_y0 = max(y0 - tile_pad, 0)
            padded_x1 = min(x1 + tile_pad, width)
            padded_y1 = min(y1 + tile_pad, height)

            input_tile = rgb[
                padded_y0:padded_y1,
                padded_x0:padded_x1,
            ]

            sr_tile = _run_tile(
                model,
                input_tile,
                device,
                use_half,
            )

            crop_x0 = (x0 - padded_x0) * scale
            crop_y0 = (y0 - padded_y0) * scale
            crop_x1 = crop_x0 + (x1 - x0) * scale
            crop_y1 = crop_y0 + (y1 - y0) * scale

            output[
                y0 * scale:y1 * scale,
                x0 * scale:x1 * scale,
            ] = sr_tile[
                crop_y0:crop_y1,
                crop_x0:crop_x1,
            ]

            index += 1
            print(
                f"\rAI 超分：{index}/{total_tiles} tiles"
                f" ({index * 100 / total_tiles:6.2f}%)",
                end="",
                flush=True,
            )

            if device.type == "cuda":
                torch.cuda.empty_cache()

    print()
    return output


def _tile_candidates(initial_tile: int) -> list[int]:
    fallback = [512, 384, 256, 192, 128]

    if initial_tile == 0:
        raw = [0, *fallback]
    else:
        raw = [initial_tile, *fallback]

    result: list[int] = []
    seen: set[int] = set()

    for value in raw:
        if value in seen:
            continue

        if initial_tile != 0 and value > initial_tile:
            continue

        seen.add(value)
        result.append(value)

    return result


def upscale_with_oom_retry(
    model: torch.nn.Module,
    rgb: np.ndarray,
    device: torch.device,
    use_half: bool,
    initial_tile: int,
) -> np.ndarray:
    last_error: Exception | None = None

    for tile in _tile_candidates(initial_tile):
        try:
            label = "整图" if tile == 0 else str(tile)
            print(f"\n开始推理：tile = {label}")

            return upscale_x4_tiled(
                model=model,
                rgb=rgb,
                device=device,
                use_half=use_half,
                tile=tile,
            )

        except torch.cuda.OutOfMemoryError as exc:
            last_error = exc

            if device.type != "cuda":
                raise

            print("\nCUDA 显存不足，降低 tile 后重试...")
            torch.cuda.empty_cache()

        except RuntimeError as exc:
            message = str(exc).lower()

            looks_like_oom = (
                device.type == "cuda"
                and "out of memory" in message
            )

            if not looks_like_oom:
                raise

            last_error = exc
            print("\nCUDA 显存不足，降低 tile 后重试...")
            torch.cuda.empty_cache()

    raise RuntimeError(
        f"所有 tile 大小都失败。最后错误：{last_error}"
    )
