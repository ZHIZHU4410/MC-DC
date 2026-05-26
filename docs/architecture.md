# 架构文档

## 设计原则

### 1. 模块化
项目被分为不同的职责域，每个模块独立：
- **core**: 核心配置和项目管理
- **builders**: 皮肤构建逻辑
- **transforms**: 图像变换操作
- **rendering**: 绘制和渲染系统
- **io**: 文件和数据处理
- **cli**: 命令行接口

### 2. 可扩展性
- 工厂模式（Builder、命令）
- 链式处理（Transform）
- 插件化设计

### 3. 配置驱动
- JSON 配置文件
- 灵活的参数系统
- 运行时配置修改

## 架构图

```
┌─────────────────────────────────────────┐
│           CLI 层 (cli/)                  │
│  - 参数解析                              │
│  - 命令路由                              │
│  - 用户交互                              │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│         命令处理层 (commands/)           │
│  - project 命令                          │
│  - skin 命令                             │
│  - build 命令                            │
│  - pack 命令                             │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
┌───────▼─┐  ┌────▼────┐ ┌──▼─────────┐
│ 核心层  │  │构建层   │ │渲染层      │
│ (core/) │  │(builder)│ │(rendering/)│
│         │  │         │ │            │
│Project  │  │Builder  │ │DrawOrder   │
│Config   │  │Factory  │ │Palette     │
└─────────┘  └────┬────┘ │Atlas       │
                  │      └────────────┘
        ┌─────────┴────────┐
        │                  │
    ┌───▼────────┐  ┌──────▼──┐
    │变换层      │  │I/O 层   │
    │(transforms)│  │(io/)    │
    │            │  │         │
    │Position    │  │FileH.   │
    │Rotation    │  │CDB      │
    │Flip        │  │Pak      │
    │Warp        │  └─────────┘
    └────────────┘
```

## 数据流

### 项目创建流程
```
create project
      │
      ├─ 创建 ProjectConfig
      ├─ 创建 Project 实例
      ├─ 初始化目录结构
      └─ 保存配置文件
```

### 皮肤构建流程
```
build skin
      │
      ├─ 加载皮肤配置
      ├─ 选择 Builder
      ├─ 创建 BuildContext
      ├─ Builder.execute()
      │   ├─ validate()
      │   ├─ prepare()
      │   ├─ build()
      │   └─ post_process()
      ├─ 应用变换链
      ├─ 调整颜色/索引
      └─ 保存输出
```

### Atlas 构建流程
```
build atlas
      │
      ├─ 添加多个图像
      ├─ 自动布局（打包算法）
      ├─ 可选：折叠优化
      ├─ 构建最终 Atlas 图像
      └─ 生成 UV 坐标映射
```

## 类设计

### Project 类
```
Project
├─ root_path: Path
├─ config: ProjectConfig
├─ skins: Dict[str, SkinConfig]
└─ 方法
   ├─ create_skin()
   ├─ get_skin()
   ├─ save()
   └─ load()
```

### Builder 继承层次
```
BaseBuilder (抽象类)
├─ DynamicBuilder
├─ OriginalBuilder
└─ LineBuilder
```

### Transform 继承层次
```
BaseTransform (抽象类)
├─ PositionTransform
├─ RotationTransform
├─ FlipTransform
└─ WarpTransform
```

## 配置文件结构

### project.json
```json
{
  "name": "MyProject",
  "version": "1.0.0",
  "author": "Author Name",
  "output_format": "png",
  "animation": {
    "enabled": true,
    "fps": 24,
    "loop": true
  },
  "atlas": {
    "width": 2048,
    "height": 2048,
    "padding": 2
  },
  "palette": {
    "indexed": true,
    "max_colors": 256
  }
}
```

### skin_name.json
```json
{
  "name": "skin_name",
  "display_name": "Display Name",
  "builder_type": "dynamic",
  "transforms": {
    "position": [0, 0],
    "rotation": 0,
    "flip": "none"
  },
  "layers": {
    "layer1": {...},
    "layer2": {...}
  },
  "animation_frames": 1
}
```

## 扩展点

### 添加新 Builder
1. 继承 `BaseBuilder`
2. 实现 `validate()`, `prepare()`, `build()`, `post_process()`
3. 在 `__init__.py` 中注册

### 添加新 Transform
1. 继承 `BaseTransform`
2. 实现 `apply()` 方法
3. 可选：添加到 `TransformChain`

### 添加新命令
1. 在 `CLIParser` 中添加子命令
2. 在 `CommandHandler` 中实现处理方法
3. 在 `SkinMakerCLI.run()` 中添加路由

## 性能考虑

### 图像处理
- 使用 PIL 的优化路径
- 避免不必要的格式转换
- 考虑内存效率（大图像）

### Atlas 打包
- 使用贪心算法快速布局
- 可选择不同的打包策略
- 支持 Atlas 折叠优化

### 调色板索引
- 仅在需要时进行索引转换
- 支持抖动算法选择

## 测试策略

### 单元测试
- 每个模块独立测试
- Mock 外部依赖
- 测试异常情况

### 集成测试
- 完整工作流测试
- 端到端命令测试
- 文件 I/O 验证

## 部署和分发

### PyPI 发布
1. 配置 `setup.py`
2. 创建源分发: `python setup.py sdist bdist_wheel`
3. 上传到 PyPI: `twine upload dist/*`

### 可执行文件
1. 使用 PyInstaller
2. 生成单一可执行文件
3. 支持跨平台分发

## 安全考虑

- 验证所有输入参数
- 检查文件路径安全性
- 限制资源使用（内存、磁盘）
- 处理异常情况

## 未来扩展

1. **GUI 界面**: 基于当前架构构建 GUI
2. **WebUI**: 提供 Web 服务接口
3. **插件系统**: 支持第三方插件
4. **云存储**: 集成云存储支持
5. **实时预览**: 实时显示构建结果
6. **批量处理**: 并行构建多个皮肤
