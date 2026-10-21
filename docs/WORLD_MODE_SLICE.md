# v0.4.0-world：几何快照与接管门控

日期：2026-10-20，Asia/Shanghai。目标仍是可转动第一/第三人称的三维DC世界与MC原生玩家。本片已完成跨语言几何数据、客体就绪门控和真实MC类型夹具，尚未安装模组或接入真实关卡。

## 实现与验证范围

| 代码 | 本片结果 |
|---|---|
| src/dotnet/Mcdn.Protocol/World.cs | 不可变完整快照、精确编码/解码、DC格坐标到MC AABB的Y翻转与小数变换 |
| src/java/dev/mcdn/protocol/World.java | 相同字节布局、摘要与形状校验、有界有序分块接收；完整校验前不暴露世界 |
| src/java/dev/mcdn/protocol/ModeGate.java | 几何/帧/合法空间/载体准备门控，精确提交、幂等提交、撤销、超时和恢复重试 |
| src/minecraft/java/dev/mcdn/minecraft/BridgeGeometry.java | 本机MC的AABB→VoxelShape；原生形状碰撞及身体空间检查的接入层 |
| src/minecraft/java/dev/mcdn/minecraft/BridgeInputBinding.java | 保存/恢复原ClientInput对象；清键、安装部分失败回滚、恢复失败保留重试，避免覆盖其它所有者 |

Python独立struct生成23组完整/损坏几何样本；C#逐个解码、重编码并导出，Java另读取这份C#导出文件，因此Java检查24份。损坏形状样本重新计算正确摘要，确保语义拒绝并非仅依赖哈希。测试覆盖尺寸/计数、版本、保留位、重复/零ID、NaN、越界、颠倒/零体积、未支持标志、哈希、截断和尾随数据。

原有39组Wire样本、256条TCP逐字节往返、50组control样本、10000次SPSC、错误nonce正常拒绝及断连清键也已回归通过。错误测试仍受main异常捕获保护，不用未捕获异常作为通过条件。

本机JDK25对真实26.3 JAR编译通过；两个测试线程各自创建原生形状层，得到相同版本/摘要和相同解算结果。它们模拟client/server职责，**没有创建或运行真实客户端世界、集成服务器、Entity.move或游戏tick**。

原生Shapes.collide夹具结果（MC block）：

| 场景 | 结果 |
|---|---:|
| 向x=2.25的小数墙移动3，身体右边界0.85 | 实际允许1.4 |
| 脚底高1向下移动3，地板顶0 | 实际允许-1 |
| 前后深度边界，身体z为±0.3 | 实际允许±0.95 |
| 身体顶1.8，天花板底3.75 | 实际允许1.95 |

原生形状相交检查确认测试站立身体空间可用，移入墙内的身体空间不可用。原生输入绑定夹具在门控允许后替换真实ClientInput类型对象，应用输入；断连清键、恢复setter失败后的重试、以及setter安装后抛错的回滚均通过，并恢复**原对象引用**。

这些结果证明几何精度与原生形状算法、输入对象交接组件可工作；不证明真实MC玩家已在DC地形上运动。

## MCDW几何blob

这是新的独立快照blob，尚未接入WORLD_*消息分发。现有control-1握手仍只允许capabilities=1；**没有**把二进制blob直接塞入原定JSON body或悄悄打开世界能力。后续须定义并协商WORLD_BEGIN/CHUNK/END/APPLIED的消息schema和分发。

所有整数/浮点little-endian，session UUID仍为RFC4122网络字节顺序。头96字节：

| 偏移 | 类型 | 含义 |
|---:|---|---|
| 0 | bytes[4] | MCDW |
| 4 / 6 | u16 / u16 | 0 / 1 |
| 8 / 12 | u32 / u32 | headerBytes=96 / shapeCount |
| 16 | bytes[16] | session |
| 32 / 40 | u64 / u64 | worldEpoch / worldRevision，均非零 |
| 48 / 52 | u32 / u32 | recordBytes=64 / reserved=0 |
| 56 | bytes[32] | 形状记录区SHA256 |
| 88 | u64 | reserved=0 |

每条记录64字节：u64 shapeId，六个f64的minXYZ/maxXYZ，u32 flags=1（solid），u32 reserved=0。最多4096条，完整blob最多262240字节；坐标有限且绝对值≤1000000，三个维度严格有正体积，ID非零且唯一。形状列表及字节对外只读或复制。完整blob的SHA256作为Stamp.digest，因而session/epoch/revision变化也改变身份。

首版只支持solid。one-way、门、保护区、材质和sourceCell语义尚未编码，未知标志明确拒绝；不能把DC单向平台偷偷当实心墙。DC真实地形导出器尚未实现，当前场景由测试数据生成。

Transfer在分配前校验总大小；每块1..1024字节，块序号严格从0连续，拒绝重复、乱序和越界。finish只允许一次，要求总长度完整、内部摘要及预期完整Stamp一致。失败对象不可恢复，重试须创建新transfer。它不等待另一线程、不在游戏线程收网络，也不代表已经完成可靠网络重传/流控。

## 客体模式门控

ModeGate仅由创建它的游戏线程使用，socket worker不能调用其方法或修改游戏对象。客户端/服务端实际适配应先在各自所属线程完成几何应用，再把不可变Stamp和空间检查证据送到客体游戏线程。

```text
HERO -> PREPARING -> READY -> ACTIVE
  ^         |          |        |
  +---------+----------+--------+  撤销/失联/超时/输入故障/世界更新
RECOVERING <--- 输入对象恢复失败；保留绑定，重试成功后回HERO
```

这里HERO是“客体输入绑定已解除”的控制状态名；它**不证明DC Hero的重力、可见性、攻击、伤害或相机已恢复**。这些仍由后续DCCM适配实现。

提交条件同时包括：

1. 当前快照session、epoch、revision、完整digest一致；client和server两份应用回执均匹配。
2. modeEpoch严格无符号递增；cameraEpoch非零。
3. frame匹配session/world/mode/revision/camera，frameId/nativeTick非零；QPC frequency正确，帧不来自未来、年龄小于1秒。
4. client和server对**同一frameId/nativeTick**确认实际姿态身体空间可用；缺一方或空间受阻均不可提交。换帧使两份空间确认失效。
5. 同mode的DC载体准备确认已收到。
6. 提交再次精确匹配Stamp/mode/camera/frameId，输入绑定属于同session/world/mode且尚未故障。

从prepare开始1秒未完成即撤销；当前参数是组件测试基线，尚未测量实际游戏加载耗时。合法的重复commit不会重复安装输入。错误/旧commit不能安装输入。新世界必须epoch递增，或同epoch revision递增；旧世界/同revision回滚拒绝。stage新快照会先解除旧输入绑定、作废全部旧几何/帧/空间准备；恢复未完成则阻止换世界或新接管。

输入租约故障由游戏线程tick观察后撤销；revoke先清除客体按键再恢复原ClientInput。恢复失败进入RECOVERING，保留原引用和绑定，下一次重试成功才回HERO；不能报告恢复成功后丢掉原对象。ModeGate本身不维护世界网络队列，不轮询socket，也不操作DC Hero。

本片Frame来自合成RGBA/元数据夹具；GPU真实帧及原生服务端状态仍未产生。未来真实适配必须提供上述证据，不能将测试的carrier确认或空间确认硬编码为true。

## 复现与下一接入点

```powershell
python tools/verify_world.py
```

该命令包含前两片回归。报告在`artifacts/world/report.json`，包含源码与样本SHA256。

真实MC类型夹具：

```powershell
python tools/inspect_mc_api.py --java-home 'C:\Users\10113\AppData\Roaming\.minecraft\runtime\java-runtime-epsilon' --mc-version-dir 'D:\MC\愚者\懒人包\.minecraft\versions\26.3-Fabric 0.20.0' --private-output 'C:\Users\10113\.codex\visualizations\2026\10\19\01a15486-778e-7dd0-8a87-d08d07c93159\mc26-private-bytecode' --world-fixture-root artifacts\world\vectors
```

结果在`artifacts/mc-api/report.json`。沿用只读放行方式解决Java25读取自身安全配置真实路径的沙箱限制，不修改安全文件、不关闭签名校验。

下一片须把组件接进真实入口：WORLD/MODE消息协商与主线程分发、DC实际几何导出、MC专用隔离世界及client/server查询替换、真实玩家姿态证据、DCCM载体准备/撤销；随后接真实帧邮箱。仅Shapes层存在不等于原超平坦已隔离，恢复ClientInput也不等于恢复DC Hero。三维显示、挖放、库存、战斗和真实游戏验收仍未完成。
