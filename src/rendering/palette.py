"""
调色板索引模块
处理颜色调色板和索引编码
"""

from typing import List, Tuple, Dict, Optional
import numpy as np
from PIL import Image


class Palette:
    """
    调色板类
    管理图像颜色索引
    """
    
    def __init__(self, max_colors: int = 256):
        self.max_colors = max_colors
        self.colors: List[Tuple[int, int, int, int]] = []
        self.color_to_index: Dict[Tuple[int, int, int, int], int] = {}
    
    def add_color(self, color: Tuple[int, int, int, int]) -> int:
        """
        添加颜色到调色板
        
        Returns:
            颜色的索引
        """
        if len(color) != 4:
            raise ValueError("颜色必须为 RGBA 四元组")
        
        if color in self.color_to_index:
            return self.color_to_index[color]
        
        if len(self.colors) >= self.max_colors:
            raise ValueError(f"调色板已满，最多 {self.max_colors} 种颜色")
        
        index = len(self.colors)
        self.colors.append(color)
        self.color_to_index[color] = index
        return index
    
    def get_color(self, index: int) -> Optional[Tuple[int, int, int, int]]:
        """根据索引获取颜色"""
        if 0 <= index < len(self.colors):
            return self.colors[index]
        return None
    
    def get_index(self, color: Tuple[int, int, int, int]) -> Optional[int]:
        """根据颜色获取索引"""
        return self.color_to_index.get(color)
    
    def build_from_image(self, image: Image.Image, dithering: bool = False) -> None:
        """
        从图像构建调色板
        
        Args:
            image: 输入图像
            dithering: 是否使用抖动
        """
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 转换为 numpy 数组
        img_array = np.array(image)
        
        # 获取唯一颜色
        pixels = img_array.reshape(-1, 4)
        unique_colors = np.unique(pixels, axis=0)
        
        # 添加到调色板
        for color in unique_colors[:self.max_colors]:
            self.add_color(tuple(color.astype(int)))
    
    def to_indexed_image(self, image: Image.Image) -> Image.Image:
        """
        将 RGBA 图像转换为索引图像
        
        Args:
            image: 输入 RGBA 图像
            
        Returns:
            索引图像（8-bit）
        """
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # 转换为 numpy 数组
        img_array = np.array(image)
        width, height = image.size
        
        # 创建索引数组
        indexed = np.zeros((height, width), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                color = tuple(img_array[y, x].astype(int))
                index = self.get_index(color)
                if index is not None:
                    indexed[y, x] = index
        
        # 转换为图像
        palette_img = Image.new('P', image.size)
        
        # 设置调色板数据
        palette_data = []
        for color in self.colors:
            palette_data.extend([color[0], color[1], color[2]])
        
        # 填充剩余调色板为黑色
        while len(palette_data) < self.max_colors * 3:
            palette_data.extend([0, 0, 0])
        
        palette_img.putpalette(palette_data)
        palette_img.putdata(indexed.flatten())
        
        return palette_img
    
    def get_color_count(self) -> int:
        """获取调色板中的颜色数量"""
        return len(self.colors)
