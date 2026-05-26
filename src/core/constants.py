"""
常量定义模块
SkinMaker 核心常量和枚举定义
"""

from enum import Enum
from typing import Dict

# 支持的图像格式
class ImageFormat(Enum):
    """图像格式枚举"""
    PNG = "png"
    JPG = "jpg"
    BMP = "bmp"
    WEBP = "webp"


class BuilderType(Enum):
    """Builder 类型枚举"""
    DYNAMIC = "dynamic"
    ORIGINAL = "original"
    LINE = "line"


class TransformType(Enum):
    """变换类型枚举"""
    POSITION = "position"
    ROTATION = "rotation"
    FLIP = "flip"
    WARP = "warp"


class DrawOrder(Enum):
    """绘制顺序枚举"""
    BACKGROUND = 0
    LAYER_1 = 1
    LAYER_2 = 2
    LAYER_3 = 3
    LAYER_4 = 4
    LAYER_5 = 5
    FOREGROUND = 100


# 默认配置
DEFAULT_CONFIG: Dict = {
    "image_format": ImageFormat.PNG.value,
    "max_atlas_width": 2048,
    "max_atlas_height": 2048,
    "palette_colors": 256,
    "animation_fps": 24,
    "default_builder": BuilderType.DYNAMIC.value,
}

# 路径常量
TEMPLATES_DIR = "data/templates"
SAMPLES_DIR = "data/samples"
OUTPUT_DIR = "output"
