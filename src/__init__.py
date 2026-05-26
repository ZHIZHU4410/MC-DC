"""
SkinMaker 主模块
Python 皮肤制作工具
"""

__version__ = "1.0.0"
__author__ = "SkinMaker Team"
__description__ = "Python 皮肤制作工具 - 完整的架构重构"

from src.core import (
    Project, ProjectConfig, SkinConfig,
    ImageFormat, BuilderType, TransformType, DrawOrder
)
from src.builders import (
    BaseBuilder, BuildContext, BuilderFactory,
    DynamicBuilder, OriginalBuilder, LineBuilder,
    AnimationBuilder
)
from src.transforms import (
    BaseTransform, TransformChain,
    PositionTransform, RotationTransform, FlipTransform, WarpTransform
)
from src.rendering import (
    DrawOrderSystem, Palette, Atlas
)
from src.io import (
    FileHandler, CDBModifier, PakPacker
)
from src.cli import SkinMakerCLI, main

__all__ = [
    # Version
    '__version__', '__author__', '__description__',
    # Core
    'Project', 'ProjectConfig', 'SkinConfig',
    'ImageFormat', 'BuilderType', 'TransformType', 'DrawOrder',
    # Builders
    'BaseBuilder', 'BuildContext', 'BuilderFactory',
    'DynamicBuilder', 'OriginalBuilder', 'LineBuilder',
    'AnimationBuilder',
    # Transforms
    'BaseTransform', 'TransformChain',
    'PositionTransform', 'RotationTransform', 'FlipTransform', 'WarpTransform',
    # Rendering
    'DrawOrderSystem', 'Palette', 'Atlas',
    # I/O
    'FileHandler', 'CDBModifier', 'PakPacker',
    # CLI
    'SkinMakerCLI', 'main',
]


if __name__ == '__main__':
    import sys
    sys.exit(main())
