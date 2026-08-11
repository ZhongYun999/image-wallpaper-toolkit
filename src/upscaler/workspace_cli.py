from __future__ import annotations

from PIL import Image

from .image_io import reveal_in_file_manager, select_image_interactively
from .workspace import (
    WorkspaceOptions,
    calculate_placement,
    open_workspace_source,
    render_workspace,
    save_workspace,
)


def choose_canvas() -> tuple[int, int, str]:
    print("\n请选择工作画布：")
    print('  1. iPad Pro 13" 1x —— 2064×2752')
    print('  2. iPad Pro 13" 1.5x —— 3096×4128')
    print('  3. iPad Pro 13" 2x —— 4128×5504')
    print('  4. iPad Pro 11" 1x —— 1668×2420')
    print('  5. iPad Pro 11" 2x —— 3336×4840')
    print("  6. 自定义")

    while True:
        choice = input('\n选择 [默认 2 = iPad Pro 13" 1.5x] > ').strip() or "2"
        presets = {
            "1": (2064, 2752, 'iPad Pro 13" 1x'),
            "2": (3096, 4128, 'iPad Pro 13" 1.5x'),
            "3": (4128, 5504, 'iPad Pro 13" 2x'),
            "4": (1668, 2420, 'iPad Pro 11" 1x'),
            "5": (3336, 4840, 'iPad Pro 11" 2x'),
        }
        if choice in presets:
            return presets[choice]
        if choice == "6":
            raw = input("输入画布，例如 3096x4128 > ").strip().lower().replace("×", "x")
            try:
                width_text, height_text = raw.split("x", 1)
                width, height = int(width_text), int(height_text)
                if width <= 0 or height <= 0:
                    raise ValueError
                return width, height, "自定义"
            except ValueError:
                print("格式错误，请输入如 3096x4128。")
                continue
        print("无效选项。")


def choose_scale() -> float:
    print("\n请选择清晰原图缩放：")
    print("  1. 70% —— 很大操作余量")
    print("  2. 80%")
    print("  3. 85% —— 推荐")
    print("  4. 90%")
    print("  5. 100% —— 完整原图刚好放入画布")
    print("  6. 120% —— 主动放大 / 允许裁切")
    print("  7. 自定义")

    fixed = {"1": 0.70, "2": 0.80, "3": 0.85, "4": 0.90, "5": 1.00, "6": 1.20}
    while True:
        choice = input("\n选择 [默认 3 = 85%] > ").strip() or "3"
        if choice in fixed:
            return fixed[choice]
        if choice == "7":
            try:
                percent = float(input("输入百分比，例如 82 / 110 / 145 > "))
                if percent <= 0:
                    raise ValueError
                return percent / 100.0
            except ValueError:
                print("请输入大于 0 的数字。")
                continue
        print("无效选项。")


def choose_offset(canvas_width: int, canvas_height: int) -> tuple[int, int]:
    print("\n请输入清晰原图位移。")
    print("正 X = 向右，负 X = 向左；正 Y = 向下，负 Y = 向上。")
    while True:
        try:
            raw_x = input(f"X 位移 px [默认 0；画布宽 {canvas_width}] > ").strip()
            raw_y = input(f"Y 位移 px [默认 0；画布高 {canvas_height}] > ").strip()
            return int(raw_x or "0"), int(raw_y or "0")
        except ValueError:
            print("位移必须是整数像素。")


def choose_blur() -> float:
    print("\n请选择扩展区域模糊：")
    print("  1. 32 px")
    print("  2. 64 px —— 推荐")
    print("  3. 96 px")
    print("  4. 128 px —— 适合 1.5x/2x 大画布")
    print("  5. 自定义")
    fixed = {"1": 32.0, "2": 64.0, "3": 96.0, "4": 128.0}
    while True:
        choice = input("\n选择 [默认 2] > ").strip() or "2"
        if choice in fixed:
            return fixed[choice]
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


def choose_extension_mode() -> str:
    print("\n请选择边缘填充方式：")
    print("  1. reflect —— 镜像延展，推荐")
    print("  2. edge —— 复制最邻近边缘")
    while True:
        choice = input("\n选择 [默认 1] > ").strip() or "1"
        if choice == "1":
            return "reflect"
        if choice == "2":
            return "edge"
        print("无效选项。")


def choose_brightness() -> float:
    print("\n请选择扩展区域亮度：")
    print("  1. 100% —— 推荐")
    print("  2. 90%")
    print("  3. 80%")
    print("  4. 自定义")
    fixed = {"1": 1.00, "2": 0.90, "3": 0.80}
    while True:
        choice = input("\n选择 [默认 1] > ").strip() or "1"
        if choice in fixed:
            return fixed[choice]
        if choice == "4":
            try:
                percent = float(input("输入百分比，例如 95 > "))
                if percent <= 0:
                    raise ValueError
                return percent / 100.0
            except ValueError:
                print("请输入大于 0 的数字。")
                continue
        print("无效选项。")


def choose_seam_blend() -> int:
    print("\n请选择接缝融合宽度：")
    print("  1. 0 px —— 不融合")
    print("  2. 24 px —— 很窄，接近旧 iOS 的轻度过渡")
    print("  3. 40 px —— 推荐起步")
    print("  4. 64 px")
    print("  5. 96 px —— 更柔和")
    print("  6. 自定义")
    fixed = {"1": 0, "2": 24, "3": 40, "4": 64, "5": 96}
    while True:
        choice = input("\n选择 [默认 3] > ").strip() or "3"
        if choice in fixed:
            return fixed[choice]
        if choice == "6":
            try:
                value = int(input("输入融合宽度 px > "))
                if value < 0:
                    raise ValueError
                return value
            except ValueError:
                print("请输入大于等于 0 的整数。")
                continue
        print("无效选项。")


def run_workspace_builder() -> None:
    print("=" * 72)
    print(" Wallpaper Workspace v0.4.1")
    print(" 自由缩放 + 自由平移 + 自动模糊填边 + 窄幅接缝融合")
    print("=" * 72)

    path = select_image_interactively()
    source, icc_profile = open_workspace_source(path)

    print("\n" + "-" * 72)
    print(f"文件      : {path.name}")
    print(f"原始分辨率: {source.width} × {source.height}")
    print("-" * 72)

    canvas_w, canvas_h, canvas_label = choose_canvas()
    scale = choose_scale()
    offset_x, offset_y = choose_offset(canvas_w, canvas_h)
    blur_radius = choose_blur()
    extension_mode = choose_extension_mode()
    brightness = choose_brightness()
    seam_blend_px = choose_seam_blend()

    options = WorkspaceOptions(
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        blur_radius=blur_radius,
        background_brightness=brightness,
        extension_mode=extension_mode,
        seam_blend_px=seam_blend_px,
    )

    try:
        placement = calculate_placement(source.width, source.height, options)
    except ValueError as exc:
        print(f"\n参数无效：{exc}")
        print("请重新运行并减小位移或调整缩放。")
        return

    print("\n" + "=" * 72)
    print("参数确认：")
    print(f"  工作画布  : {canvas_label} {canvas_w}×{canvas_h}")
    print(f"  原图缩放  : {scale * 100:.1f}% (相对 contain)")
    print(f"  实际清晰图: {placement.image_width}×{placement.image_height}")
    print(f"  摆放坐标  : x={placement.x}, y={placement.y}")
    print(f"  用户位移  : x={offset_x}, y={offset_y}")
    print(
        "  暴露边距  : "
        f"左 {placement.exposed_left}px / 上 {placement.exposed_top}px / "
        f"右 {placement.exposed_right}px / 下 {placement.exposed_bottom}px"
    )
    print(f"  填充方式  : {extension_mode}")
    print(f"  模糊半径  : {blur_radius:g}px")
    print(f"  扩展亮度  : {brightness * 100:g}%")
    print(f"  接缝融合  : {seam_blend_px}px")
    print("  生成式 AI : 不使用")
    print("=" * 72)

    if placement.effective_scale > 1.0:
        print(
            "\n[画质提醒] 当前清晰层需要把源图放大到 "
            f"{placement.effective_scale:.2f}x。"
        )
        print(
            "这一步只是 Lanczos 几何缩放。如果希望放大后保留更多细节，"
            "建议先用主菜单的 AI 超分生成高分辨率母版，再送进 Workspace。"
        )

    if seam_blend_px > 0:
        print(
            "\n[接缝说明] 只会柔化真正接壤扩展区的边缘。"
            "若仍明显可提高到 64~96px；若太软可降到 24px。"
        )

    if input("\n按 Enter 开始；输入 q 取消 > ").strip().lower() == "q":
        print("已取消。")
        return

    result, _ = render_workspace(source, options)
    output_path = save_workspace(result, path, icc_profile)

    with Image.open(output_path) as check:
        final_size = check.size

    print("\n" + "=" * 72)
    print("处理完成。")
    print(f"输出文件  : {output_path}")
    print(f"最终分辨率: {final_size[0]} × {final_size[1]}")
    print("使用方式  : 把这张母版传到 iPad，在系统壁纸界面继续双指缩放 / 拖动取景。")
    print("=" * 72)

    reveal_in_file_manager(output_path)
