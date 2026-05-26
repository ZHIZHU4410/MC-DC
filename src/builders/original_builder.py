"""
Original Builder
原始皮肤构建器，直接使用源图像
"""

from typing import Dict, Any
from PIL import Image
from .base import BaseBuilder, BuildContext


class OriginalBuilder(BaseBuilder):
    """
    Original Builder
    直接使用并处理源图像
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.preserve_format = config.get('preserve_format', True)
    
    def validate(self, context: BuildContext) -> bool:
        """验证输入数据"""
        if context.source_image is None:
            return False
        return True
    
    def prepare(self, context: BuildContext) -> None:
        """准备构建过程"""
        context.metadata['builder_type'] = 'original'
        context.metadata['original_size'] = context.source_image.size
    
    def build(self, context: BuildContext) -> Image.Image:
        """
        执行构建过程
        返回原始图像
        """
        if context.source_image is None:
            raise ValueError("源图像未设置")
        
        # 复制图像以避免修改原始图像
        return context.source_image.copy()
    
    def post_process(self, image: Image.Image) -> Image.Image:
        """后处理"""
        # 可选的格式转换或优化
        if not self.preserve_format and image.mode != 'RGBA':
            image = image.convert('RGBA')
        return image
