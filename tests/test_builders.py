"""
测试框架 - Builder 测试
"""

import unittest
from pathlib import Path
from PIL import Image

from src.builders import (
    BuildContext, BuilderFactory,
    DynamicBuilder, OriginalBuilder, LineBuilder
)


class TestBuilders(unittest.TestCase):
    """Builder 测试"""
    
    def setUp(self):
        """测试初始化"""
        self.test_image = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
    
    def test_dynamic_builder(self):
        """测试 Dynamic Builder"""
        config = {'layer_count': 2, 'canvas_width': 64, 'canvas_height': 64}
        builder = DynamicBuilder(config)
        
        context = BuildContext(
            skin_name='test_dynamic',
            builder_type='dynamic',
            source_image=self.test_image
        )
        
        result = builder.execute(context)
        self.assertIsNotNone(result)
        self.assertEqual(result.size, (64, 64))
    
    def test_original_builder(self):
        """测试 Original Builder"""
        config = {}
        builder = OriginalBuilder(config)
        
        context = BuildContext(
            skin_name='test_original',
            builder_type='original',
            source_image=self.test_image
        )
        
        result = builder.execute(context)
        self.assertIsNotNone(result)
        self.assertEqual(result.size, self.test_image.size)
    
    def test_builder_factory(self):
        """测试 Builder 工厂"""
        builders = BuilderFactory.list_builders()
        self.assertIn('dynamic', builders)
        self.assertIn('original', builders)
        self.assertIn('line', builders)
        
        builder = BuilderFactory.create('dynamic', {})
        self.assertIsNotNone(builder)


if __name__ == '__main__':
    unittest.main()
