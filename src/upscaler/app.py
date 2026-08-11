from __future__ import annotations

from .cli import main as run_super_resolution
from .wallpaper_cli import run_wallpaper_builder
from .workspace_cli import run_workspace_builder


def main() -> None:
    print("=" * 68)
    print(" Image / Wallpaper Toolkit")
    print("=" * 68)
    print("请选择功能：")
    print("  1. AI 超分（Real-ESRGAN）")
    print("  2. iOS 风格边缘扩展（v0.3：固定边缘扩展）")
    print("  3. Wallpaper Workspace（v0.4：自由缩放 / 平移 / 自动模糊填边）")

    while True:
        choice = input("\n选择 [默认 3] > ").strip() or "3"

        if choice == "1":
            run_super_resolution()
            return

        if choice == "2":
            run_wallpaper_builder()
            return

        if choice == "3":
            run_workspace_builder()
            return

        print("无效选项，请重新输入。")


if __name__ == "__main__":
    main()
