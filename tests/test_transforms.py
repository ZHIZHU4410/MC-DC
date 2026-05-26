"""
测试框架 - 变换测试
"""

import unittest
from PIL import Image

from src.transforms import (
    PositionTransform, RotationTransform,
    FlipTransform, WarpTransform, TransformChain
)


class TestTransforms(unittest.TestCase):
    """变换测试"""
    
    def setUp(self):
        """测试初始化"""
        self.test_image = Image.new('RGBA', (32, 32), (0, 255, 0, 255))
    
    def test_position_transform(self):
        """测试位置变换"""
        transform = PositionTransform(10, 20)
        result = transform.apply(self.test_image)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.width, self.test_image.width)
    
    def test_rotation_transform(self):
        """测试旋转变换"""
        transform = RotationTransform(45)
        result = transform.apply(self.test_image)
        self.assertIsNotNone(result)
    
    def test_flip_transform(self):
        """测试翻转变换"""
        h_flip = FlipTransform.horizontal()
        result = h_flip.apply(self.test_image)
        self.assertEqual(result.size, self.test_image.size)
    
    def test_transform_chain(self):
        """测试变换链"""
        chain = TransformChain()
        chain.add_transform(PositionTransform(5, 5))
        chain.add_transform(FlipTransform.horizontal())
        
        result = chain.apply(self.test_image)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
