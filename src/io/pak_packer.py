"""
res.pak 打包模块
处理资源包打包和解包
"""

from typing import Dict, List, Optional, BinaryIO
from pathlib import Path
import zipfile
import json
import struct


class PakResource:
    """Pak 资源"""
    
    def __init__(self, name: str, data: bytes, 
                 resource_type: str = 'unknown'):
        self.name = name
        self.data = data
        self.resource_type = resource_type
        self.size = len(data)
        self.compressed = False


class PakPacker:
    """
    Pak 打包器
    处理 res.pak 资源包的创建和管理
    """
    
    # Pak 文件头签名
    SIGNATURE = b'RESX'
    VERSION = 1
    
    def __init__(self):
        self.resources: Dict[str, PakResource] = {}
        self.metadata: Dict[str, any] = {}
    
    def add_resource(self, name: str, data: bytes, 
                    resource_type: str = 'unknown') -> None:
        """
        添加资源
        
        Args:
            name: 资源名称
            data: 资源数据
            resource_type: 资源类型
        """
        resource = PakResource(name, data, resource_type)
        self.resources[name] = resource
    
    def add_file(self, file_path: Path, resource_name: str = None,
                resource_type: str = 'unknown') -> None:
        """
        从文件添加资源
        
        Args:
            file_path: 文件路径
            resource_name: 资源名称（若为 None 则使用文件名）
            resource_type: 资源类型
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        resource_name = resource_name or file_path.name
        with open(file_path, 'rb') as f:
            data = f.read()
        
        self.add_resource(resource_name, data, resource_type)
    
    def get_resource(self, name: str) -> Optional[PakResource]:
        """获取资源"""
        return self.resources.get(name)
    
    def list_resources(self) -> List[str]:
        """列出所有资源"""
        return list(self.resources.keys())
    
    def remove_resource(self, name: str) -> bool:
        """删除资源"""
        if name in self.resources:
            del self.resources[name]
            return True
        return False
    
    def pack(self, output_path: Path) -> None:
        """
        打包为 Pak 文件
        
        Args:
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 为简化起见，使用 zip 作为容器
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as pak:
            # 写入资源
            for name, resource in self.resources.items():
                pak.writestr(name, resource.data)
            
            # 写入元数据
            metadata = {
                'version': self.VERSION,
                'resources': {
                    name: {
                        'type': resource.resource_type,
                        'size': resource.size,
                        'compressed': resource.compressed
                    }
                    for name, resource in self.resources.items()
                },
                'metadata': self.metadata
            }
            pak.writestr('_metadata.json', json.dumps(metadata, indent=2))
    
    def unpack(self, pak_path: Path, output_dir: Path) -> None:
        """
        解包 Pak 文件
        
        Args:
            pak_path: Pak 文件路径
            output_dir: 输出目录
        """
        pak_path = Path(pak_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(pak_path, 'r') as pak:
            pak.extractall(output_dir)
    
    @classmethod
    def load(cls, pak_path: Path) -> "PakPacker":
        """
        加载现有的 Pak 文件
        
        Args:
            pak_path: Pak 文件路径
            
        Returns:
            PakPacker 实例
        """
        packer = cls()
        pak_path = Path(pak_path)
        
        with zipfile.ZipFile(pak_path, 'r') as pak:
            for file_name in pak.namelist():
                if file_name != '_metadata.json':
                    data = pak.read(file_name)
                    packer.add_resource(file_name, data)
                else:
                    # 加载元数据
                    metadata_str = pak.read(file_name).decode('utf-8')
                    metadata = json.loads(metadata_str)
                    packer.metadata = metadata.get('metadata', {})
        
        return packer
    
    def get_info(self) -> Dict:
        """获取 Pak 信息"""
        total_size = sum(r.size for r in self.resources.values())
        return {
            'resource_count': len(self.resources),
            'total_size': total_size,
            'resources': {
                name: {
                    'type': resource.resource_type,
                    'size': resource.size
                }
                for name, resource in self.resources.items()
            }
        }
