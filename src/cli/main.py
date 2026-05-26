"""
CLI 主入口模块
"""

import sys
from pathlib import Path
from .parser import CLIParser
from .commands import CommandHandler, CommandResult


class SkinMakerCLI:
    """
    SkinMaker CLI 主类
    """
    
    def __init__(self):
        self.parser = CLIParser()
        self.handler: CommandHandler = None
    
    def run(self, args=None) -> int:
        """
        运行 CLI
        
        Args:
            args: 命令行参数列表
            
        Returns:
            退出码
        """
        try:
            parsed_args = self.parser.parse(args)
            
            # 初始化命令处理器
            self.handler = CommandHandler(Path.cwd())
            
            if not parsed_args.command:
                self.parser.get_parser().print_help()
                return 0
            
            # 路由到对应的命令处理
            if parsed_args.command == 'project':
                return self._handle_project(parsed_args)
            elif parsed_args.command == 'skin':
                return self._handle_skin(parsed_args)
            elif parsed_args.command == 'build':
                return self._handle_build(parsed_args)
            elif parsed_args.command == 'pack':
                return self._handle_pack(parsed_args)
            else:
                print(f"未知的命令: {parsed_args.command}")
                return 1
        
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    def _handle_project(self, args) -> int:
        """处理 project 命令"""
        if not args.project_command:
            print("请指定 project 子命令: create, list")
            return 1
        
        if args.project_command == 'create':
            result = self.handler.project_create(
                args.name,
                args.version,
                args.path
            )
        elif args.project_command == 'list':
            result = self.handler.project_list()
        else:
            print(f"未知的 project 子命令: {args.project_command}")
            return 1
        
        return self._print_result(result)
    
    def _handle_skin(self, args) -> int:
        """处理 skin 命令"""
        if not args.skin_command:
            print("请指定 skin 子命令: create, build")
            return 1
        
        if args.skin_command == 'create':
            result = self.handler.skin_create(
                args.name,
                args.builder,
                args.display_name
            )
        elif args.skin_command == 'build':
            result = self.handler.skin_build(args.name, args.output)
        else:
            print(f"未知的 skin 子命令: {args.skin_command}")
            return 1
        
        return self._print_result(result)
    
    def _handle_build(self, args) -> int:
        """处理 build 命令"""
        result = self.handler.build_all(args.output)
        return self._print_result(result)
    
    def _handle_pack(self, args) -> int:
        """处理 pack 命令"""
        result = self.handler.pack(args.output)
        return self._print_result(result)
    
    def _print_result(self, result: CommandResult) -> int:
        """打印命令结果"""
        if result.success:
            print(f"✓ {result.message}")
            return 0
        else:
            print(f"✗ {result.message}")
            return 1


def main(args=None) -> int:
    """主入口函数"""
    cli = SkinMakerCLI()
    return cli.run(args)


if __name__ == '__main__':
    sys.exit(main())
