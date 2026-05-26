"""
配置系统模块
处理项目和皮肤配置的加载、验证和管理
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import json
from pathlib import Path


@dataclass
class AnimationConfig:
    """动画配置"""
    enabled: bool = True
    fps: int = 24
    loop: bool = True
    frame_count: int = 1
    frame_duration: int = 100  # 毫秒


@dataclass
class AtlasConfig:
    """Atlas 配置"""
    width: int = 2048
    height: int = 2048
    padding: int = 2
    auto_collapse: bool = True
    collapse_threshold: float = 0.9


@dataclass
class PaletteConfig:
    """调色板配置"""
    indexed: bool = True
    max_colors: int = 256
    dithering: bool = False
    dither_algorithm: str = "floyd_steinberg"


@dataclass
class ProjectConfig:
    """项目配置"""
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    output_format: str = "png"
    
    # 子配置
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    atlas: AtlasConfig = field(default_factory=AtlasConfig)
    palette: PaletteConfig = field(default_factory=PaletteConfig)
    
    # 其他设置
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def save(self, filepath: Path) -> None:
        """保存配置到文件"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: Path) -> "ProjectConfig":
        """从文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """从字典创建配置对象"""
        animation_data = data.pop('animation', {})
        atlas_data = data.pop('atlas', {})
        palette_data = data.pop('palette', {})
        
        return cls(
            animation=AnimationConfig(**animation_data),
            atlas=AtlasConfig(**atlas_data),
            palette=PaletteConfig(**palette_data),
            **data
        )


@dataclass
class SkinConfig:
    """皮肤配置"""
    name: str
    display_name: str = ""
    description: str = ""
    builder_type: str = "dynamic"
    
    # 变换配置
    transforms: Dict[str, Any] = field(default_factory=dict)
    
    # 图层配置
    layers: Dict[str, Any] = field(default_factory=dict)
    
    # 动画帧
    animation_frames: int = 1
    
    # 其他元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def save(self, filepath: Path) -> None:
        """保存配置到文件"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: Path) -> "SkinConfig":
        """从文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)
