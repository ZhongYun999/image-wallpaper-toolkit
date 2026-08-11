# v0.4.1 Cleanup

在实际测试确认 `Wallpaper Workspace` 已经覆盖旧固定边缘扩展模式的主要使用场景后，项目移除旧的 v0.2 / v0.3 壁纸处理路径。

## 删除

- `src/upscaler/wallpaper.py`
- `src/upscaler/wallpaper_cli.py`
- `tests/test_wallpaper.py`
- `docs/IOS_EDGE_EXTENSION.md`
- `docs/WALLPAPER_BLUR_FILL.md`

## 主菜单

由：

```text
1. AI 超分
2. iOS 风格边缘扩展
3. Wallpaper Workspace
```

简化为：

```text
1. AI 超分
2. Wallpaper Workspace
```

`Wallpaper Workspace` 成为唯一的壁纸构图 / 填边主路径。

## 保留

- Real-ESRGAN 超分流程
- Workspace 自由缩放 / 平移
- reflect / edge 自动扩展
- Gaussian Blur
- seam blending

这次清理不改变 Workspace 的图像处理算法，只删除已经被新版流程覆盖的旧实现。
