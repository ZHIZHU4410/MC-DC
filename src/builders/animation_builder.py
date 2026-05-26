"""
动画构建器模块
处理动画帧生成和序列管理
"""

from typing import Dict, Any, List
from PIL import Image
from dataclasses import dataclass
import numpy as np


@dataclass
class AnimationFrame:
    """动画帧"""
    image: Image.Image
    duration: int = 100  # 毫秒
    index: int = 0


class AnimationBuilder:
    """
    动画构建器
    用于生成和管理动画序列
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.frames: List[AnimationFrame] = []
        self.fps = config.get('fps', 24)
        self.loop = config.get('loop', True)
    
    def add_frame(self, image: Image.Image, duration: int = None) -> None:
        """
        添加帧
        
        Args:
            image: 帧图像
            duration: 帧持续时间（毫秒）
        """
        if duration is None:
            duration = int(1000 / self.fps)
        
        frame = AnimationFrame(
            image=image,
            duration=duration,
            index=len(self.frames)
        )
        self.frames.append(frame)
    
    def add_frames(self, images: List[Image.Image]) -> None:
        """添加多个帧"""
        for image in images:
            self.add_frame(image)
    
    def generate_animation(self) -> List[Image.Image]:
        """
        生成动画序列
        
        Returns:
            动画帧列表
        """
        if not self.frames:
            raise ValueError("没有添加任何帧")
        
        return [frame.image for frame in self.frames]
    
    def save_as_gif(self, filepath: str) -> None:
        """
        保存为 GIF
        
        Args:
            filepath: 输出文件路径
        """
        if not self.frames:
            raise ValueError("没有帧数据可保存")
        
        images = [frame.image.convert('RGB') for frame in self.frames]
        durations = [frame.duration for frame in self.frames]
        
        images[0].save(
            filepath,
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0 if self.loop else 1,
            optimize=False
        )
    
    def get_frame(self, index: int) -> Image.Image:
        """获取指定索引的帧"""
        if 0 <= index < len(self.frames):
            return self.frames[index].image
        raise IndexError(f"帧索引越界: {index}")
    
    def get_frame_count(self) -> int:
        """获取帧数量"""
        return len(self.frames)
    
    def clear(self) -> None:
        """清空所有帧"""
        self.frames.clear()
