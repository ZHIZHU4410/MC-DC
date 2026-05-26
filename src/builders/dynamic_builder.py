"""
Dynamic Builder
动态皮肤构建器，根据配置动态生成皮肤
"""

from typing import Dict, Any
from PIL import Image, ImageDraw
import numpy as np
from .base import BaseBuilder, BuildContext


class DynamicBuilder(BaseBuilder):
    """
    动态 Builder
    根据参数和配置动态生成皮肤内容
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.layer_count = config.get('layer_count', 1)
        self.canvas_width = config.get('canvas_width', 64)
        self.canvas_height = config.get('canvas_height', 64)
    
    def validate(self, context: BuildContext) -> bool:
        """验证输入数据"""
        if context.skin_name is None:
            return False
        if self.canvas_width <= 0 or self.canvas_height <= 0:
            return False
        return True
    
    def prepare(self, context: BuildContext) -> None:
        """准备构建过程"""
        # 创建空白画布
        for i in range(self.layer_count):
            layer_name = f"layer_{i}"
            context.layers[layer_name] = Image.new(
                'RGBA', 
                (self.canvas_width, self.canvas_height),
                (0, 0, 0, 0)
            )
        
        context.metadata['builder_type'] = 'dynamic'
        context.metadata['layer_count'] = self.layer_count
    
    def build(self, context: BuildContext) -> Image.Image:
        """
        执行构建过程
        动态生成皮肤层
        """
        # 创建最终画布
        output = Image.new(
            'RGBA',
            (self.canvas_width, self.canvas_height),
            (0, 0, 0, 0)
        )
        
        # 按顺序合并所有层
        for layer in context.layers.values():
            output = Image.alpha_composite(output, layer)
        
        return output
    
    def post_process(self, image: Image.Image) -> Image.Image:
        """后处理"""
        # 可在此处进行优化、压缩等操作
        return image
    
    def add_content(self, context: BuildContext, layer_name: str, 
                   content: Image.Image, position: tuple = (0, 0)) -> None:
        """
        向指定层添加内容
        
        Args:
            context: 构建上下文
            layer_name: 层名称
            content: 要添加的内容
            position: 位置 (x, y)
        """
        if layer_name not in context.layers:
            raise ValueError(f"图层不存在: {layer_name}")
        
        layer = context.layers[layer_name]
        layer.paste(content, position, content if content.mode == 'RGBA' else None)
