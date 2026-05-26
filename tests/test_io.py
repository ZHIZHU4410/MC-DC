"""
测试框架 - I/O 测试
"""

import unittest
import tempfile
from pathlib import Path
from PIL import Image

from src.io import FileHandler, CDBModifier, PakPacker


class TestFileHandler(unittest.TestCase):
    """文件处理器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def test_save_and_load_image(self):
        """测试保存和加载图像"""
        img = Image.new('RGB', (32, 32), (255, 0, 0))
        img_path = self.temp_dir / 'test.png'
        
        FileHandler.save_image(img, img_path)
        self.assertTrue(img_path.exists())
        
        loaded = FileHandler.load_image(img_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.size, (32, 32))
    
    def test_save_and_load_json(self):
        """测试 JSON 保存和加载"""
        data = {'test': 'data', 'number': 42}
        json_path = self.temp_dir / 'test.json'
        
        FileHandler.save_json(data, json_path)
        loaded = FileHandler.load_json(json_path)
        
        self.assertEqual(loaded['test'], 'data')
        self.assertEqual(loaded['number'], 42)


class TestCDBModifier(unittest.TestCase):
    """CDB 修改器测试"""
    
    def test_create_and_modify(self):
        """测试创建和修改 CDB"""
        modifier = CDBModifier.create_empty()
        
        entry = modifier.add_entry(1, {'name': 'test', 'value': 100})
        self.assertIsNotNone(entry)
        
        modifier.modify_entry(1, 'value', 200)
        entry = modifier.get_entry(1)
        self.assertEqual(entry.get('value'), 200)


class TestPakPacker(unittest.TestCase):
    """Pak 打包器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def test_pack_and_unpack(self):
        """测试打包和解包"""
        packer = PakPacker()
        
        # 添加资源
        packer.add_resource('test.txt', b'Hello, World!', 'text')
        packer.add_resource('data.json', b'{"key": "value"}', 'json')
        
        # 打包
        pak_path = self.temp_dir / 'test.pak'
        packer.pack(pak_path)
        self.assertTrue(pak_path.exists())
        
        # 加载
        loaded = PakPacker.load(pak_path)
        resources = loaded.list_resources()
        self.assertIn('test.txt', resources)


if __name__ == '__main__':
    unittest.main()
