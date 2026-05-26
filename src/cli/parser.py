"""
CLI 参数解析模块
"""

import argparse
from typing import Dict, Any, Optional
from pathlib import Path


class CLIParser:
    """
    CLI 参数解析器
    """
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description='SkinMaker - Python 皮肤制作工具',
            prog='skinmaker'
        )
        self._setup_parser()
    
    def _setup_parser(self) -> None:
        """设置解析器"""
        # 全局参数
        self.parser.add_argument(
            '--version', 
            action='version', 
            version='%(prog)s 1.0.0'
        )
        self.parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='启用详细输出'
        )
        self.parser.add_argument(
            '--config',
            type=str,
            help='配置文件路径'
        )
        
        # 子命令
        subparsers = self.parser.add_subparsers(dest='command', help='可用的命令')
        
        # project 命令
        project_parser = subparsers.add_parser('project', help='项目管理命令')
        project_subparsers = project_parser.add_subparsers(dest='project_command')
        
        # project create
        create_parser = project_subparsers.add_parser('create', help='创建新项目')
        create_parser.add_argument('name', help='项目名称')
        create_parser.add_argument('--path', default='.', help='项目路径')
        create_parser.add_argument('--version', default='1.0.0', help='项目版本')
        
        # project list
        project_subparsers.add_parser('list', help='列出项目中的皮肤')
        
        # skin 命令
        skin_parser = subparsers.add_parser('skin', help='皮肤管理命令')
        skin_subparsers = skin_parser.add_subparsers(dest='skin_command')
        
        # skin create
        skin_create_parser = skin_subparsers.add_parser('create', help='创建新皮肤')
        skin_create_parser.add_argument('name', help='皮肤名称')
        skin_create_parser.add_argument(
            '--builder', 
            choices=['dynamic', 'original', 'line'],
            default='dynamic',
            help='Builder 类型'
        )
        skin_create_parser.add_argument('--display-name', help='皮肤显示名称')
        
        # skin build
        skin_build_parser = skin_subparsers.add_parser('build', help='构建皮肤')
        skin_build_parser.add_argument('name', help='皮肤名称')
        skin_build_parser.add_argument('--output', help='输出文件路径')
        
        # build 命令
        build_parser = subparsers.add_parser('build', help='构建所有皮肤')
        build_parser.add_argument('--output', help='输出目录')
        
        # pack 命令
        pack_parser = subparsers.add_parser('pack', help='打包项目')
        pack_parser.add_argument('--output', help='输出文件路径')
    
    def parse(self, args: Optional[list] = None) -> argparse.Namespace:
        """解析命令行参数"""
        return self.parser.parse_args(args)
    
    def get_parser(self) -> argparse.ArgumentParser:
        """获取 ArgumentParser 对象"""
        return self.parser
