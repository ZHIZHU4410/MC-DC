"""
CLI 命令处理模块
"""

from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import sys

from ..core import Project, ProjectConfig, SkinConfig
from ..builders import BuilderFactory, BuildContext
from ..io import FileHandler, PakPacker


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    message: str
    data: Optional[Any] = None


class CommandHandler:
    """
    命令处理器
    处理各种 CLI 命令
    """
    
    def __init__(self, project_path: Path = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.project: Optional[Project] = None
    
    def load_project(self) -> CommandResult:
        """加载项目"""
        try:
            self.project = Project.load(self.project_path)
            return CommandResult(
                success=True,
                message=f"项目已加载: {self.project.config.name}"
            )
        except Exception as e:
            return CommandResult(success=False, message=f"加载项目失败: {e}")
    
    def project_create(self, name: str, version: str = "1.0.0",
                      path: str = ".") -> CommandResult:
        """创建项目"""
        try:
            project_path = Path(path)
            self.project = Project.create(project_path, name, version)
            return CommandResult(
                success=True,
                message=f"项目创建成功: {name}",
                data=self.project
            )
        except Exception as e:
            return CommandResult(success=False, message=f"创建项目失败: {e}")
    
    def project_list(self) -> CommandResult:
        """列出项目中的皮肤"""
        if not self.project:
            result = self.load_project()
            if not result.success:
                return result
        
        skins = self.project.list_skins()
        return CommandResult(
            success=True,
            message=f"项目包含 {len(skins)} 个皮肤",
            data=skins
        )
    
    def skin_create(self, name: str, builder: str = "dynamic",
                   display_name: str = None) -> CommandResult:
        """创建皮肤"""
        if not self.project:
            result = self.load_project()
            if not result.success:
                return result
        
        try:
            skin = self.project.create_skin(
                name,
                display_name or name,
                builder
            )
            self.project.save()
            return CommandResult(
                success=True,
                message=f"皮肤创建成功: {name}",
                data=skin
            )
        except Exception as e:
            return CommandResult(success=False, message=f"创建皮肤失败: {e}")
    
    def skin_build(self, name: str, output: str = None) -> CommandResult:
        """构建皮肤"""
        if not self.project:
            result = self.load_project()
            if not result.success:
                return result
        
        try:
            skin = self.project.get_skin(name)
            if not skin:
                return CommandResult(
                    success=False,
                    message=f"皮肤不存在: {name}"
                )
            
            # 创建 Builder
            builder = BuilderFactory.create(
                skin.builder_type,
                skin.transforms or {}
            )
            
            # 创建构建上下文
            context = BuildContext(
                skin_name=name,
                builder_type=skin.builder_type
            )
            
            # 执行构建
            image = builder.execute(context)
            
            # 保存输出
            output_path = output or f"{name}.png"
            FileHandler.save_image(image, Path(output_path))
            
            return CommandResult(
                success=True,
                message=f"皮肤构建成功: {output_path}",
                data=image
            )
        except Exception as e:
            return CommandResult(success=False, message=f"构建皮肤失败: {e}")
    
    def build_all(self, output: str = None) -> CommandResult:
        """构建所有皮肤"""
        if not self.project:
            result = self.load_project()
            if not result.success:
                return result
        
        output_dir = Path(output) if output else self.project.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        for skin_name in self.project.list_skins():
            output_path = output_dir / f"{skin_name}.png"
            result = self.skin_build(skin_name, str(output_path))
            results[skin_name] = result
        
        success_count = sum(1 for r in results.values() if r.success)
        return CommandResult(
            success=True,
            message=f"构建完成: {success_count}/{len(results)} 个皮肤成功",
            data=results
        )
    
    def pack(self, output: str = None) -> CommandResult:
        """打包项目"""
        if not self.project:
            result = self.load_project()
            if not result.success:
                return result
        
        try:
            output_path = Path(output) if output else Path("project.pak")
            
            packer = PakPacker()
            
            # 添加配置文件
            config_data = str(self.project.config.to_dict()).encode('utf-8')
            packer.add_resource('project.json', config_data, 'config')
            
            # 添加所有皮肤配置和输出
            for skin_name in self.project.list_skins():
                skin = self.project.get_skin(skin_name)
                skin_json = str(skin.to_dict()).encode('utf-8')
                packer.add_resource(f"skins/{skin_name}.json", skin_json, 'config')
            
            # 打包
            packer.pack(output_path)
            
            return CommandResult(
                success=True,
                message=f"项目打包成功: {output_path}"
            )
        except Exception as e:
            return CommandResult(success=False, message=f"打包失败: {e}")
