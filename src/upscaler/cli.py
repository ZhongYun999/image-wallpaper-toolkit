from __future__ import annotations

import os
import sys

import torch
from PIL import Image

from .config import DEFAULT_TILE, MODELS, NATIVE_SCALE
from .image_io import (
    load_image,
    reveal_in_file_manager,
    save_png,
    select_image_interactively,
)
from .inference import upscale_with_oom_retry
from .sizing import (
    TargetSize,
    fit_inside,
    from_long_edge,
    from_scale,
    ipad_pro_11,
    ipad_pro_13,
)
from .weights import load_model


def human_mp(pixels: int) -> str:
    return f"{pixels / 1_000_000:.2f} MP"


def print_environment(device: torch.device) -> None:
    print("=" * 68)
    print(" Local Image Super Resolution")
    print("=" * 68)
    print(f"Python : {sys.version.split()[0]}")
    print(f"PyTorch: {torch.__version__}")
    print(f"Device : {device}")

    if device.type == "cuda":
        index = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(index)

        print(f"GPU    : {torch.cuda.get_device_name(index)}")
        print(f"VRAM   : {props.total_memory / 1024**3:.1f} GB")
        print(f"CUDA   : {torch.version.cuda}")
    else:
        print("提示：未检测到 CUDA，将使用 CPU，速度会明显更慢。")


def choose_target(width: int, height: int) -> TargetSize:
    print("\n请选择目标尺寸：")
    print("  1.  1x   —— 尺寸不变，仅 AI 恢复")
    print("  2.  1.5x")
    print("  3.  2x")
    print("  4.  3x")
    print("  5.  4x   —— 模型原生输出")
    print('  6.  iPad Pro 13" —— 2064×2752 目标框')
    print('  7.  iPad Pro 11" —— 1668×2420 目标框')
    print("  8.  2K —— 长边 2560")
    print("  9.  4K —— 长边 3840")
    print(" 10.  自定义倍数")
    print(" 11.  自定义长边")
    print(" 12.  自定义目标框")

    while True:
        choice = input("\n选择 [默认 3 = 2x] > ").strip() or "3"

        fixed_scales = {
            "1": 1.0,
            "2": 1.5,
            "3": 2.0,
            "4": 3.0,
            "5": 4.0,
        }

        if choice in fixed_scales:
            scale = fixed_scales[choice]
            label = "1x 尺寸不变增强" if scale == 1 else f"{scale:g}x"
            return from_scale(width, height, scale, label)

        if choice == "6":
            return ipad_pro_13(width, height)

        if choice == "7":
            return ipad_pro_11(width, height)

        if choice == "8":
            return from_long_edge(width, height, 2560, "2K（长边 2560）")

        if choice == "9":
            return from_long_edge(width, height, 3840, "4K（长边 3840）")

        if choice == "10":
            try:
                scale = float(input("输入倍率，例如 1.9 / 2 / 3.5 > "))
                return from_scale(width, height, scale)
            except ValueError:
                print("倍率必须是大于 0 的数字。")
                continue

        if choice == "11":
            try:
                edge = int(input("输入目标长边，例如 2752 / 3840 > "))
                return from_long_edge(width, height, edge)
            except ValueError:
                print("长边必须是正整数。")
                continue

        if choice == "12":
            raw = (
                input("输入目标框，例如 2064x2752 > ")
                .strip()
                .lower()
                .replace("×", "x")
            )

            try:
                box_w_text, box_h_text = raw.split("x", 1)
                box_w = int(box_w_text)
                box_h = int(box_h_text)
                return fit_inside(width, height, box_w, box_h)
            except (ValueError, TypeError):
                print("格式错误，请输入如 2064x2752。")
                continue

        print("无效选项，请重新输入。")


def choose_model():
    print("\n请选择模型：")

    for key, spec in MODELS.items():
        print(f"  {key}. {spec.label}  [{spec.name}]")

    choice = input("\n选择 [默认 1] > ").strip() or "1"

    if choice not in MODELS:
        print("无效选项，使用默认动漫 / 插画模型。")
        choice = "1"

    return MODELS[choice]


def choose_tile(model_blocks: int) -> int:
    default = 384 if model_blocks >= 23 else DEFAULT_TILE

    print("\nTile 分块：")
    print("  0   = 整图一次推理（最吃显存）")
    print("  512 = 默认推荐")
    print("  256 = 更省显存")

    raw = input(f"Tile [默认 {default}] > ").strip()

    if not raw:
        return default

    try:
        tile = int(raw)
        if tile < 0:
            raise ValueError
        return tile
    except ValueError:
        print(f"输入无效，使用默认 {default}。")
        return default


def main() -> None:
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    use_half = device.type == "cuda"

    try:
        print_environment(device)

        path = select_image_interactively()
        image = load_image(path)

        print("\n" + "-" * 68)
        print(f"文件      : {image.path.name}")
        print(f"原始模式  : {image.original_mode}")
        print(f"原始分辨率: {image.width} × {image.height}")
        print(f"原始像素量: {human_mp(image.width * image.height)}")
        print(f"宽高比    : {image.width / image.height:.6f}")
        print("-" * 68)

        target = choose_target(image.width, image.height)

        print("\n目标计算：")
        print(f"  预设      : {target.label}")
        print(f"  原始      : {image.width} × {image.height}")
        print(f"  目标      : {target.width} × {target.height}")
        print(
            f"  宽倍率    : {target.width / image.width:.4f}x"
        )
        print(
            f"  高倍率    : {target.height / image.height:.4f}x"
        )
        print(
            "  像素量    : "
            f"{human_mp(image.width * image.height)}"
            " -> "
            f"{human_mp(target.width * target.height)}"
        )

        if target.scale > NATIVE_SCALE:
            print("\n[提醒] 目标超过 4x。")
            print("AI 网络只负责到原生 4x，超过部分使用 Lanczos。")

        model_spec = choose_model()
        tile = choose_tile(model_spec.blocks)

        print("\n" + "=" * 68)
        print("即将开始：")
        print(f"  输入 : {image.path}")
        print(f"  模型 : {model_spec.name}")
        print(f"  目标 : {target.width} × {target.height}")
        print(f"  Tile : {'整图' if tile == 0 else tile}")
        print(f"  精度 : {'FP16' if use_half else 'FP32'}")
        print("=" * 68)

        if input("\n按 Enter 开始；输入 q 取消 > ").strip().lower() == "q":
            print("已取消。")
            return

        model = load_model(model_spec, device, use_half)

        sr_rgb_x4 = upscale_with_oom_retry(
            model=model,
            rgb=image.rgb,
            device=device,
            use_half=use_half,
            initial_tile=tile,
        )

        output_path = save_png(
            rgb=sr_rgb_x4,
            alpha=image.alpha,
            target_width=target.width,
            target_height=target.height,
            source_path=image.path,
            icc_profile=image.icc_profile,
        )

        with Image.open(output_path) as check:
            final_w, final_h = check.size

        print("\n" + "=" * 68)
        print("处理完成。")
        print(f"输出文件  : {output_path}")
        print(f"最终分辨率: {final_w} × {final_h}")
        print(f"最终像素量: {human_mp(final_w * final_h)}")
        print("=" * 68)

        reveal_in_file_manager(output_path)

    except KeyboardInterrupt:
        print("\n\n用户中断。")

    except Exception as exc:
        print("\n\n[错误]")
        print(f"{type(exc).__name__}: {exc}")

        print("\n如果是 CUDA / PyTorch 环境问题，可先运行：")
        print(
            'python -c "import torch; '
            'print(torch.cuda.is_available()); '
            'print(torch.cuda.get_device_name(0) '
            'if torch.cuda.is_available() else \'CPU\')"'
        )

        raise


if __name__ == "__main__":
    main()
