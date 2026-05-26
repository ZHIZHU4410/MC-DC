"""
变换基类模块
定义所有变换的基础接口
"""

from abc import ABC, abstractmethod
from typing import Tuple
from PIL import Image
import numpy as np


class BaseTransform(ABC):
    """
    变换基类
    所有变换的抽象基类
    """
    
    def __init__(self):
        self.enabled = True
    
    @abstractmethod
    def apply(self, image: Image.Image) -> Image.Image:
        """应用变换"""
        pass
    
    def __call__(self, image: Image.Image) -> Image.Image:
        """使变换可调用"""
        if self.enabled:
            return self.apply(image)
        return image


class TransformChain:
    """
    变换链
    管理多个变换的顺序执行
    """
    
    def __init__(self):
        self.transforms: list = []
    
    def add_transform(self, transform: BaseTransform) -> "TransformChain":
        """添加变换"""
        self.transforms.append(transform)
        return self
    
    def apply(self, image: Image.Image) -> Image.Image:
        """按顺序应用所有变换"""
        for transform in self.transforms:
            image = transform(image)
        return image
    
    def __call__(self, image: Image.Image) -> Image.Image:
        """使变换链可调用"""
        return self.apply(image)
