# control-1：握手与输入故障释放切片

日期：2026-10-19（Asia/Shanghai）。这是一段已测试的控制基础，以及对真实MC类型的输入适配夹具。没有安装模组、自动接管Hero或运行游戏。

后续进展见[WORLD_MODE_SLICE.md](WORLD_MODE_SLICE.md)：2026-10-20新增独立几何blob、客体接管门控及原生形状/输入交接夹具；本页保留上一切片记录。

## 本机入口与原生类型证据

已定位可用JDK：`C:/Users/10113/AppData/Roaming/.minecraft/runtime/java-runtime-epsilon`，Microsoft OpenJDK/Javac 25.0.1。它来自启动器日志所列路径，已实际执行版本查询和编译；不等于证明当前游戏进程使用它。

本机MC26.3游戏JAR保持上次SHA256 `4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d`。以JDK25 javap读取实际字节码，定位：

| 位置 | 本机静态证据及意义 |
|---|---|
| LocalPlayer.input | 字段类型ClientInput，可保存原对象并在模式结束恢复；本次未安装替换 |
| LocalPlayer.aiStep | 调用ClientInput.tick；输入接入点在原生玩家更新链内 |
| KeyboardInput.tick | 构造七个布尔字段的Input，计算Vec2并normalized；当前适配类采用同样的输入表达 |
| LocalPlayer.applyInput | 读取ClientInput.getMoveVector和keyPresses，供后续原生移动使用 |
| LocalPlayer.sendChanges | 对原生Input变化发送ServerboundPlayerInputPacket，并另行sendPosition |
| ServerGamePacketListenerImpl.handlePlayerInput | 调用ServerPlayer.setLastClientInput；收到输入不等于服务端移动已提交 |
| handleMovePlayer / handlePlayerPositionChange | 位置包另经服务端位置处理/校验；必须进一步验证其实际移动与碰撞结果 |
| Entity.move / collide / collideBoundingBox | 进入原生碰撞解算；不能以反复setPos替代 |
| Entity.collectCollidersIgnoringWorldBorder | 收集Level块碰撞及边界形状；碰撞查询不只一个入口 |
| CollisionGetter.getBlockCollisionsFromContext / getPreMoveCollisions | 真实形状查询候选；三维几何仍须覆盖客户端和集成服务器 |

符号引用及摘要在`artifacts/mc-api/report.json`。完整javap输出在项目外的私有目录：`C:/Users/10113/.codex/visualizations/2026/10/19/01a15486-778e-7dd0-8a87-d08d07c93159/mc26-private-bytecode`，不随项目分发。

`src/minecraft/java/dev/mcdn/minecraft/BridgeClientInput.java`已对本机JAR和其安装依赖编译通过。原生类型夹具实例化真实ClientInput/Input/Vec2，验证七种按键映射、斜向归一化、撤销清零和过期输入拒绝。它只运行测试main，不启动Minecraft、不建立世界，也不证明玩家物理/碰撞/后台模拟通过。

首次运行夹具遇到两类环境问题：Java原生启动器的UTF-8 @argfile与本机GBK路径编码不一致，改为结构化Unicode进程参数；沙箱拒绝Java25为java.security调用toRealPath，申请只读执行放行后通过。没有修改JDK安全文件、关闭签名验证或更改系统环境。

官方版本背景：[Fabric 26.1](https://fabricmc.net/2026/03/14/261.html)说明Java25及无混淆迁移；[Fabric 26.3](https://www.fabricmc.net/2026/09/15/263.html)说明SDL替代GLFW及该版本工具链变化。本次接入名称以本机JAR为准，不直接照搬旧Yarn/GLFW路径。

## 消息约束

Wire层保持原64字节信封。新增Control层只接受不超过16KiB的JSON平面对象：全部key/value为不转义的可打印ASCII字符串，空白仅允许空格、TAB、CR、LF。最多32字段，key最长64字符、value最长2048字符。拒绝重复键、转义、非ASCII/DEL、数字/布尔/null值、数组、嵌套、尾随数据及未知字段。此子集用于机器身份/计数；世界/内容文本尚未定义schema。

所有u64均为规范十进制字符串：只允许`0`或非零开头的数字串，范围0..18446744073709551615，不允许正负号、前导零、小数或浮点中转。

### HELLO与HELLO_ACK

MC先发送HELLO(type1)，DC返回HELLO_ACK(type2)。双方信封session必须等于本次随机会话；worldEpoch/modeEpoch=0，sequence=1；HELLO的ack=0，ACK的ack=1（确认握手本身已消费）。每个连接使用一个Handshake对象，任一次接受尝试后不可重用；重复或失败后再发正确包也被拒绝。

两种body字段完全一致：

| 字段 | 校验 |
|---|---|
| schema | control-1 |
| role | HELLO为mc，HELLO_ACK为dc |
| nonce | 64字符小写hex，匹配本次256bit随机秘密；常数时间比较 |
| layout | mcdn-64-256-control-1 |
| build | 64字符小写hex，与会话预先绑定的对端构建指纹相等 |
| pid | 1..4294967295的十进制字符串 |
| startTime | 非零u64进程创建时间声明 |
| javaMajor | mc为25，dc为0 |
| capabilities | 当前必须为1，仅离散按钮输入；其它能力未启用 |

Pid/startTime仍是对端声明，协调器的OS身份核验尚未实现；不能据此终止进程。真实build集合、nonce描述文件的生成/权限和已加载程序集核验也留给协调器。本次测试双方使用明确的假构建值，随机nonce/session仅经子进程环境传入，不写入测试报告。

握手通过只产生Peer，不安装输入、隐藏Hero或授予世界控制。完整WORLD/MODE准备、就绪及提交状态机仍未实现。

### INPUT(type13)

字段为inputSeq、hostTick、eventSeq、held、pressed、released，均为规范u64字符串。按钮位0..6依次为forward/backward/left/right/jump/shift/sprint；掩码只能在0..127范围。鼠标、攻击、库存和文本输入未在本切片启用。

每个已提交mode创建新InputInbox，世界/控制代次必须非零且匹配认证Peer的session。envelope sequence按无符号单调增加且不能重用握手序号1；inputSeq从1连续递增；hostTick不倒退。每组按键变化eventSeq递增一次，没有变化则保持；pressed/released必须准确描述相对上一份完整held的变化。

socket worker解析、校验后入队，队列容量128。单生产者/单消费者JVM环使用volatile发布，游戏输入线程不加锁、不读网络、不等待。每tick最多应用一份含边沿快照，按下/松开不会合并；相同held的无边沿快照可以在128条预算内消费，避免DC帧率高于MC tick造成稳定状态积压。

队列中带**本机接收时**nanoTime。超过或等于250ms的输入不得补执行；时钟倒退也失败。最后消费的输入按接收时间计算租约，断流250ms后终止并清零，网络心跳不能续租按键。nanoTime只作MC进程内相对计时，不用于跨进程延迟相减。

消费ACK初始为已消费的握手序号1，只在安装原生输入回调成功后推进，入队不推进。它证明输入已安装，不代表客户端physics或集成服务器已提交。AckWindow拒绝超过本端已发送序号的ACK及ACK倒退。同一连接的SessionOrder必须跨mode复用，保持信封序号、已消费ACK与对端ACK单调；新inbox只重置该mode的输入/边沿序号，不重置连接顺序。

### RELEASE(type12)与故障

body仅包含reason，允许release/paused/focus-lost/world-change/shutdown。有效RELEASE终止该inbox，下一原生输入tick清零并取消队列，成功清零后才确认该RELEASE信封；consumedInputSeq保留最后实际安装的输入，不能把取消的输入称为已执行。

无效数据、身份/代次错误、序号/边沿错误、队列溢出、输入租约或排队过期、原生安装回调异常都锁定故障。EOF/暂停/失焦由调用者revoke；此后消息不能恢复控制，必须由完整模式交接创建新inbox。回调异常时尝试安装空输入并保留故障，游戏适配层仍须恢复原Hero/原ClientInput。游戏线程停止运行时只能在其恢复执行的tick释放，不能声称后台线程已修改原生游戏对象。

## 复现与结果

```powershell
python tools/verify_control.py
```

该命令先运行原39组codec及256条TCP回归，再运行两语言各50组控制schema样本、握手失败不可重用、消费ACK和Java输入故障矩阵。SPSC使用两个真实线程运行10000次按键变化。真实TCP的Java客体与C#宿主验证握手、按下、消费ACK、focus-lost松开、新mode和EOF清键；错误nonce在收到任何ACK/INPUT之前被拒绝。报告：`artifacts/control/report.json`。

原生类型夹具：

```powershell
python tools/inspect_mc_api.py --java-home 'C:\Users\10113\AppData\Roaming\.minecraft\runtime\java-runtime-epsilon' --mc-version-dir 'D:\MC\愚者\懒人包\.minecraft\versions\26.3-Fabric 0.20.0' --private-output 'C:\Users\10113\.codex\visualizations\2026\10\19\01a15486-778e-7dd0-8a87-d08d07c93159\mc26-private-bytecode'
```

以上均已通过。错误nonce属于预期拒绝，测试端捕获校验失败、关闭连接并正常退出；测试程序顶层也捕获其它失败并设置非零退出码，不能让未捕获异常触发Windows错误弹窗。此前拒绝测试确曾触发dotnet.exe应用程序错误，已修复该测试退出路径。

C# TCP端点和Java TCP循环仍是测试程序；故障矩阵中的输入sink不能冒充真实物理。下一步接世界几何版本应用、完整MODE交接和有原生锁的帧邮箱；然后才能接入真实MC/DC并验收行走/碰撞/帧/恢复。
