from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


NATIVE_SCALE = 4
DEFAULT_TILE = 512
DEFAULT_TILE_PAD = 32

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEIGHTS_DIR = PROJECT_ROOT / "weights"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    blocks: int
    url: str


MODELS: dict[str, ModelSpec] = {
    "1": ModelSpec(
        name="RealESRGAN_x4plus_anime_6B",
        label="动漫 / 插画（推荐，6 个 RRDB，较快）",
        blocks=6,
        url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/download/"
            "v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
        ),
    ),
    "2": ModelSpec(
        name="RealESRGAN_x4plus",
        label="照片 / 通用图像（23 个 RRDB，更重）",
        blocks=23,
        url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/download/"
            "v0.1.0/RealESRGAN_x4plus.pth"
        ),
    ),
}
