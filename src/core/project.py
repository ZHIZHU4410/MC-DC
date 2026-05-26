"""
Project 管理模块
处理项目的创建、加载、保存和皮肤管理
"""

from pathlib import Path
from typing import Dict, List, Optional
from .config import ProjectConfig, SkinConfig


class Project:
    """
    项目管理类
    管理整个皮肤制作项目及其所有皮肤
    """
    
    CONFIG_FILENAME = "project.json"
    SKINS_DIR = "skins"
    
    def __init__(self, root_path: Path, config: ProjectConfig):
        self.root_path = Path(root_path)
        self.config = config
        self.skins: Dict[str, SkinConfig] = {}
        self._load_skins()
    
    @property
    def skins_dir(self) -> Path:
        """皮肤目录路径"""
        return self.root_path / self.SKINS_DIR
    
    @property
    def output_dir(self) -> Path:
        """输出目录路径"""
        return self.root_path / "output"
    
    @property
    def config_path(self) -> Path:
        """项目配置文件路径"""
        return self.root_path / self.CONFIG_FILENAME
    
    def create_skin(self, name: str, display_name: str = "", 
                   builder_type: str = "dynamic") -> SkinConfig:
        """创建新皮肤配置"""
        skin_config = SkinConfig(
            name=name,
            display_name=display_name or name,
            builder_type=builder_type
        )
        self.skins[name] = skin_config
        return skin_config
    
    def get_skin(self, name: str) -> Optional[SkinConfig]:
        """获取皮肤配置"""
        return self.skins.get(name)
    
    def remove_skin(self, name: str) -> bool:
        """删除皮肤配置"""
        if name in self.skins:
            del self.skins[name]
            return True
        return False
    
    def list_skins(self) -> List[str]:
        """列出所有皮肤名称"""
        return list(self.skins.keys())
    
    def _load_skins(self) -> None:
        """从磁盘加载皮肤配置"""
        if self.skins_dir.exists():
            for skin_file in self.skins_dir.glob("*.json"):
                try:
                    skin_config = SkinConfig.load(skin_file)
                    self.skins[skin_config.name] = skin_config
                except Exception as e:
                    print(f"警告: 无法加载皮肤文件 {skin_file}: {e}")
    
    def save(self) -> None:
        """保存项目和所有皮肤配置"""
        # 保存项目配置
        self.config.save(self.config_path)
        
        # 保存皮肤配置
        self.skins_dir.mkdir(parents=True, exist_ok=True)
        for name, skin_config in self.skins.items():
            skin_path = self.skins_dir / f"{name}.json"
            skin_config.save(skin_path)
    
    @classmethod
    def create(cls, root_path: Path, name: str, version: str = "1.0.0") -> "Project":
        """创建新项目"""
        root_path = Path(root_path)
        root_path.mkdir(parents=True, exist_ok=True)
        
        config = ProjectConfig(name=name, version=version)
        project = cls(root_path, config)
        project.save()
        return project
    
    @classmethod
    def load(cls, root_path: Path) -> "Project":
        """加载现有项目"""
        root_path = Path(root_path)
        config_path = root_path / cls.CONFIG_FILENAME
        
        if not config_path.exists():
            raise FileNotFoundError(f"项目配置文件不存在: {config_path}")
        
        config = ProjectConfig.load(config_path)
        return cls(root_path, config)
