"""
翻转变换模块
"""

from typing import Literal
from PIL import Image
from .base import BaseTransform


class FlipTransform(BaseTransform):
    """
    翻转变换
    在水平或垂直方向上翻转图像
    """
    
    def __init__(self, direction: Literal['h', 'v', 'both'] = 'h'):
        super().__init__()
        self.direction = direction
    
    def apply(self, image: Image.Image) -> Image.Image:
        """应用翻转变换"""
        if self.direction == 'h':
            return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif self.direction == 'v':
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif self.direction == 'both':
            return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT).transpose(
                Image.Transpose.FLIP_TOP_BOTTOM
            )
        return image
    
    def set_direction(self, direction: Literal['h', 'v', 'both']) -> None:
        """设置翻转方向"""
        if direction not in ('h', 'v', 'both'):
            raise ValueError(f"无效的翻转方向: {direction}")
        self.direction = direction
    
    @staticmethod
    def horizontal() -> "FlipTransform":
        """创建水平翻转"""
        return FlipTransform('h')
    
    @staticmethod
    def vertical() -> "FlipTransform":
        """创建垂直翻转"""
        return FlipTransform('v')
    
    @staticmethod
    def both() -> "FlipTransform":
        """创建两向翻转"""
        return FlipTransform('both')
