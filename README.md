# Image Super Resolution

一个面向本地 GPU 的交互式图片超分小项目，默认使用 **Real-ESRGAN** 的官方 x4 权重。

这个项目刻意拆成多个职责明确的模块，方便阅读和学习，而不是把所有逻辑塞进一个脚本。

## 功能

- 控制台选择图片或输入路径
- 显示原始分辨率、像素量、宽高比
- 预设输出：
  - 1x / 1.5x / 2x / 3x / 4x
  - iPad Pro 13"：2064×2752 目标框
  - iPad Pro 11"：1668×2420 目标框
  - 2K：长边 2560
  - 4K：长边 3840
  - 自定义倍率 / 长边 / 目标框
- 两种模型：
  - `RealESRGAN_x4plus_anime_6B`：动漫 / 插画，默认
  - `RealESRGAN_x4plus`：照片 / 通用
- CUDA + FP16
- Tile 分块推理
- CUDA OOM 时自动减小 tile 重试
- RGBA 图片保留 Alpha
- 最终输出 PNG，并核对实际分辨率

## 设计原则

Real-ESRGAN 这里使用的是 **原生 x4 网络**。

例如输入 `1086×1448`，选择 iPad Pro 13"：

1. AI 网络先得到 `4344×5792`
2. 再用 Lanczos 缩小到 `2064×2752`

因此：

- 2x 并不是另一个“2x 神经网络”
- 1.9x 也不是“1.9x 神经网络”
- AI 负责恢复细节
- 最后的 Lanczos 负责精确落到用户要求的像素尺寸

这比扩散模型重新绘图更适合“保持原图不变”的超分需求。

---

## 目录结构

```text
image-super-resolution/
├─ run.py
├─ pyproject.toml
├─ requirements.txt
├─ README.md
├─ docs/
│  └─ ARCHITECTURE.md
├─ src/
│  └─ upscaler/
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ cli.py
│     ├─ config.py
│     ├─ sizing.py
│     ├─ weights.py
│     ├─ model_arch.py
│     ├─ image_io.py
│     └─ inference.py
└─ tests/
   └─ test_sizing.py
```

## 环境

最低依赖：

```bash
pip install torch pillow numpy
```

如果已经有配置好的 CUDA PyTorch，**不要为了这个项目重新覆盖安装 torch**。

先检查：

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 运行方式 A：直接运行

在项目根目录：

```bash
python run.py
```

这是最省事的方式。

## 运行方式 B：作为 Python 项目安装

```bash
pip install -e .
```

然后：

```bash
upscaler
```

或者：

```bash
python -m upscaler
```

## 推荐设置

对于动漫壁纸：

```text
模型：RealESRGAN_x4plus_anime_6B
Tile：512
```

如果显存不足，程序会自动尝试：

```text
512 -> 384 -> 256 -> 192 -> 128
```

## 模型权重

首次运行时自动下载官方 `.pth` 权重到：

```text
weights/
```

权重文件不会被包含进项目压缩包。

## 输出

如果输入：

```text
wallpaper.png
```

目标：

```text
2064×2752
```

输出类似：

```text
wallpaper_SR_2064x2752.png
```

保存在原图旁边。

## 学习顺序

如果你想读代码，建议按这个顺序：

1. `sizing.py`
   - 最纯粹，负责“目标尺寸怎么算”
2. `cli.py`
   - 看控制台交互怎样组织
3. `image_io.py`
   - 看 Pillow 如何读取 / 保存图片
4. `weights.py`
   - 看模型权重如何下载和加载
5. `model_arch.py`
   - 看 RRDBNet 网络结构
6. `inference.py`
   - 看真正的 tile 超分流程

详细调用链见 `docs/ARCHITECTURE.md`。


---

## v0.2：Wallpaper Blur Fill

现在运行：

```bash
python run.py
```

首先会看到：

```text
1. AI 超分（Real-ESRGAN）
2. 壁纸模糊填充（不使用生成式 AI）
```

第二项用于：

- 缩小清晰原图
- 把主体放到画面下方
- 用原图自身生成模糊背景补边
- 给 iPad 锁屏时间 / 日期留出顶部空间
- 避免扩散模型重新绘制人物

详细说明：

```text
docs/WALLPAPER_BLUR_FILL.md
```
