# 使用示例

## 快速开始

### 1. 安装

```bash
cd SkinMaker
pip install -r requirements.txt
```

### 2. 创建第一个项目

```bash
python skinmaker.py project create MyFirstProject --path ./projects
```

### 3. 创建皮肤

```bash
cd projects/MyFirstProject
python ../../skinmaker.py skin create hero_skin
```

### 4. 构建皮肤

```bash
python ../../skinmaker.py skin build hero_skin --output output.png
```

## 详细示例

### 示例 1: 完整的项目工作流

```python
from pathlib import Path
from src.core import Project, ProjectConfig, AnimationConfig
from src.builders import BuilderFactory, BuildContext, DynamicBuilder
from src.transforms import TransformChain, PositionTransform, FlipTransform
from PIL import Image

# 1. 创建项目
project = Project.create(
    Path('./my_game_skins'),
    name='GameSkins',
    version='1.0.0'
)

# 2. 修改项目配置
project.config.animation = AnimationConfig(
    enabled=True,
    fps=24,
    loop=True
)
project.save()

# 3. 创建多个皮肤
for skin_name in ['hero_blue', 'hero_red', 'hero_gold']:
    project.create_skin(
        skin_name,
        display_name=f'{skin_name.title()} Skin',
        builder_type='dynamic'
    )

project.save()

# 4. 构建皮肤
for skin_name in project.list_skins():
    # 创建 Builder
    builder = BuilderFactory.create('dynamic', {
        'layer_count': 3,
        'canvas_width': 64,
        'canvas_height': 64
    })
    
    # 创建上下文
    context = BuildContext(
        skin_name=skin_name,
        builder_type='dynamic'
    )
    
    # 构建
    image = builder.execute(context)
    
    # 应用变换
    chain = TransformChain()
    chain.add_transform(PositionTransform(5, 5))
    image = chain.apply(image)
    
    # 保存
    output_path = project.output_dir / f'{skin_name}.png'
    from src.io import FileHandler
    FileHandler.save_image(image, output_path)

print("✓ 项目构建完成！")
```

### 示例 2: 动画皮肤构建

```python
from src.builders import AnimationBuilder
from PIL import Image
import math

# 创建动画
animator = AnimationBuilder({
    'fps': 24,
    'loop': True
})

# 生成 8 帧旋转动画
for i in range(8):
    angle = (i / 8) * 360
    
    # 创建基础图像
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    
    # 应用旋转变换
    from src.transforms import RotationTransform
    transform = RotationTransform(angle)
    rotated = transform.apply(img)
    
    # 添加到动画
    animator.add_frame(rotated)

# 保存为 GIF
animator.save_as_gif('animation.gif')
print("✓ 动画已生成：animation.gif")
```

### 示例 3: 调色板索引转换

```python
from src.rendering import Palette
from src.io import FileHandler
from pathlib import Path

# 加载原始图像
original_image = FileHandler.load_image(Path('original.png'))

# 创建调色板
palette = Palette(max_colors=256)
palette.build_from_image(original_image, dithering=True)

# 转换为索引图像
indexed_image = palette.to_indexed_image(original_image)

# 保存
FileHandler.save_image(indexed_image, Path('indexed.png'))
print(f"✓ 调色板转换完成，使用了 {palette.get_color_count()} 种颜色")
```

### 示例 4: Atlas 打包

```python
from src.rendering import Atlas
from src.io import FileHandler
from pathlib import Path

# 创建 Atlas
atlas = Atlas(
    width=512,
    height=512,
    padding=2
)

# 添加多个精灵图像
sprite_dir = Path('sprites')
for sprite_file in sprite_dir.glob('*.png'):
    image = FileHandler.load_image(sprite_file)
    atlas.add_image(sprite_file.stem, image)

# 构建 Atlas
atlas_image = atlas.build()

# 保存 Atlas 和坐标信息
FileHandler.save_image(atlas_image, Path('atlas.png'))

# 保存 UV 坐标
import json
uv_data = {}
for name in atlas.regions:
    uv_data[name] = atlas.get_uv_coordinates(name)

FileHandler.save_json(uv_data, Path('atlas_uv.json'))

print(f"✓ Atlas 构建完成：{len(atlas.regions)} 个精灵")
print(f"  大小：{atlas.width}x{atlas.height}")
```

### 示例 5: CDB 数据修改

```python
from src.io import CDBModifier
from pathlib import Path

# 创建或加载 CDB
cdb = CDBModifier.create_empty()

# 添加数据
hero_entry = cdb.add_entry(1001, {
    'name': 'Hero',
    'level': 1,
    'experience': 0,
    'health': 100
})

# 修改数据
cdb.modify_entry(1001, 'level', 10)
cdb.modify_entry(1001, 'experience', 5000)

# 保存
cdb.save(Path('heroes.json'))

# 加载和验证
cdb_loaded = CDBModifier()
cdb_loaded.load(Path('heroes.json'))
hero = cdb_loaded.get_entry(1001)
print(f"✓ 英雄数据：{hero.data}")
```

### 示例 6: 资源包打包

```python
from src.io import PakPacker, FileHandler
from pathlib import Path

# 创建打包器
packer = PakPacker()

# 添加配置文件
config_data = FileHandler.load_json(Path('config.json'))
packer.add_resource('config.json', str(config_data).encode('utf-8'), 'config')

# 添加图像文件
packer.add_file(Path('atlas.png'), 'textures/atlas', 'texture')
packer.add_file(Path('sprite1.png'), 'textures/sprite1', 'texture')

# 添加数据文件
packer.add_file(Path('heroes.json'), 'data/heroes', 'data')

# 打包
packer.pack(Path('game_resources.pak'))

# 获取信息
info = packer.get_info()
print(f"✓ 资源包已创建")
print(f"  资源数量：{info['resource_count']}")
print(f"  总大小：{info['total_size']} 字节")
```

### 示例 7: 变换链组合

```python
from src.transforms import (
    TransformChain, PositionTransform, RotationTransform,
    FlipTransform, WarpTransform
)
from src.io import FileHandler
from pathlib import Path

# 加载图像
image = FileHandler.load_image(Path('sprite.png'))

# 创建复杂的变换链
chain = (TransformChain()
    .add_transform(FlipTransform.horizontal())
    .add_transform(RotationTransform(45, expand=True))
    .add_transform(PositionTransform(10, 20)))

# 应用变换
result = chain.apply(image)

# 保存
FileHandler.save_image(result, Path('transformed.png'))
print("✓ 变换完成：transformed.png")
```

### 示例 8: 命令行使用

```bash
# 创建项目
python skinmaker.py project create GameAssets --path ./projects

# 进入项目目录
cd projects/GameAssets

# 创建多个皮肤
python ../../skinmaker.py skin create warrior --builder dynamic
python ../../skinmaker.py skin create mage --builder original
python ../../skinmaker.py skin create rogue --builder line

# 列出皮肤
python ../../skinmaker.py project list

# 构建所有皮肤
python ../../skinmaker.py build --output ./builds

# 打包项目
python ../../skinmaker.py pack --output project.pak
```

### 示例 9: 自定义 Builder

```python
from src.builders import BaseBuilder, BuilderFactory, BuildContext
from PIL import Image, ImageDraw

class CustomPatternBuilder(BaseBuilder):
    """生成自定义图案的 Builder"""
    
    def validate(self, context):
        return True
    
    def prepare(self, context):
        context.metadata['builder_type'] = 'pattern'
    
    def build(self, context):
        # 创建图案
        width = self.config.get('width', 64)
        height = self.config.get('height', 64)
        pattern_type = self.config.get('pattern', 'checker')
        
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        if pattern_type == 'checker':
            # 棋盘图案
            square_size = 8
            for y in range(0, height, square_size):
                for x in range(0, width, square_size):
                    if ((x // square_size) + (y // square_size)) % 2 == 0:
                        draw.rectangle(
                            [x, y, x + square_size, y + square_size],
                            fill=(255, 255, 255, 255)
                        )
        
        return image
    
    def post_process(self, image):
        return image

# 注册自定义 Builder
BuilderFactory.register('pattern', CustomPatternBuilder)

# 使用
builder = BuilderFactory.create('pattern', {
    'width': 128,
    'height': 128,
    'pattern': 'checker'
})

context = BuildContext(
    skin_name='pattern_test',
    builder_type='pattern'
)

result = builder.execute(context)
result.save('pattern.png')
print("✓ 自定义 Builder 测试完成")
```

## 性能优化建议

### 1. 图像处理
- 使用合适的图像格式（PNG vs JPEG）
- 避免不必要的格式转换
- 对于大图像考虑分块处理

### 2. Atlas 构建
- 使用适当的 padding 值（2-4）
- 启用 Atlas 折叠以减少大小
- 考虑不同的打包顺序

### 3. 并行处理
```python
from multiprocessing import Pool

def build_skin(skin_name):
    # 构建逻辑
    pass

if __name__ == '__main__':
    skins = project.list_skins()
    with Pool(4) as pool:
        results = pool.map(build_skin, skins)
```

### 4. 缓存
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_palette_for_image(image_hash):
    # 调色板计算
    pass
```

## 故障排除

### 问题 1: 导入错误
**解决方案**: 确保项目根目录在 Python 路径中
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### 问题 2: 内存不足
**解决方案**: 使用流式处理或分块处理
```python
# 分块处理大图像
chunk_size = 512
```

### 问题 3: 文件权限错误
**解决方案**: 检查文件权限和目录权限
```python
from src.io import FileHandler
FileHandler.ensure_directory(output_dir)
```

## 最佳实践

1. **使用类型提示**: 提高代码可读性和错误检测
2. **错误处理**: 使用 try-except 捕获异常
3. **日志记录**: 使用 logging 模块记录重要信息
4. **测试**: 为自定义模块编写单元测试
5. **配置管理**: 使用外部配置文件管理参数
6. **版本控制**: 使用 Git 管理项目版本
