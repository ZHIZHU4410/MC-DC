# Minecraft ↔ Dead Cells 原生双向桥接

独立项目根目录：`D:\steama\steamapps\common\Dead Cells\coremod\MC-DC`。

目标：在可转动第一/第三人称视角的三维 DC 世界中，由原生 MC 玩家行走、跳跃、创建/摧毁方块。DC 保留世界身份、关卡与显示入口，MC 保留原生玩家逻辑。

本轮按用户要求收紧画面边界：MC 可见元素仅为 UI、手臂和装备，其余来自 DC。已实现 [DC 原素材与世界渲染隔离切片](docs/DC_VISUAL_WORLD_SLICE.md)并完成双游戏实机验收；真实 DC prison 材质、MC 原生 UI/手臂、DC 窗口内帧上传与 F7 恢复有归档证据。MC 现在也可先启动并等待 DC 后进入，超过旧 30 秒窗口的真实握手测试通过。当前三维场景仍有大面积空域，缺少 DC 背景、逐格装饰、敌人、第三人称 DC 角色和双向编辑/战斗，不是可玩成品。

当前交付：**归档真实DC地图的2515个实体格已落成10060个MC原生方块。DC保持前台，键鼠操控后台MC原生玩家，走跳/撞墙、鼠标转向、F5第一/第三人称、E原生库存开关/显示及F7两端恢复已合成实机通过；最新254次GPU→DC内部上传逐帧配对。库存期间原生移动被抑制。当前DC实体格门控、错误地图拒绝、正常关闭前回滚及同一存档重载通过。原生方块路径没有安装诊断碰撞层。库存槽位操作、挖放、战斗及实时双向世界同步仍未完成，这是实验源码，不是可玩成品。** 见[库存切片](docs/NATIVE_INVENTORY_SLICE.md)、[原生方块世界](docs/NATIVE_BLOCK_WORLD.md)、[前台输入实验](docs/NATIVE_INPUT_LAB.md)。

本仓库仅包含项目源码、测试和复现工具。游戏文件、第三方反编译源码、独立实验存档、运行日志与私有会话凭据不在发布范围内。工具目前针对本机Windows实验环境，部分路径需要调整。实现由用户指导并由OpenAI Codex协作完成；依赖与参考来源见`research/sources.json`。未指定项目代码许可证，第三方组件仍适用各自条款。

- [GitHub 预研及源码证据](research/GITHUB_RESEARCH.md)
- [MCDN 协议草案](docs/PROTOCOL_DRAFT.md)
- [最小闭环路径及验收](docs/MINIMUM_LOOP_PLAN.md)
- [指定 ICEY 历史学习记录](REFERENCE_STUDY.md)
- [来源提交/文件清单](research/sources.json)
- [当前实现、验证范围与下一步](docs/IMPLEMENTATION_STATUS.md)
- [桥接契约入口](docs/CONTRACT.md)
- [下一切片：握手、输入租约与MC26.3入口](docs/CONTROL_SLICE.md)
- [当前切片：世界几何与客体接管门控](docs/WORLD_MODE_SLICE.md)
- [v0.5：实际加载与隔离诊断步骤](docs/LAB_SLICE.md)
- [真实 DC→MC 碰撞查询证据与隔离启动](docs/DC_RUNTIME_SLICE.md)
- [v0.6：原生三槽帧邮箱及跨进程故障验证](docs/FRAME_MAILBOX_SLICE.md)
- [下一片：MC26.3 原生渲染目标采集诊断](docs/NATIVE_FRAME_PROBE.md)
- [DC 原生纹理/HUD 记录帧显示诊断](docs/DC_TEXTURE_SLICE.md)
- [实时原生完整场景通道与626帧实机验收](docs/LIVE_COLOR_SLICE.md)
- [已通过：独立原生玩家物理测试](docs/NATIVE_PHYSICS_SLICE.md)

## 新增

原生玩家物理切片已实机通过：独立和平实例`MC-DC-Physics-26.3`中，真实客户端200个、集成服务器199个采样一致；身体限位X=2.25，自由跳跃约1.252格、低顶约0.700格，170条输入消费后超时清键并恢复原输入/相机/地面位置/模式。本次显示实体已丢弃，游戏正常退出码0；包、源码、轨迹和GPU图像已归档独立复核。这是合成MCDW场景及本地脚本组件集成，不授予生产MODE或DC输入接管。

实时完整场景诊断已接通：独立MCWC帧保留捕获时姿态/矩阵/原生tick/QPC，经有类型Win32邮箱到DC原生Texture/HUD。33组跨语言样本、20帧合成跨进程传输及旧邮箱五项故障回归通过。实机626帧全部配对上传，DC前台时MC后台继续采集；5秒诊断快照文件占用不中断帧流，主动停止后约1.49秒观察到清理。两款实验游戏已正常退出，临时会话配置已解除。详见LIVE_COLOR_SLICE.md。这仍是MC超平坦完整场景预览，未完成DC网格显示、正式上下文协商或玩家接管。

DC原生纹理诊断已实机通过：修复HashLink重新构造RGBA枚举导致的同名格式转换错误，改用引擎已有nativeFormat对象。12帧连续上传返回，实际角色场景显示方向/颜色正常，返回标题画面后缩略图消失。证据在DC_TEXTURE_SLICE.md；这是记录帧回放，尚未连接实时邮箱。

真实MC主渲染目标采集已完成：最大化2560×1494异步GPU读回、后台拟合1024×598，12帧图像/姿态/矩阵及推进tick通过，图像已目视确认。这是含HUD的原生MC实验场景，尚不绘制DC网格，也没有冒充MCDF角色层。详见NATIVE_FRAME_PROBE.md。

原生 Win32 DLL 统一实现文件映射和 0ms 命名互斥，Java25 JNI 与 C# P/Invoke 五项跨进程测试通过：忙锁、槽复用、完整像素/姿态、u64 最大帧号、损坏像素及持锁进程退出。故障停用共享会话，旧文件不能重新接入。邮箱仍只测合成RGBA，与已通过的独立GPU帧诊断尚未合成正式通道。

world-1 能力协商及 WORLD/MODE 消息已接入真实 C#↔Java TCP；socket 解析、游戏线程分发和独立发送队列分开。消费 ACK 只越过已消费或取消的前缀。完整回归和新增 ACK 空洞、短按、失焦撤销、旧世界取消、坏流清键测试通过。此处帧、载体和输入 sink 仍是测试替身。

DC 局部碰撞导出和 Fabric 隔离诊断入口已实机加载：2555 个实际实体形状在 MC 客户端及集成服务器以相同摘要应用并被查询，7 个未支持格子没有冒充实体墙。原本地存档/配置核对零变化。隔离启动包含原生存档读写自检和加载器缺失拒绝测试，详见实机记录；不授予输入控制。

新增C#/Java一致的完整几何快照、SHA256校验与有界分块接收；DC格网Y翻转和小数坐标保留。客体接管需双方几何回执、同帧合法身体空间、配对帧与载体准备齐备，再精确提交。原ClientInput保存/恢复、清键、部分安装失败回滚及恢复失败重试已验证。

23组几何样本及C#导出→Java接收通过；本机MC26.3原生VoxelShape夹具通过地板、小数墙、前后深度及天花板解算。这里只运行真实类型的夹具，尚未接入DC地图或真实MC世界。

已实现 Java/C# 的64字节信封、有限内存TCP增量拆包、会话/代次/无符号序号过滤，以及256字节帧头/像素快照校验。两语言各通过39组正常和损坏样本，256条实际回环TCP消息逐字节往返一致。

新增严格control-1 schema、一次性nonce/构建绑定握手、消费ACK窗口，以及MC侧128条输入队列、按键边沿、250ms租约和终止清键。两语言各50组控制样本、10000次双线程队列及实际TCP握手/按下/松开/断连验证通过。

已定位Microsoft JDK25.0.1，MC26.3输入适配类对真实JAR编译通过；真实ClientInput/Input/Vec2类型夹具验证七种按键、原生向量归一化和故障清零。探针安装不等于输入适配已接管；客户端/服务端物理仍未验收。

只读定位本机 MC 26.3 / Fabric Loader 0.20.0 / Fabric API 0.164.0+26.3。配置要求Java25，游戏JAR抽样class major=69；PATH Java21用于独立协议验证。DCCM35.13.9与本机GameProxy指纹已记录。

## 运行验证

需要 Python 3、.NET 10 SDK、JDK 21或更高；独立协议不依赖第三方包，不启动游戏。在项目根目录运行：

```powershell
python tools/verify_protocol.py
python tools/verify_control.py
python tools/verify_world.py
python tools/verify_pipeline.py
```

输出 `artifacts/protocol/report.json`，含检查结果及源码/样本SHA256。诊断端点只绑定127.0.0.1临时端口；echo不授予游戏控制权。MC26.3游戏适配仍需Java25。

只读环境指纹：

```powershell
python tools/inspect_environment.py --mc-version-dir 'D:\MC\愚者\懒人包\.minecraft\versions\26.3-Fabric 0.20.0'
```

输出 `artifacts/environment.json`；安装文件指纹不代表运行进程加载代码已核验。

## 修正

废止 ReverseStrongCompat 窗口嵌入作为目标实现。确认 crossover 示例的焦点路径不符合 DC 前台输入要求；MineCells 只作内容参考；DC 世界结构不能用 seed 或同名 LevelId 代替；ICEY 历史通过不算 MC 验收。

## 还做不到

尚未完成完整DC碰撞语义、MC世界物理隔离、生产会话/上下文核验、DC Hero旁路/恢复和正式MCDF角色帧通道。诊断导出只覆盖局部Plain/Invisible实体；单向平台、翻滚通道、梯子、斜坡等不能冒充实体墙。原生运动只在合成场景通过，实时完整场景显示只作诊断；真实DC输入运动、三维DC显示、挖放、库存、战斗和输入至显示延迟仍未验收。

下一步接正式会话/输入协调、真实DC几何的原生运动与可撤销Hero载体，再补三维视觉。不静默降级MC或套用上游1.21.1适配。代理按用户授权离线操作独立实验实例，修改前备份；未修改ICEY工程。
