"""
Atlas 管理模块
处理多个图像的 Atlas 打包和折叠
"""

from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw
from dataclasses import dataclass
import numpy as np


@dataclass
class AtlasRegion:
    """
    Atlas 中的区域
    """
    name: str
    x: int
    y: int
    width: int
    height: int
    image: Optional[Image.Image] = None


class Atlas:
    """
    Atlas 管理类
    将多个图像打包到单个大图像中
    """
    
    def __init__(self, width: int = 2048, height: int = 2048, 
                 padding: int = 2):
        self.width = width
        self.height = height
        self.padding = padding
        self.regions: Dict[str, AtlasRegion] = {}
        self.image: Optional[Image.Image] = None
        self._packing_data = []
    
    def add_image(self, name: str, image: Image.Image) -> bool:
        """
        添加图像到 Atlas
        
        Args:
            name: 图像名称
            image: 图像对象
            
        Returns:
            是否成功添加
        """
        if name in self.regions:
            return False
        
        # 查找合适的位置
        position = self._find_position(image.width, image.height)
        
        if position is None:
            return False
        
        x, y = position
        self.regions[name] = AtlasRegion(
            name=name,
            x=x,
            y=y,
            width=image.width,
            height=image.height,
            image=image.copy()
        )
        return True
    
    def _find_position(self, width: int, height: int) -> Optional[Tuple[int, int]]:
        """
        查找合适的位置
        使用简单的打包算法
        """
        # 简单的贪心算法
        occupied = set()
        
        for region in self.regions.values():
            # 标记被占用的矩形
            for x in range(region.x, region.x + region.width + self.padding):
                for y in range(region.y, region.y + region.height + self.padding):
                    occupied.add((x, y))
        
        # 尝试找到第一个可用位置
        for y in range(0, self.height - height, self.padding):
            for x in range(0, self.width - width, self.padding):
                if self._can_place(x, y, width, height, occupied):
                    return (x, y)
        
        return None
    
    def _can_place(self, x: int, y: int, width: int, height: int,
                  occupied: set) -> bool:
        """检查是否可以在该位置放置"""
        if x + width > self.width or y + height > self.height:
            return False
        
        for px in range(x, x + width):
            for py in range(y, y + height):
                if (px, py) in occupied:
                    return False
        
        return True
    
    def build(self, background_color: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
        """
        构建 Atlas 图像
        
        Args:
            background_color: 背景颜色
            
        Returns:
            最终的 Atlas 图像
        """
        self.image = Image.new('RGBA', (self.width, self.height), background_color)
        
        for region in self.regions.values():
            if region.image:
                self.image.paste(
                    region.image,
                    (region.x, region.y),
                    region.image if region.image.mode == 'RGBA' else None
                )
        
        return self.image
    
    def get_region(self, name: str) -> Optional[AtlasRegion]:
        """获取区域信息"""
        return self.regions.get(name)
    
    def get_uv_coordinates(self, name: str) -> Optional[Tuple[float, float, float, float]]:
        """
        获取 UV 坐标（0-1 标准化）
        
        Returns:
            (u_min, v_min, u_max, v_max) 或 None
        """
        region = self.regions.get(name)
        if region:
            return (
                region.x / self.width,
                region.y / self.height,
                (region.x + region.width) / self.width,
                (region.y + region.height) / self.height
            )
        return None
    
    def collapse(self, threshold: float = 0.9) -> bool:
        """
        尝试折叠 Atlas（减少大小）
        
        Args:
            threshold: 使用阈值（0-1）
            
        Returns:
            是否成功折叠
        """
        # 计算实际使用的区域
        if not self.regions:
            return False
        
        max_x = max(r.x + r.width for r in self.regions.values())
        max_y = max(r.y + r.height for r in self.regions.values())
        
        usage_ratio = (max_x * max_y) / (self.width * self.height)
        
        if usage_ratio < threshold:
            # 找到最适合的新大小
            new_width = int(np.ceil(max_x / 128) * 128)  # 对齐到 128 的倍数
            new_height = int(np.ceil(max_y / 128) * 128)
            
            if new_width < self.width or new_height < self.height:
                self.width = new_width
                self.height = new_height
                return True
        
        return False
    
    def get_info(self) -> Dict:
        """获取 Atlas 信息"""
        return {
            'size': (self.width, self.height),
            'region_count': len(self.regions),
            'regions': {
                name: {
                    'position': (r.x, r.y),
                    'size': (r.width, r.height),
                    'uv': self.get_uv_coordinates(name)
                }
                for name, r in self.regions.items()
            }
        }
