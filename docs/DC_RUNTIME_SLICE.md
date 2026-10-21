# v0.5 实机诊断：DC 地图进入 MC 双侧碰撞查询

2026-10-20，Windows 用户离线实验。已证明真实 DC 局部地图快照在真实 MC 客户端及集成服务器注册并被查询；尚未证明原生输入接管、完整地形物理、DC Hero 恢复或实际画面合成。

## 已取得的实机证据

- 用户自行启动离线 `MC-DC-Lab-26.3` 并进入 `MCDN-Lab`。探针来源和包哈希匹配，CollisionGetter/Minecraft 两个注入点及实际 Render thread tick 通过。观察数据持续刷新，非暂停，实验 gameDir 生效。
- 先用明确标记的合成地板/墙检查真实调用链：两侧接受同一 digest，两个计数从零增长。仅作为入口诊断，报告 `artifacts/lab/mc-native-query-report.json`，不能当 DC 地图证据。
- 随后独立 DC 实验进程捕获实际局部 64×48 碰撞格网；首份实机快照 MapUid=582910、epoch=3、revision=1，包含 2555 个实体形状和 7 个未支持格子（原始编码 1、33、11）。没有把未支持格子当实体墙。
- MC 客户端和集成服务器都接受完整摘要 `1997970bace29dec5314730923c9c8d37ec653ae043672129cd9872119c686ae`，查询计数为正。Java 在真实 Level 所属线程构造形状；服务器保存路径核验通过后才注册。报告 `artifacts/lab/dc-mc-native-query-report.json`。
- 原本地 DC 存档及配置对照启动前快照，修改/新增均为零。不能据此声称单独核验了 Steam 云端数据。

DC 捕获锚点为连续格 `(56.5,80)`，对应本次静止 MC 玩家 `(0.5,-60,-1.5)`。坐标轴翻转与小数保留，深度为 MC 锚点前后各 2 格；只用于当前局部诊断，并非最终三维世界范围。

所有导出及 MC 观察仍固定 `eligibleForControl=false`；MC 观察还固定 `physicsIsolationComplete=false`。站立标志可能变化，不以此单独声称碰撞运动正确。读取形状的计数不能替代原生走跳、服务端姿态配对或完整物理验收。

## DC 隔离启动

入口为项目根目录 `Start-DC-Lab.cmd`。它调用 `tools/start_dc_lab.py --launch`，仅使用 `artifacts/lab/dc-launch-spec.json` 指定的私有资源、模组、插件、缓存、数据、配置和存档目录。

`tools/prepare_dc_lab.py` 先备份原 `save` 和 `coremod/config`，再复制用户本机资源到 `artifacts/lab/dc-game`；不使用会写穿原目录的链接。只复制原装 DCCM 默认模组加载器，不加载用户其它模组。私有配置显式使用合法安装的 Steam 库，关闭 Goldberg；不更换认证组件。

编译引用遵循 DCCM MDK 的 CoreLib 引用重定向方式，输出单独的编译用 GameProxy 副本，修复运行时生成绑定与 SDK 引用类型的差异。实际游戏仍加载原样复制的本机 GameProxy；原运行时 DLL 保持不变。编译引用、游戏 DLL、资源、缓存均不打入模组包。记录在 `artifacts/lab/dc-build-report.json`。

初次 DC 实验遗漏默认加载器，日志报 Unknown mod type，探针与保护没有运行。已按记录的 PID/启动时间停止该实验进程，原本地存档/配置核对零变化；未将这次进入游戏当作成功。完整性记录 `artifacts/lab/dc-first-start-integrity.json`。

修复后增加独立于模组发现的 `LabStartup`：

1. DCCMShell 在核心启动前显式装入自己的包，并调用自定义入口，提前注册检查。
2. 原始 Boot.main 之前，核对独立目录/标记；禁止云存档使能及读写删除、禁止本地/云互传；所有原生本地存档入口固定绝对实验路径。
3. 调用游戏原生存档接口，实际完成唯一临时文件的写入、存在检查、读取和删除，再记录 `MCDN_DC_LAB_GUARD_READY`。
4. 在全部普通模组初始化之后，确认必须的探针确实完成初始化；否则正常退出码 2，禁止继续原始游戏入口。DCCM 的 OnAfterBroadcastEvent 每个接收者调用一次，不能将它当整个广播结束；这里使用事先注册的最高优先值接收者最后检查。
5. 正常实验会话才记录 `MCDN_DC_ORIGINAL_ENTRY_RELEASED`。自动预检在这个边界之前退出，不进入游戏场景。

正常原生预检及“故意缺失默认加载器”的原生拒绝测试均通过。后者不删除实际插件，只为该测试子进程指定空目录。报告 `artifacts/lab/dc-native-preflight-report.json` 和 `dc-negative-preflight-report.json` 分别保留，绑定同一启动配置和包哈希；启动器要求两份一致的通过记录。

## 复现与检查

```powershell
python tools/build_lab.py --dc-only
python tools/prepare_dc_lab.py
python tools/start_dc_lab.py --preflight
python tools/start_dc_lab.py --preflight --missing-loader-check
```

仅在离线环境中由用户运行入口。不要在 DC 实验进程活跃时重做准备。进入角色场景后：

```powershell
python tools/check_dc_lab.py
```

检查器只接受当前 DC 会话的真实导出，验证 blob/header/metadata/摘要、MC 双侧匹配回执和查询计数，并比较原本地存档/配置。仅启动预检日志或旧会话数据不能通过。

`tools/record_world_lifecycle.py` 以有界观察记录世界修订及代次更新，不发送任何游戏输入；它会先备份当前实验存档。其结果以 `artifacts/lab/world-lifecycle-runtime-report.json` 为准，不从用户操作描述推断通过。

本次实机记录已通过：同 epoch 的 revision 从 1 到 7，以及重开后的 epoch 从 3 到 7、MapUid 改变，都取得 MC 客户端/服务器相同 digest 和正查询计数。证据同时保存当时最新源快照与实际已应用源快照，避免将尚在应用中的下一修订误配给原生回执。首份 2555 形状证据另存 `dc-mc-native-query-baseline-report.json`；当前检查报告可随新地图更新，重开后一次为 2515 形状、仍有 7 格未支持，原本地存档/配置仍无变化。

## 后续缺口

当前文件诊断入口与 GuestSession TCP 管线尚未合成正式协调器；只覆盖 Plain/Invisible 的局部实体形状，没有完整 one-way/roll/ladder/slope、流体及其它原生块状态隔离。尚无 DC 前台输入到 MC 原生输入绑定、双侧原生姿态空间证据、DC 可撤销载体、GPU 真帧/IPC 邮箱和 DC 内三维显示。两个游戏画面分别出现不算最终显示闭环。
