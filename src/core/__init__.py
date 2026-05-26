"""
核心模块
包含项目配置、皮肤管理和基础数据结构
"""

from .constants import (
    ImageFormat, BuilderType, TransformType, DrawOrder,
    DEFAULT_CONFIG, TEMPLATES_DIR, SAMPLES_DIR, OUTPUT_DIR
)
from .config import (
    ProjectConfig, SkinConfig, AnimationConfig, 
    AtlasConfig, PaletteConfig
)
from .project import Project

__all__ = [
    # Constants
    'ImageFormat', 'BuilderType', 'TransformType', 'DrawOrder',
    'DEFAULT_CONFIG', 'TEMPLATES_DIR', 'SAMPLES_DIR', 'OUTPUT_DIR',
    # Config
    'ProjectConfig', 'SkinConfig', 'AnimationConfig',
    'AtlasConfig', 'PaletteConfig',
    # Project
    'Project',
]
