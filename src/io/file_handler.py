"""
文件处理模块
通用文件操作和格式处理
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from PIL import Image
import json
import shutil


class FileHandler:
    """
    文件处理器
    处理各种文件格式的读写
    """
    
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'}
    
    @staticmethod
    def load_image(file_path: Path) -> Optional[Image.Image]:
        """
        加载图像文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            PIL Image 对象
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if file_path.suffix.lower() not in FileHandler.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的图像格式: {file_path.suffix}")
        
        return Image.open(file_path).convert('RGBA')
    
    @staticmethod
    def save_image(image: Image.Image, file_path: Path,
                  quality: int = 95) -> None:
        """
        保存图像文件
        
        Args:
            image: 图像对象
            file_path: 输出文件路径
            quality: 保存质量（1-100）
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.png':
            image.save(file_path, 'PNG', optimize=True)
        elif suffix in {'.jpg', '.jpeg'}:
            rgb_image = image.convert('RGB')
            rgb_image.save(file_path, 'JPEG', quality=quality)
        elif suffix == '.webp':
            image.save(file_path, 'WEBP', quality=quality)
        elif suffix == '.bmp':
            image.save(file_path, 'BMP')
        else:
            image.save(file_path)
    
    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        """
        加载 JSON 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析后的 JSON 数据
        """
        file_path = Path(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def save_json(data: Dict[str, Any], file_path: Path,
                 indent: int = 2) -> None:
        """
        保存 JSON 文件
        
        Args:
            data: 要保存的数据
            file_path: 输出文件路径
            indent: JSON 缩进
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def load_text(file_path: Path, encoding: str = 'utf-8') -> str:
        """加载文本文件"""
        file_path = Path(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    
    @staticmethod
    def save_text(text: str, file_path: Path,
                 encoding: str = 'utf-8') -> None:
        """保存文本文件"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(text)
    
    @staticmethod
    def copy_file(src: Path, dst: Path) -> None:
        """复制文件"""
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    
    @staticmethod
    def copy_directory(src: Path, dst: Path) -> None:
        """复制目录"""
        shutil.copytree(src, dst, dirs_exist_ok=True)
    
    @staticmethod
    def list_files(directory: Path, pattern: str = '*',
                  recursive: bool = False) -> List[Path]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归
            
        Returns:
            文件路径列表
        """
        directory = Path(directory)
        
        if recursive:
            return list(directory.rglob(pattern))
        else:
            return list(directory.glob(pattern))
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """确保目录存在"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """获取文件大小（字节）"""
        return Path(file_path).stat().st_size
    
    @staticmethod
    def file_exists(file_path: Path) -> bool:
        """检查文件是否存在"""
        return Path(file_path).exists()
