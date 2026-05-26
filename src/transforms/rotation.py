"""
旋转变换模块
"""

from typing import Tuple
from PIL import Image
import math
from .base import BaseTransform


class RotationTransform(BaseTransform):
    """
    旋转变换
    旋转图像到指定角度
    """
    
    def __init__(self, angle: float = 0.0, expand: bool = True):
        super().__init__()
        self.angle = angle
        self.expand = expand
    
    def apply(self, image: Image.Image) -> Image.Image:
        """应用旋转变换"""
        return image.rotate(
            -self.angle,  # PIL 中负值表示逆时针
            expand=self.expand,
            resample=Image.Resampling.BICUBIC,
            fillcolor=(0, 0, 0, 0)
        )
    
    def set_angle(self, angle: float) -> None:
        """设置旋转角度（度）"""
        self.angle = angle % 360
    
    def rotate_by(self, delta: float) -> None:
        """增加旋转角度"""
        self.angle = (self.angle + delta) % 360
    
    @staticmethod
    def rotate_90() -> "RotationTransform":
        """创建 90 度旋转"""
        return RotationTransform(angle=90)
    
    @staticmethod
    def rotate_180() -> "RotationTransform":
        """创建 180 度旋转"""
        return RotationTransform(angle=180)
    
    @staticmethod
    def rotate_270() -> "RotationTransform":
        """创建 270 度旋转"""
        return RotationTransform(angle=270)
