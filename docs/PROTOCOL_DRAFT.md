# MCDN v0.1 原生双向桥接协议草案

状态：v0.1布局codec及control-1的HELLO/HELLO_ACK、INPUT、RELEASE子集已实现并测试，见CONTROL_SLICE.md。世界/MODE语义、原生映射/锁及完整游戏适配仍为草案。以下是本项目设计，不是上游已有能力。

2026-10-20最新：world-1/WORLD/MODE 独立 TCP 管线见 LAB_SLICE.md，真实 DC→MC 局部碰撞及代次更新见 DC_RUNTIME_SLICE.md；Win32 三槽映射与 JNI/PInvoke 跨进程合成帧测试见 FRAME_MAILBOX_SLICE.md。后文旧状态说明保留历史背景，正式输入、GPU 采集和 DC 显示仍未完成。

2026-10-20补充：独立MCDW几何blob和客体ModeGate已实现，布局/验收见WORLD_MODE_SLICE.md。blob尚未接入WORLD_CHUNK；现有JSON信封语义和capabilities=1未被暗中更改。完整世界/MODE网络协商与游戏端应用仍待实现。

## 目标及阶段

用户已明确最终目标：**可转动视角的三维 DC 地图，MC 第一/第三人称操作、直接创建和摧毁方块**。首个可验收切片仍是 DC 地面/墙上的原生 MC 行走、跳跃、落地、随世界移动的真实玩家帧与可靠返回 Hero。

首切片的侧视显示和受限深度用于证明原生物理/显示/所有权闭环，不是三维产品交付。后续不得把限制 Z 的侧视版标成完整三维世界。

## 1. 三个进程内外职责

| 部分 | 拥有的职责 | 禁止承担的职责 |
|---|---|---|
| DC 进程内 Mod | 世界/关卡/实体身份；真实输入入口；世界导出；Hero 载体；世界图层及最终 DC 窗口显示；必要世界事件适配 | 重写 MC 移动/攻击/受伤公式；后台线程访问 HashLink 对象 |
| MC 进程内 Mod | 客体桥接场景；原生玩家输入消费、移动/物理/动画/后续库存与战斗；原生渲染采集 | 继续让原超平坦地形影响玩家；用反复传送冒充原生碰撞 |
| 会话协调器及小型原生 IPC 库 | 版本、会话、进程身份、文件映射与跨语言锁、诊断/归档 | 操作游戏对象；伪造玩法结果；抢窗口焦点 |

MC 客户端游戏/渲染线程和集成服务器线程分别负责各自原生对象。服务器必须应用同一份桥接几何和控制代次，再执行原生玩家模拟。仅客户端表现运动、服务器仍在超平坦世界不算通过。

DCCM 候选入口：ModBase + IOnFrameUpdate，Hero init/dispose，游戏更新/原生输入 Hook；生成的运动、攻击、伤害 Hook 由本机绑定核对。游戏线程仅消费已有消息，不等待 MC/网络/互斥锁。

## 2. 会话、版本与代次

- 标识：MCDN；major=0、minor=1。草案格式仍可变，生产前冻结并生成跨语言布局/黄金样本。
- sessionId：随机 128 bit；线上字节顺序为 RFC 4122 网络顺序，不能直接使用 .NET Guid 默认混合端序数组。
- 每个进程身份为 PID + OS 创建时间 + 角色 + sessionId。PID 相同不足以接管或终止进程。
- worldEpoch：DC 负责的 u64，每次关卡切换、重新生成、重开 run、换载体/重生等影响身份的事件递增。即使 LevelId 字符串相同，也不能复用旧代次。
- worldRevision：同代次内几何/交互状态增量修订；worldEpoch 与 revision 不可合并。
- modeEpoch：每次控制权请求/撤销递增，丢弃旧输入、旧帧和旧激活回执。
- levelKey/roomKey、runSeed、生成图指纹是诊断/定位字段，不是实际碰撞快照的替代品。
- 版本握手包括实际 DC build、DCCM/MDK/绑定指纹、MC version id/JAR 摘要、loader/API、Java major、IPC 布局摘要及能力位。
- 当前窗口标题 MC 26.3 / SDL_app 仅是侦察线索。未验证对应模组工具链、原生入口与字节码，不能套用上游 1.21.1 的版本声明。版本不符只保持 Hero 并报告，不能静默降级或换 MC 版本。

## 3. 通道与背压

### 控制、输入、可靠事件

首版采用仅 127.0.0.1 的 TCP，有界增量解析；会话协调器绑定 OS 分配的空闲端口，写入本会话描述。禁止占用 ICEY 42250 或复用 EP4、ICEY 命名对象。认证为本次随机会话 nonce，不能复用历史描述文件。

socket 线程只解析字节、检查边界并入队；不把 StreamReader 缓存与 Socket.Available 混用。每条消息上限 1 MiB；几何大快照分块，有总块数、总长度及摘要。没有等待另一进程的游戏线程调用。

- 输入有序，完整 held 状态 + 独立 press/release/eventSeq；完整状态用于纠正粘键，边沿不能被快照合并吞掉。
- 队列初始上限 128 条/方向，采用显式确认的消费序号。溢出立即撤销 MC 控制、释放输入、回 Hero，不能静默丢掉按键松开或战斗事件。
- 普通连续位置状态可 latest-wins；可靠世界编辑/交接事件必须有 requestId 与幂等去重。
- 失焦、打开 DC 菜单、切 Hero、会话关闭、代次变化均触发 release-all。控制租约过期时 MC 自行释放，不依赖失联 DC 发出最后一个包。

### 动态像素

使用本会话独立、固定大小、文件映射的 3 槽**最新完整帧邮箱**；它不是视频队列。每槽最多 1024×1024 RGBA8，首测可协商较小尺寸，具体清晰度/耗时由实测决定。

一个经 JNI/PInvoke 调用的小型 Win32 IPC 库统一拥有映射文件与命名互斥；Java/C# 不直接访问共享映射。每槽独立锁，发布头独立锁，均只尝试 0ms；忙就跳过该次读/发布。转换、GPU 读回等待、统计及完整帧验证在临界区外完成，只有映射内完整复制、必要的固定头检查和元数据发布持锁。放弃发布不能推进已发布 frameId。当前单写者/单读者调用契约、64字节MCDM头及五项验证见 FRAME_MAILBOX_SLICE.md。

不得仅凭 Java VarHandle 与 C# volatile 的相似名称声称跨进程原子性成立。共享内存发布需要实际 Java/C#/原生三端压力测试；若锁开销不可接受，另立已验证的原子协议版本，不偷偷替换实现。

写者锁空闲槽、写完整头及像素并解锁，然后短锁发布索引。读者短锁取索引/预期 frameId，解锁后尝试槽锁、核对标识并复制到本地，再解锁。若槽已被重用而 frameId 不匹配则丢弃。检测 abandoned mutex 时设置共享故障位、释放已获互斥所有权并停用整个会话，必须新 session 恢复，不使用可能半写的数据。

文件、锁及目录名都包含 sessionId，例如 Local\\MCDN_<session>_FrameSlot_0。只用当前用户同等普通权限和明确访问控制，不降低两个游戏权限，不改系统安全策略。

## 4. 控制消息信封（固定 64 字节）

所有数字 little-endian，禁止直接序列化托管结构的 padding/指针。UUID 规则单独如上。

| 偏移 | 类型/字节 | 含义 |
|---:|---|---|
| 0 | bytes[4] | ASCII MCDN |
| 4 | u16 | major |
| 6 | u16 | minor |
| 8 | u16 | messageType |
| 10 | u16 | flags，未知必需位拒绝 |
| 12 | u32 | bodyBytes，先检查长度再分配 |
| 16 | bytes[16] | sessionId |
| 32 | u64 | worldEpoch |
| 40 | u64 | modeEpoch |
| 48 | u64 | sequence，每发送方单调 |
| 56 | u64 | ackSequence，仅确认已消费的消息 |

v0.1 消息体草案采用 UTF-8 JSON，数组/字符串上限单独验证，禁止 NaN/Infinity、重复键、未知必需字段；高频二进制压缩暂不作为首测依赖。64 字节信封是真正 TCP framing，不能用换行拆 JSON 或用一次 Read 当一条消息。

JSON 消息体中的 u64/i64 标识、代次、计数和时钟使用规范十进制字符串，禁止经 double 中转而损失超过 2^53 的整数。二进制信封/帧头仍使用精确整数；解析时检查符号、范围及规范形式。

## 5. 消息语义

codec固定type编号：HELLO=1、HELLO_ACK=2、HEARTBEAT=3、WORLD_BEGIN=4、WORLD_CHUNK=5、WORLD_END=6、WORLD_PATCH=7、WORLD_APPLIED=8、MODE_PREPARE=9、READY=10、COMMIT=11、RELEASE=12、INPUT=13、PLAYER_STATE=14、FRAME_PUBLISHED=15、TRANSITION_BEGIN=16、WORLD_READY=17、ERROR=18、SHUTDOWN=19。20–22为未来BLOCK_EDIT/ENTITY/COMBAT保留；仅识别编号不表示能力已协商，语义层须在能力关闭时拒绝。0、23及以上拒绝，flags当前只接受0。

Wire层body仍是不透明字节；新增Control层对HELLO/ACK、INPUT、RELEASE应用control-1严格平面ASCII字符串JSON schema，拒绝重复键/未知字段、非规范整数并验证nonce/构建绑定，见CONTROL_SLICE.md。其它消息body未实现schema。原诊断echo不进行所有权交接；认证通过也不能跳过世界/MODE准备和真实帧条件。

| 类型 | 方向 | 必需信息 / 消费线程 |
|---|---|---|
| HELLO / HELLO_ACK | 双向 | build/布局/角色/进程身份/capabilities/时钟频率；连接阶段，尚不接管玩家 |
| HEARTBEAT | 双向 | control/render/server tick 的独立活跃计数；区别暂停、渲染慢和进程断连 |
| WORLD_BEGIN | DC→MC | 代次、真实地图身份、脚底锚点、单位、深度策略、初始形状摘要 |
| WORLD_CHUNK / WORLD_END | DC→MC | chunk/segment AABB、solid/one-way/door/protected 标签、版本、校验；集成服务器和客户端确认同一版本 |
| WORLD_PATCH / WORLD_APPLIED | DC↔MC | baseRevision、newRevision、形状增删、应用 tick；缺失基线不得继续移动 |
| MODE_PREPARE / READY / COMMIT / RELEASE | 双向 | modeEpoch、目标所有权、几何版本、输入释放确认、当前站立与脚底姿态；游戏线程 |
| INPUT | DC→MC | inputSeq、hostTick、held 位、边沿序列、移动轴、鼠标相对量/按钮；MC 原生客户端入口并经正常玩家输入链到集成服务器 |
| PLAYER_STATE | MC→DC | serverTick、consumedInputSeq、position/velocity/yaw/pitch、onGround/pose、碰撞版本、原生生命/状态；只在版本配对时更新载体 |
| FRAME_PUBLISHED | MC→DC | 最新帧提醒；帧本体仍以邮箱完整快照为准；不保证每个通知都显示 |
| TRANSITION_BEGIN / WORLD_READY | DC↔MC | 来源/目的 levelKey、门/过渡序号、新 worldEpoch；旧帧立即失效 |
| ERROR / SHUTDOWN | 双向 | 可复现原因、错误阶段、恢复结果；释放输入与资源，不关闭玩家自己启动的游戏 |

BLOCK_EDIT 与 ENTITY/COMBAT 先保留能力位和后续版本范围，**首个切片不启用**。消息出现但能力未协商时拒绝，不能“成功 ACK”一个没有实际效果的操作。

## 6. 帧槽头（256 字节）

| 偏移 | 类型 | 含义 |
|---:|---|---|
| 0 | bytes[4] | MCDF |
| 4 / 6 | u16 / u16 | major / minor |
| 8 / 12 | u32 / u32 | headerBytes=256 / pixelBytes |
| 16 | bytes[16] | sessionId |
| 32 / 40 / 48 | u64 ×3 | worldEpoch / modeEpoch / worldRevision |
| 56 / 64 / 72 | u64 ×3 | frameId / nativeTick / consumedInputSeq |
| 80 / 84 / 88 / 92 | u32 ×4 | width / height / strideBytes / pixelFormat |
| 96 | u32 | layerFlags：player/effects，后续 HUD/world 分层协商 |
| 100 / 104 / 108 | u32 ×3 | bottomUp / premultipliedAlpha / reserved |
| 112 / 120 / 128 | f64 ×3 | **捕获该帧时**玩家脚底 MC xyz |
| 136 / 144 / 152 | f64 ×3 | 同帧速度 xyz |
| 160 / 164 | f32 ×2 | 同帧 yaw / pitch |
| 168 / 172 | f32 ×2 | 输出脚底 pivot uv |
| 176 / 184 | f64 ×2 | 稳定站立高度（MC block）/ 采集范围世界宽度 |
| 192 / 200 / 208 / 216 | u64 ×4 | inputSourceQpc / consumedQpc / physicsCommitQpc / frameReadyQpc |
| 224 | u64 | QPC frequency |
| 232 | u32 | pose/grounded flags |
| 236 | u32 | 像素 CRC32，诊断一致性，不替代同步 |
| 240 | u64 | cameraEpoch，后续旋转/透视切换用于防混帧 |
| 248 | u64 | reserved=0 |

校验 width/height 非零且不超协商上限、stride=width×4、pixelBytes=stride×height，不允许整数溢出或越界。格式初始为 RGBA8，默认 top-down、straight-alpha；若协商其它格式/预乘，DC 混合状态必须成对验证。

当前codec最大边长1024；pixelFormat=1为RGBA8，layerFlags位0=player、位1=effects（至少一位，拒绝其它位）；bottomUp/premultipliedAlpha只接受0/1。保留字段为0，QPC frequency非零，空间/角度有限，稳定高度/采集宽度正值，pivot uv在[0,1]。CRC32采用IEEE/zlib口径。pose/grounded flags位分配仍待原生入口绑定。

异步 PBO 读回必须把姿态/tick/输入序号和 GPU 采集一同快照，不能读回完成时才读取最新玩家姿态。DC 纹理上传完成后，在同一主线程更新载体、帧位置和 visible 状态；旧代次、旧相机代次或错误 revision 帧丢弃。

相机三维阶段另加明确 WORLD_COLOR / WORLD_DEPTH / HUD 通道能力、分辨率及 view/projection/inverse 矩阵结构；上述角色槽不冒充完整透视场景协议。

已实现但尚未接入正式能力协商的独立MCWC0.1完整场景**诊断**帧布局见[LIVE_COLOR_SLICE.md](LIVE_COLOR_SLICE.md)。它使用有类型的MCDM0.2映射入口，626张真实GPU帧已到达DC原生纹理；没有WORLD_DEPTH、逆矩阵/重投影、DC世界/控制上下文配对或MODE ready权限。MCDF布局/角色标志保持原意。

## 7. 坐标与三维语义

定义 DC 连续格位置 q=(cx+xr, cy+yr)。qY 向下。MC xyz 以 block 为单位，Y 向上。锚点是脚底，不是贴图中心。

```text
MC.x = mcAnchor.x + k * (q.x - dcAnchor.x)
MC.y = mcAnchor.y - k * (q.y - dcAnchor.y)
MC.z = mcAnchor.z + depth
DC.qx = dcAnchor.x + (MC.x - mcAnchor.x) / k
DC.qy = dcAnchor.y - (MC.y - mcAnchor.y) / k
DC pixel = q * 24  // 仅本机 DC 绑定的世界单位，版本校验后采用
```

k（每 DC 格的 MC block 数）、固定站立比例和镜头参数独立标定。不用动态蹲伏/游泳/碰撞高度重算视觉比例。

- 首闭环：DC 形状精确转换成挤出 AABB/shape，前后边界由 MC 原生碰撞解决，形成测试运动平面；不靠每 tick setPos 固定 Z。客户端和服务器都必须看到同一形状。
- 非整 block 边界不能直接四舍五入成实心方块。须验证原生 MC collision query 中组合 VoxelShape 或自定义桥接块 shape 的可用入口，保持原生 move/碰撞解算。
- 三维产品：墙、地板、平台须有厚度/深度、房间之间的门洞连通、楼层净空与完整可达性。MC 可转动第一/第三人称相机；玩家深度需真正受世界限制。
- DC 原生二维 AI/命中/交互不能读懂 MC.z。三维世界层必须为实体/门/陷阱定义深度范围，并在原生事件发生前验证三维接触/可达性。未来深度移动、目标代理及必要路径适配仍未解决；不得仅忽略 Z 投影位置就宣称三维世界能正确交战。
- 角色、世界与相机的变换分开；viewport/缩放/DPI 不得进入物理单位换算。

## 8. 所有权与恢复

```text
HERO -> PREPARING_MC -> MC_ACTIVE -> RETURNING_HERO -> HERO
            |               |
            +--失败---------+--断连/版本/过渡故障--> RECOVERING -> HERO
```

进入 MC_ACTIVE 前：两个端点握手、桥接场景隔离、两侧几何已应用、空间有效、首个匹配代次的原生姿态/真实帧可用、载体职责已安装并可撤销。仅连接成功不能隐藏 Hero。

F7 请求换 owner，不换焦点。MC_ACTIVE 时仅 MC 拥有玩家自主运动/攻击/伤害；DC 保留载体身份、相机、世界检测和允许的交互。原生 Hero 自主动作不得再叠加执行。

保存并恢复：重力开关/权重/碰撞模式、controller 锁、可见性/alpha/围巾层、实体接触检查、被替换的玩家更新/技能 Hook 和渲染资源。HP 不恢复成进入 MC 前的旧值，避免回切刷血；同步到经确认的客体当前生命。

正常回切先撤销客体输入，取得最后一致的脚底/速度；恢复物理后以此重建 Hero 运动。紧急回切可明确采用安全的零速度策略并记录，不能恢复数秒前的旧冲量。找不到合法位置时使用本关真实安全锚点，并记录恢复失败/位移，不能静默穿墙或漂浮。

控制租约目标初值 250ms，心跳超时目标初值 1s，均为待实测参数，不是延迟承诺。MC 自行在租约过期时释放按键；DC 在主线程检测帧/服务器心跳不新鲜时撤销客体模式。断连不可保留永久无敌载体。

切关/关卡卸载：先递增 worldEpoch、撤销输入和呈现；丢弃旧实体注册及未提交请求；新世界快照和对端应用确认后才允许重新进入 MC。重连不能沿用旧队列。

## 9. 方块编辑的后续权威（首切片关闭）

MC 放置/挖掘以原生玩家操作、射线、挖掘进度及集成服务器规则为入口，不在 DC 重写为“点击就删格”。

- DC 基础几何：DC 权威，明确 sourceCell/shapeId、材质与可编辑标签。MC 不能先删自己的镜像再假装 DC 地形已修改。
- MC 新放方块：MC 集成服务器权威，DC 接收已提交的 block state/shape/版本用于显示及世界碰撞适配。
- 涉及 DC 原墙体的编辑：requestId + 预期 worldRevision + 原生操作证据；DC 验证保护区、门/机关和拓扑，原子应用真实世界修改，再返回实际结果/新 revision。MC 在确认后完成原生物品扣除/掉落；拒绝、断连与重试必须有可回滚/去重事务。
- DC 地图碰撞、显示、导航/缓存如何一起更新尚未验证。若无法做到，报告这一验收项未满足，不把仅删除 MC 显示块称作“摧毁 DC 墙体”。

## 10. 计时与清理

两端通过原生 IPC 库取同一 Windows QPC/frequency；不直接减 Java nanoTime 与 .NET Stopwatch 的任意基点。记录输入、消费、原生物理提交、帧 ready、DC 上传/绘制及 present 返回。软件 present 不是显示器光子延迟；不同物理 tick 与渲染帧率单独报告。

协调器只归档/结束自身创建、manifest 身份匹配的 helper；不按进程名杀游戏，不抢 ICEY 端口，不覆盖旧会话证据。玩家自己启动的两游戏只解除桥接，不关闭。
