# 项目结构与调用链

这个项目最重要的目的之一，是把“超分脚本”拆成几个容易理解的层次。

---

## 1. `cli.py`：控制流程

这是程序入口。

它负责：

1. 检查 CUDA
2. 让用户选择图片
3. 显示原始分辨率
4. 让用户选择目标尺寸
5. 让用户选择模型和 tile
6. 调用模型加载
7. 调用 AI 超分
8. 保存结果

它本身不关心：

- RRDB 网络内部怎么工作
- 权重怎么下载
- tile 如何拼接
- 图片怎么保存

这就是“分层”。

---

## 2. `sizing.py`：只管尺寸数学

例如：

```python
target = from_scale(1086, 1448, 2)
```

得到：

```text
2172 × 2896
```

而：

```python
target = ipad_pro_13(1086, 1448)
```

得到：

```text
2064 × 2752
```

这部分完全不依赖 PyTorch，可以单独测试。

---

## 3. `image_io.py`：只管图片 I/O

读取时：

```text
Pillow Image
    ↓
RGB numpy array
    ↓
交给 PyTorch
```

RGBA 图片会把 Alpha 单独保存。

超分结束后：

```text
AI 得到 RGB
    +
Lanczos 放大的 Alpha
    ↓
RGBA PNG
```

---

## 4. `model_arch.py`：网络结构

这里定义：

```text
ResidualDenseBlock
        ↓
       RRDB
        ↓
      RRDBNet
```

大致关系：

```text
输入 RGB
  │
  ▼
conv_first
  │
  ▼
多个 RRDB
  │
  ├──── 残差连接
  ▼
2x nearest + conv
  │
  ▼
2x nearest + conv
  │
  ▼
最终卷积
  │
  ▼
4x RGB
```

Real-ESRGAN 的 x4 模型并不是直接把最终宽高写成 4 倍，
而是连续做两次 2x 上采样。

---

## 5. `weights.py`：模型参数

网络结构只是“空壳”。

`.pth` 权重才包含训练后得到的大量卷积参数。

流程：

```text
如果本地没有 .pth
        ↓
下载官方权重
        ↓
torch.load()
        ↓
load_state_dict()
        ↓
把参数装进 RRDBNet
```

---

## 6. `inference.py`：真正处理图片

如果直接把一张大图一次塞进 GPU：

```text
整图
 ↓
RRDBNet
 ↓
4x 大图
```

可能显存爆掉。

所以默认分块：

```text
原图
 ├─ tile 1
 ├─ tile 2
 ├─ tile 3
 └─ tile 4
```

每块周围还会额外带一点 `tile_pad`。

原因是卷积网络在 tile 边缘缺少邻域信息，
如果完全硬切，拼回去以后容易出现接缝。

因此实际是：

```text
      padding
   ┌──────────┐
   │ ┌──────┐ │
   │ │有效块│ │
   │ └──────┘ │
   └──────────┘
```

网络处理完整 padding 区域，
但最终只把中间“有效块”放进输出图。

---

## 7. 为什么 2x 还要先做 4x？

这个项目使用的是官方 x4 权重。

假设原图：

```text
1086 × 1448
```

模型原生输出：

```text
4344 × 5792
```

但用户只要：

```text
2064 × 2752
```

所以流程是：

```text
1086 × 1448
     │
     │ Real-ESRGAN x4
     ▼
4344 × 5792
     │
     │ Lanczos
     ▼
2064 × 2752
```

这看起来有点“绕”，但有两个优势：

1. 神经网络在更高分辨率空间重建细节
2. 最终缩小可以抑制一部分 AI 锐化伪影

对于动漫壁纸尤其适合。

---

## 8. 最值得你动手改的地方

### 增加新的尺寸预设

改：

```text
sizing.py
cli.py
```

例如加入：

```python
def wallpaper_3000(src_w, src_h):
    return from_long_edge(src_w, src_h, 3000)
```

### 改默认 tile

改：

```text
config.py
```

### 增加 JPG 输出

改：

```text
image_io.py
```

### 以后加 GUI

完全可以保留：

```text
sizing.py
weights.py
model_arch.py
inference.py
image_io.py
```

只需要把：

```text
cli.py
```

换成：

```text
gui.py
```

这也是现在拆项目而不是写一个 700 行单文件的价值。
