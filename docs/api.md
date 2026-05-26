# API 文档

## 核心模块 (core)

### ProjectConfig
项目配置类
```python
ProjectConfig(
    name: str,
    version: str = "1.0.0",
    author: str = "",
    animation: AnimationConfig = ...,
    atlas: AtlasConfig = ...,
    palette: PaletteConfig = ...
)

# 方法
.to_dict() -> Dict          # 转换为字典
.save(filepath: Path)       # 保存到文件
.load(filepath: Path)       # 从文件加载（类方法）
.from_dict(data: Dict)      # 从字典创建（类方法）
```

### SkinConfig
皮肤配置类
```python
SkinConfig(
    name: str,
    display_name: str = "",
    builder_type: str = "dynamic",
    transforms: Dict = {},
    layers: Dict = {},
    animation_frames: int = 1
)

# 方法
.to_dict() -> Dict
.save(filepath: Path)
.load(filepath: Path)
```

### Project
项目管理类
```python
Project(root_path: Path, config: ProjectConfig)

# 属性
.root_path -> Path          # 项目根目录
.config -> ProjectConfig    # 项目配置
.skins -> Dict[str, SkinConfig]  # 皮肤集合
.skins_dir -> Path          # 皮肤目录
.output_dir -> Path         # 输出目录

# 方法
.create_skin(name, display_name, builder_type) -> SkinConfig
.get_skin(name) -> SkinConfig | None
.remove_skin(name) -> bool
.list_skins() -> List[str]
.save()
.load(root_path) -> Project  # 类方法
.create(root_path, name, version) -> Project  # 类方法
```

## Builder 模块 (builders)

### BaseBuilder
抽象基类
```python
BaseBuilder(config: Dict[str, Any])

# 抽象方法
.validate(context: BuildContext) -> bool
.prepare(context: BuildContext)
.build(context: BuildContext) -> Image
.post_process(image: Image) -> Image

# 具体方法
.execute(context: BuildContext) -> Image  # 完整流程
```

### BuildContext
构建上下文
```python
BuildContext(
    skin_name: str,
    builder_type: str,
    source_image: Image | None = None,
    output_image: Image | None = None,
    layers: Dict[str, Image] = {},
    metadata: Dict = {}
)
```

### DynamicBuilder
动态构建器
```python
DynamicBuilder(config: Dict)
.add_content(context, layer_name, content, position)
```

### OriginalBuilder
原始图像处理器
```python
OriginalBuilder(config: Dict)
```

### LineBuilder
轮廓线构建器
```python
LineBuilder(config: Dict)
```

### AnimationBuilder
动画构建器
```python
AnimationBuilder(config: Dict)

# 属性
.fps -> int
.loop -> bool
.frames -> List[AnimationFrame]

# 方法
.add_frame(image: Image, duration: int)
.add_frames(images: List[Image])
.generate_animation() -> List[Image]
.save_as_gif(filepath: str)
.get_frame(index: int) -> Image
.get_frame_count() -> int
.clear()
```

### BuilderFactory
Builder 工厂
```python
BuilderFactory.register(name: str, builder_class: type)
BuilderFactory.create(builder_type: str, config: Dict) -> BaseBuilder
BuilderFactory.list_builders() -> List[str]
```

## Transform 模块 (transforms)

### BaseTransform
抽象基类
```python
BaseTransform()

# 属性
.enabled -> bool

# 抽象方法
.apply(image: Image) -> Image

# 可调用接口
__call__(image: Image) -> Image
```

### TransformChain
变换链
```python
TransformChain()

# 方法
.add_transform(transform: BaseTransform) -> TransformChain  # 链式调用
.apply(image: Image) -> Image
__call__(image: Image) -> Image
```

### PositionTransform
位置变换
```python
PositionTransform(x: int = 0, y: int = 0)

# 方法
.set_position(x: int, y: int)
.offset(dx: int, dy: int)
```

### RotationTransform
旋转变换
```python
RotationTransform(angle: float = 0.0, expand: bool = True)

# 方法
.set_angle(angle: float)
.rotate_by(delta: float)
.rotate_90() -> RotationTransform  # 静态方法
.rotate_180() -> RotationTransform
.rotate_270() -> RotationTransform
```

### FlipTransform
翻转变换
```python
FlipTransform(direction: Literal['h', 'v', 'both'] = 'h')

# 方法
.set_direction(direction)
.horizontal() -> FlipTransform  # 静态方法
.vertical() -> FlipTransform
.both() -> FlipTransform
```

### WarpTransform
扭曲变换
```python
WarpTransform(warp_type: str = 'perspective')

# 方法
.set_perspective_points(source_points, dest_points)
.skew(skew_x: float, skew_y: float)
```

## Rendering 模块 (rendering)

### DrawOrderSystem
绘制顺序系统
```python
DrawOrderSystem()

# 方法
.add_layer(name, order_level, visible, opacity)
.remove_layer(name) -> bool
.set_order_level(name, order_level)
.set_visibility(name, visible)
.set_opacity(name, opacity)
.get_draw_order() -> List[str]
.move_layer_forward(name)
.move_layer_backward(name)
.get_layer_info(name) -> DrawableLayer
.list_layers() -> List[str]
```

### Palette
调色板
```python
Palette(max_colors: int = 256)

# 方法
.add_color(color: Tuple[R,G,B,A]) -> int  # 返回索引
.get_color(index: int) -> Tuple | None
.get_index(color: Tuple) -> int | None
.build_from_image(image, dithering)
.to_indexed_image(image) -> Image
.get_color_count() -> int
```

### Atlas
Atlas 管理
```python
Atlas(width: int = 2048, height: int = 2048, padding: int = 2)

# 属性
.width -> int
.height -> int
.regions -> Dict[str, AtlasRegion]

# 方法
.add_image(name: str, image: Image) -> bool
.build(background_color) -> Image
.get_region(name) -> AtlasRegion | None
.get_uv_coordinates(name) -> Tuple | None  # (u_min, v_min, u_max, v_max)
.collapse(threshold: float = 0.9) -> bool
.get_info() -> Dict
```

## I/O 模块 (io)

### FileHandler
文件处理
```python
FileHandler.load_image(file_path: Path) -> Image
FileHandler.save_image(image, file_path, quality)
FileHandler.load_json(file_path) -> Dict
FileHandler.save_json(data, file_path, indent)
FileHandler.load_text(file_path, encoding) -> str
FileHandler.save_text(text, file_path, encoding)
FileHandler.copy_file(src, dst)
FileHandler.copy_directory(src, dst)
FileHandler.list_files(directory, pattern, recursive) -> List[Path]
FileHandler.ensure_directory(path)
FileHandler.get_file_size(file_path) -> int
FileHandler.file_exists(file_path) -> bool
```

### CDBModifier
CDB 修改器
```python
CDBModifier(file_path: Path | None = None)

# 方法
.load(file_path)
.add_entry(entry_id, data) -> CDBEntry
.get_entry(entry_id) -> CDBEntry | None
.modify_entry(entry_id, key, value) -> bool
.remove_entry(entry_id) -> bool
.get_all_entries() -> List[CDBEntry]
.save(file_path)
.export_to_json(file_path)
.create_empty() -> CDBModifier  # 类方法
```

### PakPacker
Pak 打包器
```python
PakPacker()

# 方法
.add_resource(name, data, resource_type)
.add_file(file_path, resource_name, resource_type)
.get_resource(name) -> PakResource | None
.list_resources() -> List[str]
.remove_resource(name) -> bool
.pack(output_path)
.unpack(pak_path, output_dir)
.load(pak_path) -> PakPacker  # 类方法
.get_info() -> Dict
```

## CLI 模块 (cli)

### CLIParser
参数解析器
```python
CLIParser()

# 方法
.parse(args: List | None) -> argparse.Namespace
.get_parser() -> argparse.ArgumentParser
```

### CommandHandler
命令处理器
```python
CommandHandler(project_path: Path = None)

# 方法
.load_project() -> CommandResult
.project_create(name, version, path) -> CommandResult
.project_list() -> CommandResult
.skin_create(name, builder, display_name) -> CommandResult
.skin_build(name, output) -> CommandResult
.build_all(output) -> CommandResult
.pack(output) -> CommandResult
```

### CommandResult
命令结果
```python
CommandResult(
    success: bool,
    message: str,
    data: Any | None = None
)
```

### SkinMakerCLI
CLI 主类
```python
SkinMakerCLI()

# 方法
.run(args: List | None) -> int  # 返回退出码
```

## 常用操作示例

### 创建和管理项目
```python
from pathlib import Path
from src.core import Project

# 创建项目
project = Project.create(Path('./my_project'), 'MyProject', '1.0.0')

# 创建皮肤
skin = project.create_skin('hero', display_name='Hero Skin', builder_type='dynamic')

# 获取皮肤
skin = project.get_skin('hero')

# 保存项目
project.save()

# 加载项目
project = Project.load(Path('./my_project'))
```

### 构建皮肤
```python
from src.builders import BuilderFactory, BuildContext
from PIL import Image

builder = BuilderFactory.create('dynamic', {
    'layer_count': 2,
    'canvas_width': 64,
    'canvas_height': 64
})

context = BuildContext(
    skin_name='my_skin',
    builder_type='dynamic',
    source_image=Image.new('RGBA', (64, 64))
)

result = builder.execute(context)
```

### 应用变换
```python
from src.transforms import TransformChain, PositionTransform, FlipTransform

chain = (TransformChain()
    .add_transform(PositionTransform(10, 20))
    .add_transform(FlipTransform.horizontal()))

result = chain.apply(image)
```

### 使用 Atlas
```python
from src.rendering import Atlas

atlas = Atlas(2048, 2048)
atlas.add_image('sprite1', img1)
atlas.add_image('sprite2', img2)
atlas.build()

uv = atlas.get_uv_coordinates('sprite1')
```

### 打包资源
```python
from src.io import PakPacker

packer = PakPacker()
packer.add_resource('config.json', config_bytes)
packer.add_file(Path('image.png'), 'texture')
packer.pack(Path('output.pak'))
```
