# MC/DC 桥接契约入口

权威布局及生命周期细节见 [PROTOCOL_DRAFT.md](PROTOCOL_DRAFT.md)，实现范围见 [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)。这里不定义第二套协议。

- 世界、关卡代次、前台输入与最终显示归 DC；原生玩家模拟、姿态与后续库存归 MC。F7 改所有权，不切操作系统焦点。
- 单位和轴：DC 连续格 q=(cx+xr,cy+yr)，Y 向下；MC block，Y 向上。以脚底为锚点，比例 k 显式标定。见协议第 7 节。
- 控制：127.0.0.1 TCP，64字节信封，Wire body上限1MiB。control-1子集上限16KiB，严格schema见CONTROL_SLICE.md。MC输入接收队列已实现128条容量，满则终止并在下一输入tick清键；codec回调不是游戏队列。
- 像素：Win32 0ms三槽邮箱的旧MCDF角色层通过五项跨进程故障测试；独立MCWC完整场景诊断通过626张真实MC GPU→邮箱→DC原生Texture/HUD上传、后台推进及断流撤图。MCDF不冒充完整场景；MCWC也不作为MODE ready帧。详见 FRAME_MAILBOX_SLICE.md、LIVE_COLOR_SLICE.md。
- 版本0.1，数字little-endian，UUID为RFC4122网络顺序。Java long保存u64原始位，序号采用无符号比较。消息体u64须是规范十进制字符串。
- session/worldEpoch/modeEpoch/revision/cameraEpoch配对后才能使用帧。收到包不等于游戏线程已消费；ackSequence只能在消费提交后前移。
- 接管前必须有握手、双方几何、原生姿态、真实帧及可撤销载体旁路。失联、超时、溢出、切关、暂停/失焦均释放输入并恢复Hero。当前代码没有授予控制的路径。

已实现的InputInbox只输出原生输入安装请求和消费确认。BridgeClientInput对真实26.3类型编译/夹具通过，未自动装入LocalPlayer；完整MODE提交及Hero恢复仍是后续职责。

2026-10-20新增独立 MCDW 快照及客体 ModeGate，见 WORLD_MODE_SLICE.md。ModeGate 要求 client/server 几何回执、同帧合法空间、匹配帧及载体准备；BridgeInputBinding 保存/恢复 MC 原输入对象。后续 v0.5 已新增 world-1(capabilities=3) 协商与 WORLD/MODE 有界分发；旧 control-1(capabilities=1) 不接收世界命令。真实 DC 局部地图进入真实 MC 双侧 Level 查询、修订及代次更新已实机通过，但诊断文件入口尚未与 TCP/正式协调器整合；组件 HERO 状态不等于 DC Hero 恢复。详见 DC_RUNTIME_SLICE.md。

运行条件：Windows本地用户自己的DC与MC安装；DC使用DCCM，MC26.3使用匹配Fabric和Java25。用户授权代理控制离线实验会话。DC实验使用私有资源/存档/模组目录、独立启动保护与原生云调用阻断；MC使用标记gameDir。原本地存档/配置的晚间新基线核对变化0，历史跨会话基线差异另行保留，不覆盖用户文件；不改既有ICEY工程。
