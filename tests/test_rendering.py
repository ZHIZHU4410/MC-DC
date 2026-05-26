"""
测试框架 - 渲染测试
"""

import unittest
from PIL import Image

from src.rendering import (
    DrawOrderSystem, DrawOrderLevel,
    Palette, Atlas
)


class TestRendering(unittest.TestCase):
    """渲染系统测试"""
    
    def test_draw_order_system(self):
        """测试绘制顺序系统"""
        system = DrawOrderSystem()
        
        system.add_layer('background', DrawOrderLevel.BACKGROUND.value)
        system.add_layer('layer1', DrawOrderLevel.LAYER_1.value)
        system.add_layer('foreground', DrawOrderLevel.FOREGROUND.value)
        
        order = system.get_draw_order()
        self.assertEqual(len(order), 3)
        self.assertEqual(order[0], 'background')
    
    def test_palette(self):
        """测试调色板"""
        palette = Palette(256)
        
        # 添加颜色
        idx1 = palette.add_color((255, 0, 0, 255))
        idx2 = palette.add_color((0, 255, 0, 255))
        
        self.assertEqual(idx1, 0)
        self.assertEqual(idx2, 1)
        self.assertEqual(palette.get_color_count(), 2)
    
    def test_atlas(self):
        """测试 Atlas"""
        atlas = Atlas(256, 256, 2)
        
        img1 = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
        img2 = Image.new('RGBA', (32, 32), (0, 255, 0, 255))
        
        result1 = atlas.add_image('image1', img1)
        result2 = atlas.add_image('image2', img2)
        
        self.assertTrue(result1)
        self.assertTrue(result2)
        
        built = atlas.build()
        self.assertIsNotNone(built)


if __name__ == '__main__':
    unittest.main()
