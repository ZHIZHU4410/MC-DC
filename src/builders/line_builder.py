"""
Line Builder
轮廓线皮肤构建器，生成轮廓效果
"""

from typing import Dict, Any
from PIL import Image, ImageFilter, ImageOps
import numpy as np
from .base import BaseBuilder, BuildContext


class LineBuilder(BaseBuilder):
    """
    Line Builder
    从源图像生成轮廓线效果
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.line_width = config.get('line_width', 2)
        self.line_color = config.get('line_color', (0, 0, 0, 255))
        self.algorithm = config.get('algorithm', 'edge_detect')
    
    def validate(self, context: BuildContext) -> bool:
        """验证输入数据"""
        if context.source_image is None:
            return False
        if self.line_width <= 0:
            return False
        return True
    
    def prepare(self, context: BuildContext) -> None:
        """准备构建过程"""
        context.metadata['builder_type'] = 'line'
        context.metadata['line_width'] = self.line_width
        context.metadata['algorithm'] = self.algorithm
    
    def build(self, context: BuildContext) -> Image.Image:
        """
        执行构建过程
        生成轮廓线
        """
        if context.source_image is None:
            raise ValueError("源图像未设置")
        
        source = context.source_image.convert('RGBA')
        
        if self.algorithm == 'edge_detect':
            return self._edge_detect_method(source)
        elif self.algorithm == 'contour':
            return self._contour_method(source)
        else:
            return self._edge_detect_method(source)
    
    def _edge_detect_method(self, image: Image.Image) -> Image.Image:
        """边缘检测方法"""
        # 转换为灰度用于边缘检测
        gray = image.convert('L')
        
        # 应用边缘检测滤镜
        edges = gray.filter(ImageFilter.FIND_EDGES)
        
        # 创建新的 RGBA 图像
        result = Image.new('RGBA', image.size, (0, 0, 0, 0))
        
        # 将边缘转换为指定颜色的线
        result.paste(self.line_color, (0, 0), edges)
        
        return result
    
    def _contour_method(self, image: Image.Image) -> Image.Image:
        """轮廓提取方法"""
        # 简化处理：使用边缘检测作为基础
        return self._edge_detect_method(image)
    
    def post_process(self, image: Image.Image) -> Image.Image:
        """后处理"""
        # 可选的线宽增强
        if self.line_width > 1:
            # 通过膨胀来增加线宽
            arr = np.array(image)
            if arr.shape[2] == 4:  # RGBA
                alpha = arr[:, :, 3]
                # 简单的膨胀操作
                from scipy import ndimage
                dilated = ndimage.binary_dilation(alpha > 0, iterations=self.line_width - 1)
                arr[:, :, 3] = dilated.astype(np.uint8) * 255
                image = Image.fromarray(arr)
        
        return image
