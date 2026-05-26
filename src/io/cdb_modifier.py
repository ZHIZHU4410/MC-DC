"""
CDB 修改模块
处理 CDB（Character Data Base）数据修改
"""

from typing import Dict, Any, Optional, List
import struct
from pathlib import Path
import json


class CDBEntry:
    """CDB 条目"""
    
    def __init__(self, entry_id: int, data: Dict[str, Any]):
        self.entry_id = entry_id
        self.data = data
    
    def update(self, key: str, value: Any) -> None:
        """更新条目数据"""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取条目数据"""
        return self.data.get(key, default)


class CDBModifier:
    """
    CDB 修改器
    处理 CDB 文件的读取、修改和保存
    """
    
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = Path(file_path) if file_path else None
        self.entries: Dict[int, CDBEntry] = {}
        self.metadata: Dict[str, Any] = {}
    
    def load(self, file_path: Path) -> None:
        """
        加载 CDB 文件
        
        Args:
            file_path: 文件路径
        """
        self.file_path = Path(file_path)
        
        # 这里应该实现实际的 CDB 文件解析
        # 为简化起见，使用 JSON 格式作为示例
        if self.file_path.suffix.lower() == '.json':
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metadata = data.get('metadata', {})
                for entry_id, entry_data in data.get('entries', {}).items():
                    self.entries[int(entry_id)] = CDBEntry(int(entry_id), entry_data)
    
    def add_entry(self, entry_id: int, data: Dict[str, Any]) -> CDBEntry:
        """添加新条目"""
        entry = CDBEntry(entry_id, data)
        self.entries[entry_id] = entry
        return entry
    
    def get_entry(self, entry_id: int) -> Optional[CDBEntry]:
        """获取条目"""
        return self.entries.get(entry_id)
    
    def modify_entry(self, entry_id: int, key: str, value: Any) -> bool:
        """修改条目"""
        entry = self.entries.get(entry_id)
        if entry:
            entry.update(key, value)
            return True
        return False
    
    def remove_entry(self, entry_id: int) -> bool:
        """删除条目"""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False
    
    def get_all_entries(self) -> List[CDBEntry]:
        """获取所有条目"""
        return list(self.entries.values())
    
    def save(self, file_path: Optional[Path] = None) -> None:
        """
        保存 CDB 文件
        
        Args:
            file_path: 文件路径（若为 None 则使用加载时的路径）
        """
        if file_path:
            self.file_path = Path(file_path)
        
        if not self.file_path:
            raise ValueError("未指定文件路径")
        
        # 为简化起见，保存为 JSON 格式
        data = {
            'metadata': self.metadata,
            'entries': {
                str(entry_id): entry.data
                for entry_id, entry in self.entries.items()
            }
        }
        
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_to_json(self, file_path: Path) -> None:
        """导出为 JSON 格式"""
        self.save(file_path)
    
    @classmethod
    def create_empty(cls) -> "CDBModifier":
        """创建空的 CDB 修改器"""
        return cls()
