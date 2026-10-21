# GitHub 预研结论：MC ↔ DC 原生双向桥接

研究日期：2026-10-19，Asia/Shanghai。证据等级：源码静态阅读；本轮未运行这些项目或两款游戏。先完成本报告，再提出项目协议与实施路径。

## 结论先行

在本次审阅的仓库和资料范围内，**没有找到“DC 世界身份 + MC 原生玩家逻辑”的完整可直接采用先例**。这不是对所有互联网项目的穷尽性证明。

| 项目 | 实际类别 | 可借鉴点 | 不可借鉴点 | 与 MC↔DC 的差异 |
|---|---|---|---|---|
| justbustin/minecraft-crossover-bridge | 像素合成 + 相机/碰撞/战斗状态桥 | C/Java 字节布局；控制/帧映射分离；完整帧先于配对姿态发布；游戏线程调用；玩家载体 | MC 窗口持有输入焦点及 F8 切窗口路径；透明桌面 overlay fallback；宿主地址与平台屏障假设 | MC 1.21.1、macOS/CrossOver、MHW/ER D3D，不是 Windows/DC HashLink；没有 DC 二维世界三维化 |
| MartianLee 十二项目文章 | 像素 / 网格 / 逻辑 / 无独立桥的分类索引 | 识别跨桥数据、渲染责任及 README/源码差异 | 二手静态阅读与算术带宽不能当实机或性能证明 | 不是实现库，也不是 MC↔DC 验证；四分类不等于功能完成度 |
| dead-cells-core-modding/core | DC 进程内加载/Hook 框架 | ModBase、modinfo、FrameUpdate、Hero init/dispose、原函数链及主线程上下文 | 把“有 Hook”当作已正确旁路玩家物理/伤害；无须重新校验绑定的假设 | 不自带外来玩家、MC 原生接口、跨进程协议或项目 worldEpoch |
| vaiserYT/DeadCellsMultiplayerMod | DC↔DC 世界与实体状态同步 | 位置/朝向/房间；Generation + NetId；过关提交序号/目的地；生成图/RNG；主线程消费 | 用 Ghost 或 DC 动画名代替原生 MC；照搬网络生成实体/多人存档 | 两端都是 DC，同步目标不是外来原生玩家；没有 MC 镜像物理/真实帧 |
| mim1q/MineCells | 单游戏内容移植 | 区域、材质、块/门/敌人的内容分类映射 | 其单 MC 架构不能充当进程桥；保留权利的纹理/模型不复制 | 不运行 DC，没有 DC 世界身份、载体或当前实际关卡回路 |
| chasmlol/SkyCraft（补充） | 网格合成 + HUD 像素 + 宿主输入/碰撞/实体桥 | 宿主→MC 输入环、release-all、菜单/加载标志；MC 原生块网格 | Skyrim 的 D3D11 世界 pass、坐标/碰撞实现；将设计文档等同实际代码 | 宿主是 SKSE/Skyrim；DC 的三维场景与二维机制深度适配要另做 |
| Xu060113/SekiroCraft-Passthrough（补充） | 实验性共享内存及 D3D11 显示合成 | Windows 像素合成的相邻项目索引 | 本轮未审计完整源码，其输入/战斗实现不作为确定结论 | MC 1.20.1/Sekiro，不是 DC；仅 README 级证据 |
| BennettCode/Skyring（补充） | 逻辑与姿态桥 | 输入状态、协议模式、过期数据约束，分清原生状态与宿主计算 | 未审计的战斗数学；把状态/骨骼当作真实像素帧 | ER→Skyrim，不传 MC 真帧；本轮只核对 schema |
| Ilyaki/ProtoInput（补充） | Windows 输入重定向 | 设备路由、按键释放、失焦与游戏内部消费的区分 | 将通用 Windows Hook 当作原生 MC 玩法入口或完整桥 | 不提供跨游戏世界/显示/玩家物理；本项目优先进程内游戏输入 |

## 1. minecraft-crossover-bridge：协议、帧槽、生命周期、输入

固定源码提交：`d1723873ec8f370389cf19f74fac455b9e581321`。

审阅的主要文件：

- [bridge_protocol.h](https://github.com/justbustin/minecraft-crossover-bridge/blob/d1723873ec8f370389cf19f74fac455b9e581321/elden-ring/er-bridge/include/bridge_protocol.h)
- [FramePassthrough.java](https://github.com/justbustin/minecraft-crossover-bridge/blob/d1723873ec8f370389cf19f74fac455b9e581321/elden-ring/mc-bridge/src/client/java/dev/ermc/bridge/client/FramePassthrough.java)
- [Overlay.java](https://github.com/justbustin/minecraft-crossover-bridge/blob/d1723873ec8f370389cf19f74fac455b9e581321/elden-ring/mc-bridge/src/client/java/dev/ermc/bridge/client/Overlay.java)
- [ErLink.java](https://github.com/justbustin/minecraft-crossover-bridge/blob/d1723873ec8f370389cf19f74fac455b9e581321/elden-ring/mc-bridge/src/main/java/dev/ermc/bridge/link/ErLink.java)、[shm.cpp](https://github.com/justbustin/minecraft-crossover-bridge/blob/d1723873ec8f370389cf19f74fac455b9e581321/elden-ring/er-bridge/src/shm.cpp)、[frame.cpp](https://github.com/justbustin/minecraft-crossover-bridge/blob/d1723873ec8f370389cf19f74fac455b9e581321/elden-ring/er-bridge/src/frame.cpp)

观察：

1. 控制映射是 8 MiB，头含 magic/version/size、双侧 heartbeat、PID/start 时间及重载/切换请求计数。ER 与 MHW 沿用相同 magic，但通过不同目录隔离，不能据此认为 magic 足以识别会话。
2. 独立帧映射版本为 2：3 个槽，每槽 256 字节头 + 最大 1920×1200×16 字节四层容量。实际层为 world RGBA、float depth、GUI RGBA、可选 hand RGBA；行方向和预乘 alpha 明确。
3. Java 发布流程：槽序号置奇数 → 填像素与头 → release 发布偶数 → 发布 latest → 最后发布匹配该帧的控制姿态。异步 GPU 读回保存原捕获时姿态，避免拿旧像素配新相机。
4. 该代码依赖其 x86/Rosetta 内存顺序假设、编译器屏障和 Java acquire/release。不能直接转写成 C# volatile 后就认定 Java/C# 进程间原子性成立。
5. ErLink 会等待 heartbeat 实际变化，避免把残留文件里的旧值当活跃宿主。frame.cpp 先收集状态，再短时间发布；游戏主线程工作与呈现线程职责分开。
6. **输入不符合本项目要求**：FramePassthrough 明说 MC 窗口保留输入焦点；Overlay.switchToHost/switchToMc 使用 hide/show/focus，并请求宿主焦点。这证明渲染合成与“DC 前台消费输入”是两件事。

该仓库确有地形/战斗桥接实现，不应误写成“只做截图”；但它未解决 DC 世界身份、二维→三维映射、DC 墙体修改及本项目的前台输入契约。

## 2. 分类文章及补充项目的边界

[What Crosses the Bridge Between Two Games?](https://martianlee.github.io/posts/2026-10-08-passthrough-bridge-spectrum) 自述为 2026-10-08 的静态审阅，不是实机评测。本文只采用其四类数据责任框架和仓库索引；实现判断回查对应主源。

- 像素：由客体绘制，发送颜色/深度/透明层；需要解决延迟、姿态配对、遮挡和混合。
- 网格：客体发送几何/材质，宿主绘制；要开发宿主渲染接入，并处理增量、生命周期和资源代次。
- 逻辑：交换状态/规则结果，宿主自己显示；不能自动满足“客体真实当前帧”。
- 无独立桥：嵌入库或统一运行时，不等于两个原生游戏进程。

主源补充：[SkyCraft 协议](https://github.com/chasmlol/SkyCraft/blob/main/protocol/skycraft_protocol.h) 的 render ring 明确发送 MC 原生块网格；input ring 明确 Skyrim 生产、MC 消费，包含 press/release、鼠标、文本、release-all。这里确有适合参考的宿主前台输入方向。[Skyring schema](https://github.com/BennettCode/Skyring/blob/main/protocol/schema/messages.toml) 明确 InputState 及状态槽；本轮不外推未阅读的实现。[SekiroCraft README](https://github.com/Xu060113/SekiroCraft-Passthrough) 与 [ProtoInput README](https://github.com/Ilyaki/ProtoInput) 仅支持上述范围分类，不作为游戏实测证据。

## 3. DCCM：确认的入口与仍需实现的部分

固定源码提交：`343ee7ea8b90572e11999fd26c3efc1a9136f2de`。本机记录 DCCM 为 35.13.9；实际构建还须核对本机 MDK、缓存 GameProxy 和游戏 build 的绑定指纹。

- [ModLoader.cs](https://github.com/dead-cells-core-modding/core/blob/343ee7ea8b90572e11999fd26c3efc1a9136f2de/sources/ModCore/Modules/ModLoader.cs)：枚举 mod 目录、读取 modinfo，处理附加目录及版本信息。
- [DefaultModLoader.cs](https://github.com/dead-cells-core-modding/core/blob/343ee7ea8b90572e11999fd26c3efc1a9136f2de/sources/ModCore.ModLoader.Default/DefaultModLoader.cs)：装入程序集，查找 ModBase 主类、调用构造函数与 Initialize。
- [Game.cs](https://github.com/dead-cells-core-modding/core/blob/343ee7ea8b90572e11999fd26c3efc1a9136f2de/sources/ModCore/Modules/Game.cs)：Hero init/dispose、IOnFrameUpdate/IOnHeroUpdate、主线程同步上下文。不得从后台线程直接调用 HashLink 游戏对象，也不得在游戏线程等待 IPC。
- Hero 运动/伤害候选 Hook 为本机 ICEY-DC 已使用的 Hook_Hero.fixedUpdate、Hook__AttackUtils.hit、Hook_Hero/Entity.applyAttackResult 和武器/技能更新边界。它们来自生成绑定和客体适配代码，**不是 DCCM 自动提供的外来玩家模式**。每个旁路必须在 MC 项目重新编译/实机证明。
- 未找到一个可以直接照用的“MC worldEpoch 接口”。项目需在 Hero/Level 生命周期、地图身份、重生/重新生成与几何更新上维护自己的 session/worldEpoch/worldRevision，不能只用地图字符串或指针。

## 4. DC 联机：必须进入桥接协议的世界状态

固定提交：`7ed82513b71a0d947d628764b0b72450be3e0aa8`。

源码依据：[Protocol.Types.cs](https://github.com/vaiserYT/DeadCellsMultiplayerMod/blob/7ed82513b71a0d947d628764b0b72450be3e0aa8/server/server.NetNode.Protocol.Types.cs)、[LevelExitSync.cs](https://github.com/vaiserYT/DeadCellsMultiplayerMod/blob/7ed82513b71a0d947d628764b0b72450be3e0aa8/UI/LevelExitSync.cs)、[GameDataSync.LevelGraph.cs](https://github.com/vaiserYT/DeadCellsMultiplayerMod/blob/7ed82513b71a0d947d628764b0b72450be3e0aa8/GameDataSync/GameDataSync.LevelGraph.cs)、Mobs/MobWireCodec.cs、MonsterSynchronization 生命周期/Registry 文件。

- 玩家快照有 Id、X/Y、Dir、LevelId、RoomLevelId/RoomId、动画及头部状态；生命快照与武器另行表示。MC 协议需位置/朝向/世界身份与存活状态，不需要照搬 DC 动画名。
- 怪物快照/事件有 Generation、NetId/Index、类型、位置、速度、生命、技能或事件序号。网络 NetId 不等于 DC 原生 UID；MC 桥接应自行建立 session + worldEpoch + stableBridgeEntityId ↔ nativeUID 注册表。
- 过关提交带 Sequence、门坐标、来源 LevelId 和目标 LevelId。目的地图加载完、碰撞快照已被 MC 应用前，不得重新授予客体控制权。
- 图同步代码指出，仅 run seed 不足以复现实际地图；有图及生成后 RNG 状态。这里给 MC 的权威数据应是 DC **当前实际碰撞/可交互元数据**，不是让 MC 复制 DC 生成器。
- 状态清理由会话和代次决定；不能把结构性世界数据按墙钟 TTL 随意删掉后继续游戏。帧/输入则必须有独立的新鲜度规则。

## 5. MineCells 与内容许可

固定提交：`317eac3152b23b5332dc12c2d69a919bca21a62b`。读取 README、MineCells.java 的 ModInitializer 注册链和源文件目录。

[MineCells.java](https://github.com/mim1q/MineCells/blob/317eac3152b23b5332dc12c2d69a919bca21a62b/src/main/java/com/github/mim1q/minecells/MineCells.java) 在 MC 内注册 blocks/entities/structures/dimensions 等内容。它不运行 DC，不导出 DC 当前地形或接管 DC Hero；方向是 DC 内容→MC，不能作为本项目的桥接架构。

[README 许可](https://github.com/mim1q/MineCells/blob/317eac3152b23b5332dc12c2d69a919bca21a62b/README.md) 区分代码 MIT 与纹理/模型保留权利。只学习内容分类与代码，不复制保留权利的素材。

## 6. ICEY 历史与交付经验

延续此前 REFERENCE_STUDY.md 的两段指定历史。只读本机 ICEY 仓库提交 `1d4c4f4...` 和独立的 v1.0.12 候选；未将远端 latest 或 v1.0.12 实机状态重新标为通过。

实际可借鉴：Hero 职责分离、真实动态纹理、同帧姿态、稳定站立尺度、最新帧邮箱、原生输入边沿、断连恢复及关卡代次。不能复用 Unity Physics2D、Rewired、Unity RenderTexture 采集实现到 Java MC。

TerraKnight 只参考独立切片和“新增 / 修正 / 还做不到”交付方式。本轮不改动它或 ICEY 的仓库。

## 检索与证据限制

检索：仓库全名；文章准确标题；SekiroCraft-Passthrough / SkyCraft / Skyring / ProtoInput；DCCM mod loader、Hero、generation/level graph 和 Multiplayer protocol 字段。命名相同的存储系统 Skyring 已排除，参考目标是 BennettCode/Skyring。

4 个主要仓库以 Git 浅克隆保存在 research/upstream，仅作只读调研，不执行构建脚本、不初始化子模块。提交及阅读文件清单见 sources.json。补充项目为网页源码/README 阅读，证据等级已分开。

未核验 MC 26.3 模组开发入口或运行旁路；未实测跨语言同步原子性、透明输出、DC 三维渲染、可编辑地形、原生控制或延迟。这些均进入后续验证，不用相邻项目成果代替。
