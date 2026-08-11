from __future__ import annotations

import urllib.request
from pathlib import Path

import torch

from .config import ModelSpec, WEIGHTS_DIR
from .model_arch import RRDBNet


def _download_with_progress(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n首次使用需要下载模型：\n{url}")
    print(f"保存到：{destination}\n")

    def hook(block_num: int, block_size: int, total_size: int) -> None:
        downloaded = block_num * block_size

        if total_size > 0:
            pct = min(100.0, downloaded * 100.0 / total_size)
            print(
                f"\r下载 {pct:6.2f}%  "
                f"{downloaded / 1024**2:7.1f}/{total_size / 1024**2:.1f} MB",
                end="",
                flush=True,
            )
        else:
            print(
                f"\r已下载 {downloaded / 1024**2:.1f} MB",
                end="",
                flush=True,
            )

    try:
        urllib.request.urlretrieve(url, destination, reporthook=hook)
        print("\n下载完成。")
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _safe_torch_load(path: Path):
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def load_model(spec: ModelSpec, device: torch.device, use_half: bool) -> RRDBNet:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    weight_path = WEIGHTS_DIR / f"{spec.name}.pth"

    if not weight_path.exists():
        _download_with_progress(spec.url, weight_path)

    print("\n正在加载模型...")

    model = RRDBNet(
        num_in_ch=3,
        num_out_ch=3,
        num_feat=64,
        num_block=spec.blocks,
        num_grow_ch=32,
    )

    checkpoint = _safe_torch_load(weight_path)

    if isinstance(checkpoint, dict):
        state = (
            checkpoint.get("params_ema")
            or checkpoint.get("params")
            or checkpoint
        )
    else:
        state = checkpoint

    state = {
        (key[7:] if key.startswith("module.") else key): value
        for key, value in state.items()
    }

    model.load_state_dict(state, strict=True)
    model.eval().to(device)

    if use_half:
        model.half()

    return model
