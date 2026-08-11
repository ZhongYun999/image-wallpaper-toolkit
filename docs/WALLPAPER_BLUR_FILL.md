# 壁纸模糊填充模块

这一模块的目标不是“AI 扩图”，而是复现类似旧版 iOS / iPadOS 壁纸中常见的：

> 缩小原图后，用同一张图生成模糊背景来填满边缘。

## 核心原则

清晰主体层不经过扩散模型。

```text
源图
 ├─> cover 放大 -> 高斯模糊 -> 变暗 -> 背景层
 │
 └─> 原图 / Lanczos 缩放 -> 边缘羽化 -> 清晰前景层
                                      │
                                      ▼
                                合成固定画布
```

因此不会发生：

- 人脸被重新生成
- 衣服纹理被重画
- 飘带位置改变
- 花瓣数量被模型猜测

如果选择“原始像素 1:1”，清晰前景甚至不会进行 Lanczos 缩放。

---

## 新增文件

把以下三个文件放入：

```text
src/upscaler/
```

```text
app.py
wallpaper.py
wallpaper_cli.py
```

其中：

### `wallpaper.py`

纯图像处理算法。

不负责控制台，不负责 PyTorch。

主要函数：

```python
make_blurred_background()
prepare_foreground()
render_wallpaper()
save_wallpaper()
```

### `wallpaper_cli.py`

只负责控制台交互：

- 目标画布
- 前景大小
- 上下位置
- 左右位置
- 模糊半径
- 背景亮度
- 羽化范围

最终把参数组织成：

```python
WallpaperOptions(...)
```

然后调用：

```python
render_wallpaper(...)
```

### `app.py`

成为整个项目的新总入口：

```text
1. AI 超分
2. 壁纸模糊填充
```

它只负责把用户分流到旧的 `cli.py` 或新的 `wallpaper_cli.py`。

---

# 需要修改的旧文件

## 1. `run.py`

原先：

```python
from upscaler.cli import main
```

改成：

```python
from upscaler.app import main
```

## 2. `src/upscaler/__main__.py`

原先：

```python
from .cli import main
```

改成：

```python
from .app import main
```

## 3. `pyproject.toml`

原先：

```toml
upscaler = "upscaler.cli:main"
```

改成：

```toml
upscaler = "upscaler.app:main"
```

这样：

```bash
python run.py
```

和：

```bash
upscaler
```

都会先打开总菜单。

---

# 推荐参数：人物在右下、顶部需要给锁屏时间留白

对于类似动漫人物壁纸，可以先试：

```text
画布：
iPad Pro 13" 2064×2752

清晰前景：
85%

垂直位置：
靠下（95%）

水平位置：
居中

背景模糊：
64px

背景亮度：
85%

边缘羽化：
48px
```

如果顶部仍然不够：

1. 先把前景从 85% 调到 80%
2. 再把垂直位置设为 100% 靠底
3. 不要先把模糊调得特别大

真正决定顶部留白的是：

```text
前景尺寸 + 垂直位置
```

而不是模糊半径。

---

# “最严格保真”与“视觉更好”是两件事

## 原始像素 1:1

```text
不缩放清晰前景
```

优点：

- 源图前景像素完全不做几何插值

缺点：

- 如果源图只有 1086×1448，而画布是 2064×2752，
  前景会明显偏小。

## 85% / 90% 模式

会对清晰前景做 Lanczos 缩放。

这不是生成式 AI，不会重新画角色，但严格来说输出像素会经过插值。

如果希望：

> 既有较大的清晰前景，又尽量减少普通插值带来的软化

最合理的流程是：

```text
原图
  ↓
Real-ESRGAN 只做一次超分
  ↓
得到高分辨率“母版”
  ↓
Wallpaper Blur Fill
  ↓
缩小并摆放到 iPad 画布
```

这与“先让扩散模型生成一张新图”完全不同。

---

# 为什么要羽化

如果直接把矩形原图贴到模糊背景：

```text
模糊背景 | 清晰矩形
```

很容易看见矩形边界。

羽化会让清晰层在边缘逐渐透明：

```text
清晰 ██████████
     ██████████
     ▓▓▓▓▓▓▓▓▓▓
     ▒▒▒▒▒▒▒▒▒▒
     ░░░░░░░░░░
模糊背景
```

对于暗色壁纸，通常 32~64 px 已经足够。

---

# 后续可以扩展什么

这个模块故意没有加入 AI。

比较适合继续练习的功能：

- 实时预览窗口
- 鼠标拖动前景位置
- 滑杆控制模糊 / 亮度
- 锁屏时间安全区叠加线
- 同时导出 11" / 13" 多种尺寸
- 只向上扩展而不是四周都留边
