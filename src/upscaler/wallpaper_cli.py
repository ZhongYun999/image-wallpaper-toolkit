from __future__ import annotations

from PIL import Image

from .image_io import reveal_in_file_manager, select_image_interactively
from .wallpaper import (
    WallpaperOptions,
    open_source_image,
    render_wallpaper,
    save_wallpaper,
)


def choose_canvas() -> tuple[int, int, str]:
    print("\n请选择目标画布：")
    print('  1. iPad Pro 13" 竖屏 —— 2064×2752')
    print('  2. iPad Pro 11" 竖屏 —— 1668×2420')
    print("  3. 4K 竖屏 —— 2160×3840")
    print("  4. 自定义")

    while True:
        choice = input("\n选择 [默认 1] > ").strip() or "1"

        if choice == "1":
            return 2064, 2752, 'iPad Pro 13"'

        if choice == "2":
            return 1668, 2420, 'iPad Pro 11"'

        if choice == "3":
            return 2160, 3840, "4K 竖屏"

        if choice == "4":
            raw = (
                input("输入画布，例如 2064x2752 > ")
                .strip()
                .lower()
                .replace("×", "x")
            )

            try:
                w, h = raw.split("x", 1)
                w, h = int(w), int(h)

                if w <= 0 or h <= 0:
                    raise ValueError

                return w, h, "自定义"
            except ValueError:
                print("格式错误，请输入如 2064x2752。")
                continue

        print("无效选项。")


def choose_extension(
    canvas_w: int,
    canvas_h: int,
) -> tuple[int, int, int, int, str]:
    print("\n请选择边缘扩展方式：")
    print("  1. 只向上扩展 20%")
    print("  2. 只向上扩展 25% —— 推荐，接近旧 iOS 锁屏效果")
    print("  3. 只向上扩展 30%")
    print("  4. 只向上扩展：自定义像素")
    print("  5. 自定义四边")
    print("  6. 四周各扩展 5%")

    while True:
        choice = input("\n选择 [默认 2] > ").strip() or "2"

        if choice in {"1", "2", "3"}:
            pct = {
                "1": 0.20,
                "2": 0.25,
                "3": 0.30,
            }[choice]

            top = round(canvas_h * pct)
            return top, 0, 0, 0, f"上方 {pct * 100:g}%"

        if choice == "4":
            try:
                top = int(input("输入上方扩展像素 > "))
                if not 0 <= top < canvas_h:
                    raise ValueError
                return top, 0, 0, 0, f"上方 {top}px"
            except ValueError:
                print("必须是 0 到画布高度之间的整数。")
                continue

        if choice == "5":
            try:
                top = int(input("上方 px [默认 0] > ") or "0")
                bottom = int(input("下方 px [默认 0] > ") or "0")
                left = int(input("左侧 px [默认 0] > ") or "0")
                right = int(input("右侧 px [默认 0] > ") or "0")

                if min(top, bottom, left, right) < 0:
                    raise ValueError

                if top + bottom >= canvas_h:
                    raise ValueError

                if left + right >= canvas_w:
                    raise ValueError

                return (
                    top,
                    bottom,
                    left,
                    right,
                    "自定义四边",
                )
            except ValueError:
                print("边距无效：不能为负，也不能占满整个画布。")
                continue

        if choice == "6":
            top = bottom = round(canvas_h * 0.05)
            left = right = round(canvas_w * 0.05)
            return top, bottom, left, right, "四周 5%"

        print("无效选项。")


def choose_focus(axis: str) -> tuple[float, str]:
    if axis == "x":
        print("\n请选择横向裁切焦点：")
        print("  1. 居中")
        print("  2. 偏左")
        print("  3. 偏右")
        labels = {
            "1": (0.50, "居中"),
            "2": (0.35, "偏左"),
            "3": (0.65, "偏右"),
        }
    else:
        print("\n请选择纵向裁切焦点：")
        print("  1. 居中")
        print("  2. 偏上")
        print("  3. 偏下")
        labels = {
            "1": (0.50, "居中"),
            "2": (0.35, "偏上"),
            "3": (0.65, "偏下"),
        }

    print("  4. 自定义 0~100")

    while True:
        choice = input("\n选择 [默认 1] > ").strip() or "1"

        if choice in labels:
            return labels[choice]

        if choice == "4":
            try:
                percent = float(input("输入 0~100 > "))
                if not 0 <= percent <= 100:
                    raise ValueError
                return percent / 100.0, f"{percent:g}%"
            except ValueError:
                print("请输入 0~100。")
                continue

        print("无效选项。")


def choose_blur() -> float:
    print("\n请选择扩展边缘的模糊强度：")
    print("  1. 32 px")
    print("  2. 48 px")
    print("  3. 64 px —— 推荐")
    print("  4. 96 px")
    print("  5. 自定义")

    values = {
        "1": 32.0,
        "2": 48.0,
        "3": 64.0,
        "4": 96.0,
    }

    while True:
        choice = input("\n选择 [默认 3] > ").strip() or "3"

        if choice in values:
            return values[choice]

        if choice == "5":
            try:
                value = float(input("输入模糊半径 px > "))
                if value < 0:
                    raise ValueError
                return value
            except ValueError:
                print("请输入大于等于 0 的数字。")
                continue

        print("无效选项。")


def choose_brightness() -> float:
    print("\n请选择扩展区域亮度：")
    print("  1. 100% —— 推荐，忠于原图")
    print("  2. 90%")
    print("  3. 80%")
    print("  4. 自定义")

    values = {
        "1": 1.00,
        "2": 0.90,
        "3": 0.80,
    }

    while True:
        choice = input("\n选择 [默认 1] > ").strip() or "1"

        if choice in values:
            return values[choice]

        if choice == "4":
            try:
                value = float(input("输入百分比，例如 95 > "))
                if value <= 0:
                    raise ValueError
                return value / 100.0
            except ValueError:
                print("请输入大于 0 的数字。")
                continue

        print("无效选项。")


def run_wallpaper_builder() -> None:
    print("=" * 70)
    print(" iOS-like Edge Extension")
    print(" 原图仍然是主体，只对真正缺失的外边缘做反射 + 模糊填充")
    print("=" * 70)

    path = select_image_interactively()
    source, icc_profile = open_source_image(path)

    print("\n" + "-" * 70)
    print(f"文件      : {path.name}")
    print(f"原始分辨率: {source.width} × {source.height}")
    print("-" * 70)

    canvas_w, canvas_h, canvas_label = choose_canvas()

    top, bottom, left, right, extension_label = choose_extension(
        canvas_w,
        canvas_h,
    )

    focus_x, focus_x_label = choose_focus("x")
    focus_y, focus_y_label = choose_focus("y")

    blur_radius = choose_blur()
    brightness = choose_brightness()

    options = WallpaperOptions(
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        extend_top=top,
        extend_bottom=bottom,
        extend_left=left,
        extend_right=right,
        focus_x=focus_x,
        focus_y=focus_y,
        blur_radius=blur_radius,
        background_brightness=brightness,
    )

    content_w = options.content_width
    content_h = options.content_height

    print("\n" + "=" * 70)
    print("参数确认：")
    print(f"  画布      : {canvas_label} {canvas_w}×{canvas_h}")
    print(f"  扩展      : {extension_label}")
    print(
        "  边距      : "
        f"上 {top} / 下 {bottom} / 左 {left} / 右 {right}"
    )
    print(f"  清晰区域  : {content_w}×{content_h}")
    print(f"  横向焦点  : {focus_x_label}")
    print(f"  纵向焦点  : {focus_y_label}")
    print(f"  边缘模糊  : {blur_radius:g}px")
    print(f"  边缘亮度  : {brightness * 100:g}%")
    print("  生成式 AI : 不使用")
    print("=" * 70)

    if input("\n按 Enter 开始；输入 q 取消 > ").strip().lower() == "q":
        print("已取消。")
        return

    result, fit_info = render_wallpaper(source, options)

    print("\n实际原图变换：")
    print(f"  源图      : {fit_info.source_width}×{fit_info.source_height}")
    print(f"  COVER倍率 : {fit_info.scale:.4f}x")
    print(
        f"  缩放后    : "
        f"{fit_info.resized_width}×{fit_info.resized_height}"
    )
    print(
        f"  裁切起点  : "
        f"x={fit_info.crop_left}, y={fit_info.crop_top}"
    )
    print(
        f"  保留主体  : "
        f"{fit_info.content_width}×{fit_info.content_height}"
    )

    output_path = save_wallpaper(
        result,
        path,
        icc_profile,
    )

    with Image.open(output_path) as check:
        final_size = check.size

    print("\n" + "=" * 70)
    print("处理完成。")
    print(f"输出文件  : {output_path}")
    print(f"最终分辨率: {final_size[0]} × {final_size[1]}")
    print("=" * 70)

    reveal_in_file_manager(output_path)
