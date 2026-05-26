# SkinMaker - Python 皮肤制作工具

完整的 Python 重构架构，将 `SkinMaker.jar` 的逻辑拆解成模块化的 Python 实现。

## 项目结构

```
SkinMaker/
├── src/
│   ├── core/                 # 核心模块
│   │   ├── constants.py      # 常量定义
│   │   ├── config.py         # 配置系统
│   │   ├── project.py        # 项目管理
│   │   └── __init__.py
│   │
│   ├── builders/             # Builder 系统
│   │   ├── base.py           # 基类
│   │   ├── dynamic_builder.py
│   │   ├── original_builder.py
│   │   ├── line_builder.py
│   │   ├── animation_builder.py
│   │   └── __init__.py
│   │
│   ├── transforms/           # 变换系统
│   │   ├── base.py
│   │   ├── position.py       # 位置变换
│   │   ├── rotation.py       # 旋转变换
│   │   ├── flip.py           # 翻转变换
│   │   ├── warp.py           # 扭曲变换
│   │   └── __init__.py
│   │
│   ├── rendering/            # 渲染系统
│   │   ├── draw_order.py     # 绘制顺序
│   │   ├── palette.py        # 调色板索引
│   │   ├── atlas.py          # Atlas 管理
│   │   └── __init__.py
│   │
│   ├── io/                   # I/O 系统
│   │   ├── file_handler.py   # 文件处理
│   │   ├── cdb_modifier.py   # CDB 修改
│   │   ├── pak_packer.py     # Pak 打包
│   │   └── __init__.py
│   │
│   ├── cli/                  # CLI 系统
│   │   ├── parser.py         # 参数解析
│   │   ├── commands.py       # 命令处理
│   │   ├── main.py           # CLI 入口
│   │   └── __init__.py
│   │
│   ├── __init__.py           # 主模块
│   └── main.py               # 应用入口
│
├── tests/                    # 测试
│   ├── test_builders.py
│   ├── test_transforms.py
│   ├── test_rendering.py
│   ├── test_io.py
│   └── __init__.py
│
├── data/
│   ├── templates/            # 模板文件
│   └── samples/              # 示例文件
│
├── docs/                     # 文档
│   ├── architecture.md
│   ├── api.md
│   └── examples.md
│
├── skinmaker.py              # 命令行入口
├── requirements.txt          # 依赖
├── setup.py                  # 安装脚本
└── README.md                 # 本文件
```

## 功能模块

### 核心模块 (core)
- **ProjectConfig**: 项目配置管理
- **SkinConfig**: 皮肤配置管理
- **Project**: 项目生命周期管理
- **Constants**: 全局常量和枚举

### Builder 系统 (builders)
- **DynamicBuilder**: 动态皮肤构建
- **OriginalBuilder**: 原始皮肤处理
- **LineBuilder**: 轮廓线皮肤生成
- **AnimationBuilder**: 动画帧管理
- **BuilderFactory**: Builder 工厂模式

### 变换系统 (transforms)
- **PositionTransform**: 位置平移
- **RotationTransform**: 旋转变换
- **FlipTransform**: 翻转变换
- **WarpTransform**: 扭曲/透视变换
- **TransformChain**: 变换链式处理

### 渲染系统 (rendering)
- **DrawOrderSystem**: 图层绘制顺序管理
- **Palette**: 颜色调色板索引
- **Atlas**: 多图像 Atlas 打包
- **AtlasRegion**: Atlas 中的区域信息

### I/O 系统 (io)
- **FileHandler**: 通用文件处理
- **CDBModifier**: CDB 数据库修改
- **PakPacker**: res.pak 资源包管理

### CLI 系统 (cli)
- **CLIParser**: 命令行参数解析
- **CommandHandler**: 命令处理器
- **SkinMakerCLI**: CLI 主类
- **main()**: 命令行入口

## 使用示例

### 创建项目
```bash
python skinmaker.py project create MyProject --path ./my_project
```

### 创建皮肤
```bash
python skinmaker.py skin create hero_skin --builder dynamic
```

### 构建皮肤
```bash
python skinmaker.py skin build hero_skin --output output.png
```

### 构建所有皮肤
```bash
python skinmaker.py build
```

### 打包项目
```bash
python skinmaker.py pack --output project.pak
```

## Python 代码示例

### 基础使用
```python
from src.core import Project

# 创建项目
project = Project.create(Path('./my_project'), 'MyProject')

# 创建皮肤
skin = project.create_skin('hero_skin', builder_type='dynamic')

# 保存项目
project.save()
```

### 使用 Builder
```python
from src.builders import BuilderFactory, BuildContext
from PIL import Image

# 创建 Builder
builder = BuilderFactory.create('dynamic', {
    'layer_count': 2,
    'canvas_width': 64,
    'canvas_height': 64
})

# 构建
context = BuildContext(
    skin_name='my_skin',
    builder_type='dynamic',
    source_image=Image.new('RGBA', (64, 64))
)

result_image = builder.execute(context)
```

### 变换链
```python
from src.transforms import TransformChain, PositionTransform, FlipTransform

chain = TransformChain()
chain.add_transform(PositionTransform(10, 20))
chain.add_transform(FlipTransform.horizontal())

result = chain.apply(image)
```

### 调色板索引
```python
from src.rendering import Palette

palette = Palette(256)
palette.build_from_image(image)

# 转换为索引图像
indexed_img = palette.to_indexed_image(image)
```

### Atlas 管理
```python
from src.rendering import Atlas

atlas = Atlas(2048, 2048)
atlas.add_image('sprite1', image1)
atlas.add_image('sprite2', image2)

# 获取 UV 坐标
uv = atlas.get_uv_coordinates('sprite1')

# 构建 Atlas
atlas_image = atlas.build()
```

### 资源打包
```python
from src.io import PakPacker

packer = PakPacker()
packer.add_resource('config.json', config_data)
packer.add_file(Path('texture.png'))

packer.pack(Path('output.pak'))
```

## 运行测试

```bash
# 运行所有测试
python -m unittest discover -s tests -p "test_*.py"

# 运行特定测试
python -m unittest tests.test_builders
python -m unittest tests.test_transforms
python -m unittest tests.test_rendering
python -m unittest tests.test_io
```

## 安装依赖

```bash
pip install -r requirements.txt
```

或使用 setup.py 安装：

```bash
pip install -e .
```

## 架构设计特点

1. **模块化设计**: 各功能模块独立，易于扩展
2. **工厂模式**: Builder 和其他可扩展组件使用工厂模式
3. **链式处理**: Transform 系统支持链式操作
4. **配置驱动**: 使用 JSON 配置文件管理项目和皮肤
5. **可扩展的 CLI**: 易于添加新的命令和子命令
6. **完整的测试框架**: 包含 unit 测试用例

## 扩展指南

### 添加新的 Builder
```python
from src.builders import BaseBuilder, BuilderFactory

class MyBuilder(BaseBuilder):
    def validate(self, context):
        # 实现验证逻辑
        pass
    
    def prepare(self, context):
        # 实现准备逻辑
        pass
    
    def build(self, context):
        # 实现构建逻辑
        pass
    
    def post_process(self, image):
        # 实现后处理
        pass

# 注册 Builder
BuilderFactory.register('my_builder', MyBuilder)
```

### 添加新的变换
```python
from src.transforms import BaseTransform

class MyTransform(BaseTransform):
    def apply(self, image):
        # 实现变换逻辑
        return transformed_image
```

## 许可证

MIT License

## 联系方式

- Email: team@skinmaker.dev
- Issues: https://github.com/yourusername/skinmaker/issues
