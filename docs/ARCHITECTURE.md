# 项目结构与调用链

项目现在保留两条主路径：

```text
run.py / python -m upscaler / upscaler
                ↓
              app.py
        ┌───────┴────────┐
        ↓                ↓
   AI 超分            Workspace
     cli.py          workspace_cli.py
        ↓                ↓
 inference.py        workspace.py
```

`app.py` 只负责主菜单分流，具体算法都放在独立模块里。

---

## 1. `app.py`：项目总入口

主菜单目前只有：

```text
1. AI 超分（Real-ESRGAN）
2. Wallpaper Workspace
```

这样旧的固定边缘扩展路径已经移除，避免同一个目标保留两套业务流程。

---

## 2. AI 超分路径

### `cli.py`

负责：

1. 检查 CUDA
2. 选择图片
3. 显示原始分辨率
4. 选择目标尺寸
5. 选择模型与 tile
6. 调用权重加载
7. 调用 Real-ESRGAN 推理
8. 保存输出

### `sizing.py`

只负责尺寸数学，例如：

```python
target = from_scale(1086, 1448, 2)
```

得到：

```text
2172 × 2896
```

### `model_arch.py`

网络结构：

```text
ResidualDenseBlock
        ↓
       RRDB
        ↓
      RRDBNet
```

Real-ESRGAN x4 网络通过两次 2x 上采样得到最终 4x 输出。

### `weights.py`

负责：

```text
检查本地权重
    ↓
必要时下载官方 .pth
    ↓
torch.load()
    ↓
load_state_dict()
```

### `inference.py`

负责真正的 GPU 推理以及 tile 分块。

大图不会强制一次全部塞入显存，而是：

```text
原图
 ├─ tile 1
 ├─ tile 2
 ├─ tile 3
 └─ tile 4
```

每块还会保留 `tile_pad`，减少拼接接缝。

---

## 3. Wallpaper Workspace 路径

### `workspace_cli.py`

只负责交互参数：

- 工作画布大小
- 清晰原图 `scale`
- `offset_x / offset_y`
- 模糊半径
- `reflect / edge` 填充方式
- 扩展区亮度
- `seam_blend_px` 接缝融合宽度

然后组织为：

```python
WorkspaceOptions(...)
```

并交给 `workspace.py`。

### `workspace.py`

这是当前壁纸功能的核心算法。

流程：

```text
原图 / 超分母版
      ↓
contain-fit × scale
      ↓
按 offset_x / offset_y 摆放
      ↓
根据当前暴露区域自动延展边缘
      ↓
Gaussian Blur
      ↓
局部 seam blending
      ↓
导出工作母版 PNG
```

关键点有两个：

1. 清晰原图是真正可缩放、可平移的对象，不再通过固定裁切区域间接控制构图。
2. 接缝融合只作用于和扩展区真正接壤的边缘，主体中心仍保持清晰。

---

## 4. `image_io.py`：公共图片 I/O

负责 Pillow 图片读取、保存以及文件选择等公共逻辑。

AI 超分路径和 Workspace 路径都会复用其中的部分功能。

---

## 5. 推荐学习顺序

如果主要想理解项目结构：

```text
app.py
  ↓
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

如果主要想研究壁纸效果，可以直接从：

```text
workspace.py
  ↓
workspace_cli.py
```

开始。

---

## 6. 后续扩展方向

现在底层算法已经和交互层分开，因此以后加入 GUI 时不需要重写 Workspace 算法。

比较自然的下一步是新增：

```text
workspace_gui.py
```

让 GUI 直接调用现有：

```python
render_workspace(...)
```

即可实现实时预览、鼠标拖动和滑杆缩放。
