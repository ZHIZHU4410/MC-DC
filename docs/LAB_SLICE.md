# v0.5：WORLD/MODE 通信和实机诊断入口

2026-10-20，当前仍在接入验证中。最终目标保持：DC 前台输入、世界与最终显示，后台 MC 原生玩家与三维模拟/渲染；可转动第一/第三人称。探针既不接管输入，也不把测试帧当成实机画面。

后续实际 DC 地形→MC 双侧查询已通过，当前状态和隔离启动修复见 [DC_RUNTIME_SLICE.md](DC_RUNTIME_SLICE.md)。本文后面的“待执行/尚未安装”为准备阶段记录，不能覆盖后续实机证据。

## 已通过的验证

- `tools/verify_pipeline.py` 包含前三片回归。真实 C#↔Java TCP 完成 world-1 握手、分块、双侧应用回执、PREPARE/READY/COMMIT、消费 ACK、释放和 EOF。
- reader、writer、游戏消费者分属不同线程；每个队列及未消费回执最多 128 条，满则终止。ACK 只推进连续已消费/取消前缀，不能跳过待执行输入。
- 额外异常测试检查 ACK 空洞/越界/倒退、未协商世界能力、旧世界取消、跨 tick 短按边沿、失焦优先释放、畸形流清键和游戏线程所有权。
- DC 探针对本机 DCCM 35.13.9 / GameProxy 构建通过；Fabric 探针对本机 MC 26.3 / Loader 0.20.0 / JDK 25 构建通过。构建成功不等于 Hook 已在游戏里生效。

通信报告：`artifacts/pipeline/report.json`。构建与来源摘要：`artifacts/lab/build-report.json`。通信实验的几何/帧/载体/输入 sink 是合成数据。

## 离线主菜单加载检查

用户已自行通过启动器离线启动，首次在初始化时崩溃，根因是入口/辅助类放入了 Mixin 保留包。修复将注入类移到独立 `dev.mcdn.fabric.mixin`，并用真实 Knot/Mixin 验证入口实例化及两个 handler 合并。随后用户重试成功并报告停在主菜单，10:31:42 初始化/来源/两个注入点和 10:31:44 实际 Render thread tick 标记均已核验，`MC_LOAD_PASS`。

探针唯一安装文件：

`D:\MC\愚者\懒人包\.minecraft\versions\26.3-Fabric 0.20.0\mods\mcdn-lab-probe-0.5.0.jar`

安装记录 `artifacts/lab/mc-install.json` 含包哈希及同名旧包备份（如有）。首次安装 previous=null；修复覆盖时会备份出错包。没有修改启动器、其它模组或存档；没有设置隔离实验 JVM 属性，默认只输出诊断日志。

`tools/verify_fabric_package.py` 在构建和安装时拒绝 Mixin 保留包中的普通类；独立干净编译目录避免改包后的旧 class 残留。`tools/verify_fabric_transform.py` 对本机 26.3/0.20.0/Java25 执行真实类转换检查，报告在 `artifacts/fabric-transform/report.json`，包含被测包摘要。原错误包被保留包检查明确拒绝，修复包检查及实际转换通过。

用户离线启动至主菜单后执行：

```powershell
python tools/check_mc_load.py
```

只有日志晚于安装且同时满足下列条件才报告 `MC_LOAD_PASS`：

1. 已安装文件 SHA256 与安装记录一致，加载来源路径精确指向该文件。
2. `MCDN_LOAD_CHECK collisionMixin=true tickMixin=true`。
3. 实际 `MCDN_CLIENT_TICK_OBSERVED` 标记出现。

结果写 `artifacts/lab/mc-load-report.json`；只保留自己的三个标记，不复制启动器日志。它证明客户端启动及注入入口，不能证明主菜单视觉正常、世界碰撞、原生行走或离线网络状态。离线状态由用户声明；不读取账号凭据。

## 独立实验实例（已安装，世界验证待执行）

已在同一启动器目录新增 `MC-DC-Lab-26.3`，游戏目录为：

`D:\MC\.minecraft\versions\MC-DC-Lab-26.3`

用户随后反馈误删，检查确认原整合包根目录及实验版本均不在原路径。已使用项目保留的版本元数据、验证过的探针和 Mojang 固定下载重建到上面的当前路径；游戏 JAR 的大小/SHA1/SHA256 与原记录一致。`tools/restore_mc_lab_profile.py` 及 `artifacts/lab/mc-profile-restore-plan.json` 记录恢复方式。当前为空实验实例，先前实验世界未恢复；缺失的公共 libraries/assets 由 PCL 首次启动补全。用户此前报告进入过实验世界，但未取得其世界运行证据前目录已被删除，因此不计为世界/物理验收。

使用用户本机同一游戏 JAR 和已验证探针，设置独立 gameDir、标记文件与 manifest；没有复制原存档或账号，也没有覆盖原版本。安装记录为 `artifacts/lab/mc-profile-install.json`，包含创建文件哈希。脚本拒绝合并到已存在目录。启动器参数处理参照 [PCL ModLaunch 源码](https://github.com/Meloong-Git/PCL/blob/main/Plain%20Craft%20Launcher%202/Modules/Minecraft/ModLaunch.vb)，版本隔离键沿用本机实际实例的 `VersionArgumentIndieV2:True`；隔离运行路径还会由探针二次核验。

已用本机 Fabric 对实验实例配置做初始化预检，`labConfigured=true`、两个 handler 合并通过；不运行游戏 main/构造器、tick 或世界。实际启动仍需用户在启动器刷新版本列表后自行选择该实例离线启动，并新建 `MCDN-Lab` 创造模式单人世界（可用超平坦）。不打开现有世界。

```powershell
python tools/check_mc_load.py --profile
```

实验实例的输出报告为 `artifacts/lab/mc-profile-load-report.json`，与首次主菜单证据分开。只读日志支持严格 UTF-8/GB18030 解码；本机启动器日志使用 GBK，不用替换坏字节的方式模糊匹配中文加载路径。

下面是工作区模板的原始构建说明；实际已安装实验实例以 `mc-profile-install.json` 及其 `mcdn-lab.json` 为准。

`tools/build_lab.py` 生成独立目录 `artifacts/lab/minecraft`，其中有 `MCDN_ISOLATED_LAB` 标记和自己的探针包。`artifacts/lab/launch-spec.json` 给出实际 gameDir、Java、assets、libraries 和 JVM 参数：

`-Dmcdn.lab.manifest=<项目绝对路径>\artifacts\lab\fabric-lab.json`

用户仍通过正常启动器/账号自行离线启动，使用这个独立 gameDir，新建一次性单人世界；不能把现有 `新的世界` 当实验存档。构建脚本不创建账号或令牌，不自动启动游戏。需要配置独立实例时先备份启动器设置，再做可恢复变更。

DC 探针包在 `artifacts/lab/packages/McdnDcProbe`，尚未安装。设置该 DC 子进程的 `MCDN_LAB_ROOT=<项目绝对路径>\artifacts\lab` 后，探针才开始只读捕获；主线程只复制局部碰撞格网，后台写不可变 `.mcdw` 和最后发布的 `latest.json`。Hero 生命周期、地图 UID 和碰撞指针变化使世界分代。

Fabric 文件线程只读/解析值，client tick 和集成服务器各在所属线程安装原生形状。仅独立 gameDir、标记文件及 saves 路径核对通过才允许安装诊断层；普通实例保持原查询。

当前只导出局部 64×48、Plain=3 / Invisible=35。其它非空类型计入 unsupported，元数据 `eligibleForControl=false`。MC 观察记录也固定 `physicsIsolationComplete=false`。这里只替换部分实体块碰撞，尚未隔离流体、其它块状态、世界边界等完整物理；不能据此允许接管。

## 尚需完成

主菜单加载已实机证明。下一步实际 DC 地图导出与两侧真实碰撞调用；随后补完整地形语义与隔离、原生姿态证据、DC Hero 旁路/恢复、真实帧采集/邮箱及 DC 内显示。GuestSession 网络管线与 Fabric 文件诊断仍是独立入口，尚未连成正式传输适配。
