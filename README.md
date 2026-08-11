# Image Wallpaper Toolkit

一个面向本地 GPU 的交互式图片超分与壁纸工作画布工具。

目前项目保留两个核心功能：

```text
1. AI 超分（Real-ESRGAN）
2. Wallpaper Workspace
```

其中 `Wallpaper Workspace` 是当前推荐的壁纸处理入口，支持：

- 自由缩放清晰原图
- 自由上下左右平移
- 根据暴露区域自动做 `reflect` / `edge` 边缘延展
- 对扩展区域应用高斯模糊
- 使用接缝融合减少清晰原图与模糊延展之间的矩形边界感
- 导出可继续在 iPad 壁纸界面缩放 / 拖动的高余量母版

## 目录结构

```text
image-wallpaper-toolkit/
├─ run.py
├─ pyproject.toml
├─ requirements.txt
├─ README.md
├─ docs/
│  ├─ ARCHITECTURE.md
│  ├─ WALLPAPER_WORKSPACE_V04.md
│  └─ WALLPAPER_WORKSPACE_V041_SEAM_BLENDING.md
├─ src/
│  └─ upscaler/
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ app.py
│     ├─ cli.py
│     ├─ config.py
│     ├─ sizing.py
│     ├─ weights.py
│     ├─ model_arch.py
│     ├─ image_io.py
│     ├─ inference.py
│     ├─ workspace.py
│     └─ workspace_cli.py
└─ tests/
   ├─ test_sizing.py
   └─ test_workspace.py
```

## 环境

最低依赖：

```bash
pip install torch pillow numpy
```

如果已经有配置好的 CUDA PyTorch，建议保留现有环境，不要为了这个项目重新覆盖安装 `torch`。

先检查：

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 运行

项目根目录：

```bash
python run.py
```

主菜单：

```text
1. AI 超分（Real-ESRGAN）
2. Wallpaper Workspace
```

也可以安装为可编辑项目：

```bash
pip install -e .
upscaler
```

## 推荐工作流

如果源图分辨率已经足够高：

```text
原图
 ↓
Wallpaper Workspace
 ↓
导出工作母版
 ↓
iPad 壁纸界面继续缩放 / 平移
```

如果准备在 iPad 中继续较大幅度放大：

```text
原图
 ↓
AI 超分
 ↓
高分辨率 PNG
 ↓
Wallpaper Workspace
 ↓
导出工作母版
```

## AI 超分

Real-ESRGAN 使用原生 x4 网络。

例如输入 `1086×1448`，如果目标是 iPad Pro 13" 的 `2064×2752`：

```text
1086×1448
 ↓ Real-ESRGAN x4
4344×5792
 ↓ Lanczos 精确缩放
2064×2752
```

因此 2x、1.9x 等目标尺寸并不是另一套神经网络，而是先完成 x4 AI 重建，再缩放到最终像素尺寸。

## Wallpaper Workspace

`scale`：相对于 contain-fit 的缩放倍率。

`offset_x / offset_y`：相对于居中位置的像素位移。

`extension_mode`：`reflect` 或 `edge`。

`blur_radius`：扩展区域的高斯模糊强度。

`seam_blend_px`：清晰原图和模糊扩展区之间的局部融合宽度。

如果希望接近旧 iOS 自动填充的视觉效果，实际使用中通常需要让融合带有一定宽度，可以从：

```text
40 px → 64 px → 96 px
```

逐步测试；如果主体边缘被柔化过多，再往回减小。

详细说明：

```text
docs/WALLPAPER_WORKSPACE_V04.md
docs/WALLPAPER_WORKSPACE_V041_SEAM_BLENDING.md
```

## 代码阅读顺序

建议：

```text
sizing.py
  ↓
cli.py
  ↓
image_io.py
  ↓
weights.py
  ↓
model_arch.py
  ↓
inference.py
  ↓
workspace.py
  ↓
workspace_cli.py
```

其中：

- `workspace.py`：壁纸工作画布核心算法
- `workspace_cli.py`：工作画布控制台交互
- `inference.py`：Real-ESRGAN 分块推理
