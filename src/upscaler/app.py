from __future__ import annotations

from .cli import main as run_super_resolution
from .workspace_cli import run_workspace_builder


def main() -> None:
    print("=" * 68)
    print(" Image / Wallpaper Toolkit")
    print("=" * 68)
    print("请选择功能：")
    print("  1. AI 超分（Real-ESRGAN）")
    print("  2. Wallpaper Workspace（缩放 / 平移 / 模糊填边 / 接缝融合 / 显示校准）")

    while True:
        choice = input("\n选择 [默认 2] > ").strip() or "2"

        if choice == "1":
            run_super_resolution()
            return

        if choice == "2":
            run_workspace_builder()
            return

        print("无效选项，请重新输入。")


if __name__ == "__main__":
    main()
