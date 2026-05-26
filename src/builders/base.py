"""
Builder 基类模块
定义所有 Builder 的基础接口和抽象方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from PIL import Image
import numpy as np


@dataclass
class BuildContext:
    """构建上下文"""
    skin_name: str
    builder_type: str
    source_image: Optional[Image.Image] = None
    output_image: Optional[Image.Image] = None
    layers: Dict[str, Image.Image] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.layers is None:
            self.layers = {}
        if self.metadata is None:
            self.metadata = {}


class BaseBuilder(ABC):
    """
    Builder 基类
    所有皮肤构建器的抽象基类
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context: Optional[BuildContext] = None
    
    @abstractmethod
    def validate(self, context: BuildContext) -> bool:
        """验证输入数据"""
        pass
    
    @abstractmethod
    def prepare(self, context: BuildContext) -> None:
        """准备构建过程"""
        pass
    
    @abstractmethod
    def build(self, context: BuildContext) -> Image.Image:
        """执行构建过程"""
        pass
    
    @abstractmethod
    def post_process(self, image: Image.Image) -> Image.Image:
        """后处理"""
        pass
    
    def execute(self, context: BuildContext) -> Image.Image:
        """
        执行完整的构建流程
        
        Args:
            context: 构建上下文
            
        Returns:
            构建结果图像
        """
        self.context = context
        
        if not self.validate(context):
            raise ValueError("构建参数验证失败")
        
        self.prepare(context)
        image = self.build(context)
        image = self.post_process(image)
        
        context.output_image = image
        return image


class BuilderFactory:
    """Builder 工厂类"""
    
    _builders: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, builder_class: type) -> None:
        """注册 Builder 类"""
        cls._builders[name] = builder_class
    
    @classmethod
    def create(cls, builder_type: str, config: Dict[str, Any]) -> BaseBuilder:
        """创建 Builder 实例"""
        if builder_type not in cls._builders:
            raise ValueError(f"未知的 Builder 类型: {builder_type}")
        
        builder_class = cls._builders[builder_type]
        return builder_class(config)
    
    @classmethod
    def list_builders(cls) -> List[str]:
        """列出所有注册的 Builder"""
        return list(cls._builders.keys())
