"""
Builder 模块
包含所有皮肤构建器
"""

from .base import BaseBuilder, BuildContext, BuilderFactory
from .dynamic_builder import DynamicBuilder
from .original_builder import OriginalBuilder
from .line_builder import LineBuilder
from .animation_builder import AnimationBuilder, AnimationFrame

# 注册所有 Builder
BuilderFactory.register('dynamic', DynamicBuilder)
BuilderFactory.register('original', OriginalBuilder)
BuilderFactory.register('line', LineBuilder)

__all__ = [
    # Base
    'BaseBuilder', 'BuildContext', 'BuilderFactory',
    # Builders
    'DynamicBuilder', 'OriginalBuilder', 'LineBuilder',
    # Animation
    'AnimationBuilder', 'AnimationFrame',
]
