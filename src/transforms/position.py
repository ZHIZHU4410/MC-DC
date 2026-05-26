"""
位置变换模块
"""

from typing import Tuple
from PIL import Image
from .base import BaseTransform


class PositionTransform(BaseTransform):
    """
    位置变换
    平移图像到指定位置
    """
    
    def __init__(self, x: int = 0, y: int = 0):
        super().__init__()
        self.x = x
        self.y = y
    
    def apply(self, image: Image.Image) -> Image.Image:
        """应用位置变换"""
        # 创建新的画布
        new_size = (
            max(image.width, self.x + image.width),
            max(image.height, self.y + image.height)
        )
        
        result = Image.new('RGBA', new_size, (0, 0, 0, 0))
        result.paste(image, (self.x, self.y), image if image.mode == 'RGBA' else None)
        return result
    
    def set_position(self, x: int, y: int) -> None:
        """设置位置"""
        self.x = x
        self.y = y
    
    def offset(self, dx: int, dy: int) -> None:
        """相对偏移"""
        self.x += dx
        self.y += dy
