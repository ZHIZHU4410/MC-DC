"""
绘制顺序模块
管理图层的绘制顺序
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field


class DrawOrderLevel(Enum):
    """绘制顺序级别"""
    BACKGROUND = 0
    LAYER_1 = 10
    LAYER_2 = 20
    LAYER_3 = 30
    LAYER_4 = 40
    LAYER_5 = 50
    FOREGROUND = 100


@dataclass
class DrawableLayer:
    """可绘制的图层"""
    name: str
    order_level: int
    visible: bool = True
    opacity: float = 1.0
    blend_mode: str = 'normal'
    metadata: Dict = field(default_factory=dict)


class DrawOrderSystem:
    """
    绘制顺序系统
    管理图层的绘制顺序和优先级
    """
    
    def __init__(self):
        self.layers: Dict[str, DrawableLayer] = {}
        self.order_cache: List[str] = []
        self._dirty = True
    
    def add_layer(self, name: str, order_level: int = None,
                 visible: bool = True, opacity: float = 1.0) -> None:
        """添加图层"""
        if order_level is None:
            order_level = len(self.layers) * 10
        
        self.layers[name] = DrawableLayer(
            name=name,
            order_level=order_level,
            visible=visible,
            opacity=opacity
        )
        self._dirty = True
    
    def remove_layer(self, name: str) -> bool:
        """删除图层"""
        if name in self.layers:
            del self.layers[name]
            self._dirty = True
            return True
        return False
    
    def set_order_level(self, name: str, order_level: int) -> None:
        """设置绘制顺序级别"""
        if name in self.layers:
            self.layers[name].order_level = order_level
            self._dirty = True
    
    def set_visibility(self, name: str, visible: bool) -> None:
        """设置图层可见性"""
        if name in self.layers:
            self.layers[name].visible = visible
    
    def set_opacity(self, name: str, opacity: float) -> None:
        """设置图层不透明度"""
        if name in self.layers:
            self.layers[name].opacity = max(0.0, min(1.0, opacity))
    
    def get_draw_order(self) -> List[str]:
        """
        获取绘制顺序
        按顺序级别从小到大返回可见图层
        """
        if self._dirty:
            self.order_cache = [
                name for name, layer in sorted(
                    self.layers.items(),
                    key=lambda x: x[1].order_level
                )
                if layer.visible
            ]
            self._dirty = False
        
        return self.order_cache
    
    def move_layer_forward(self, name: str) -> None:
        """向前移动图层"""
        if name in self.layers:
            current_level = self.layers[name].order_level
            self.set_order_level(name, current_level + 5)
    
    def move_layer_backward(self, name: str) -> None:
        """向后移动图层"""
        if name in self.layers:
            current_level = self.layers[name].order_level
            self.set_order_level(name, max(0, current_level - 5))
    
    def get_layer_info(self, name: str) -> Optional[DrawableLayer]:
        """获取图层信息"""
        return self.layers.get(name)
    
    def list_layers(self) -> List[str]:
        """列出所有图层"""
        return list(self.layers.keys())
