# 实时完整场景诊断切片（626帧实机通过）

路线：MC真实GPU目标→后台有界RGBA→Win32三槽邮箱→DC后台校验→游戏线程原生Texture/HUD。使用用户自己的Windows游戏、Fabric26.3/Java25与DCCM35.13.9，不接管Hero/输入。记录回放已单独验收，本片才检查实时生产与断流。

独立MCWC0.1诊断帧，384字节小端头、RGBA top-down straight alpha、每边≤1024、像素CRC32；UUID使用RFC字节序。不得进入MCDF角色层或MODE ready门控。

| 偏移 | 字段 |
|---|---|
| 0/4/6/8/12 | MCWC / u16 major0 / u16 minor1 / u32 header384 / u32 pixelBytes |
| 16/32/40/48 | UUID16 / u64原生Level流代次（非DC worldEpoch）/ u64保留0 / u64保留0 |
| 56/64/72 | u64 frameId / nativeGameTime / 请求QPC |
| 80/84/88/92 | u32 width / height / stride / format1 |
| 96/100/104/108 | u32 flags7=完整场景+HUD+仅诊断 / cameraType0..2 / sourceWidth / sourceHeight |
| 112/136 | 三个f64脚底xyz / 三个f64相机xyz |
| 160/164/168/172 | f32 yaw / pitch / partialTick / u32保留0 |
| 176/240 | 各16个f32列主序viewRotation / projection |
| 304/312/320 | u64 GPU读回完成QPC / frequency / u32像素CRC |
| 324..383 | 保留0 |

像素与姿态/矩阵在GPU请求时配对，完成时不得重采样；跨原生Level递增流代次。无DC上下文、深度或输入ACK声明。有类型邮箱入口：MCDF沿用MCDM0.1；MCWC使用MCDM0.2，offset52=channel1，锁名加入WorldColor，固定MCWC帧头。沿用0ms锁、完整复制、槽复用校验、abandoned故障停用，不允许两种帧混读。

本片协调器仅在标记实验目录生成随机会话、受保护映射和固定摘要清单，离线运行≤180秒、目标≤5帧/秒。单GPU请求、待处理图像/上传各1份；独立后台线程拥有邮箱并编码/校验，游戏线程不等待邮箱或文件。DC超过1.5秒无新鲜帧即撤下预览；返回菜单同样撤下。CRC不提供认证，仅本机同用户诊断，不宣称正式HELLO能力协商完成。

先运行两语言codec坏包/矩阵/尺寸/时钟/保留位及真实跨进程邮箱测试，同时回归旧MCDF故障测试。再由代理操作隔离实例，核对加载包/会话，验证MC tick/frameId推进、DC原生上传与可见输出、停止生产后的清理。编译/合成帧不计作实机链路通过。

## 实现与验证结果（2026-10-20 Asia/Shanghai）

- `WorldColorFrame.java/.cs`：不可变私有帧，检查范围/标志、保留位、有限姿态和矩阵、QPC顺序、源尺寸、UUID/流代次/帧号及CRC。33组黄金/损坏样本两语言一致，20张合成帧经真实Java25 JNI→Win32→C#传输，混读通道拒绝。
- `mcdn_ipc.cpp`保留旧ABI和MCDF/MCDM0.1入口，新增有类型MCWC入口；Java/C#包装器相应限制调用。旧邮箱五项跨进程忙锁/槽复用/坏像素/abandoned回归全部通过，历史DLL/报告保留于`artifacts/mailbox/v0.6-baseline`，新DLL SHA256 `3d155cff02593abd0d7e6438104688a9d1d66bac705771a7110eec288de3f57f`。
- MC独立附加包继续使用实际`GameRenderer.mainRenderTarget / Screenshot`异步GPU读回，冻结姿态/矩阵/原生流代次与QPC。后台缩放最大边512并读取NativeImage RGBA原始字节，单独线程拥有邮箱；实时模式不继续写每帧PNG，只保存首张原生PNG与有界回执日志。无指针时保留原12张记录诊断模式。
- DC把同一已测邮箱/codec源码链接到自有附加包，避免替换基础探针或其Protocol程序集。独立Thread持有邮箱并验证会话/无符号帧序/流代次/时钟/新鲜度；只投递一份不可变待上传数据。游戏线程复用原生Texture/HUD Bitmap、检查新鲜度，超1.5秒撤下预览。无Hero/Input替换。

首次由沙箱账户创建会话，受保护ACL阻止桌面用户访问；停止该helper并由桌面用户重新创建，没有放宽权限。初次实时运行已接通并记录数百帧，但读取可选latest JSON时，Windows禁止删除共享导致原子替换AccessDenied，生产诊断停用；证据保留在会话`bd5c729a-5cc2-4675-a7d3-adbd13c09846`。两端改为append-only JSONL作权威回执，可选latest快照的此类占用不终止原生链路。

最终会话`9dcf6a08-707a-469f-b5dd-51a2df8ff201`：

| 项目 | 实测 |
|---|---|
| MC附加JAR SHA256 | b5d0c934257bf38727277743148e777734a35f541ffe93662717aa2ff2ae69d1 |
| DC附加DLL SHA256 | 0c9f8a377b4c58e6f2ab736083f60bc0a7918c5db5dce0f952befbb7531ea843 |
| 真实发布/原生上传 | 626 / 626；626个不同像素摘要，原生tick推进 |
| RGBA输出 | 512×299；首张NativeImage PNG解码RGBA与传输像素SHA完全相同 |
| DC前台、MC后台 | 前台PID24996；4次采样两端帧号587→597→606→616 |
| Windows快照占用5秒 | 两份latest文件均禁止delete sharing；快照停留旧值，producer帧563→587、consumer562→587；均继续传输 |
| 主动断流 | 仅写stop-producer，游戏不退出；约1.4896秒后观察到DC清理日志，截图确认缩略图消失 |
| 软件计时 | GPU请求QPC至原生上传返回中位67.08ms、最大212.29ms；不是输入延迟、present或显示器延迟 |

实际DC窗口内天空、云、草地、手、HUD方向和颜色正常；MC仍是实验超平坦场景，**未绘制DC三维网格**。`runtime-report.json`自动校验仅报告上传通过；独立`visible-report.json`绑定目视截图/运行报告/文件占用与断流证据。截图只用于验收，绝不是MC图像生产源。全套归档含自身JAR/DLL、首张原生PNG、两端JSONL/日志/启动身份及摘要清单，不含游戏零售二进制。

本轮实际2515形状/7未支持仍在MC客户端/集成服务器以相同摘要被查询。旧17:01原存档基线包含用户跨会话差异，不重新声称该基线零变化；晚间新只读基线核对变化0，结论写入visible-report。Steam保持离线。

## 复现与清理

构建/组件测试：

```powershell
python tools/verify_mailbox.py --java-home <Java25> --jni-home D:\Jdk\jdk-21
python tools/verify_world_color.py --java-home <Java25>
python tools/build_frame_probe.py --java-home <Java25> --mc-version-dir D:\MC\.minecraft\versions\MC-DC-Lab-26.3 --transform
python tools/build_dc_frame_probe.py
```

正常关闭实验游戏、备份并替换自有附加包后，以**桌面用户**运行`live_color_session.py`保持映射存在（Codex沙箱中须使用桌面执行权限），再`configure_live_color.py --arm`。重新执行DC正负原生预检；用PCL离线启动原MC实验世界与受守卫保护的DC实验角色场景。自动化切焦困难时，Win键打开开始菜单后点DC任务栏按钮，避免反复最小化；MC最小化会暂时停止Surface采集，不能作为正常后台运行状态。

在临时配置仍有效、日志未复用时运行`check_live_color.py --require-stopped`。结束后正常关闭两款实验游戏，`configure_live_color.py --disarm`备份并删除仅本项目摘要匹配的MC会话指针/两项DC环境配置，再生成普通诊断模式的正负预检。实验实例`pauseOnLostFocus:false`保留，以支持后续后台桥接；原用户实例配置不变。

本轮游戏均已正常保存退出、临时指针/环境项已解除、helper已结束，普通DC实验入口的正负预检重新通过。归档可在游戏关闭后独立复核：

```powershell
python tools/verify_live_archive.py 9dcf6a08-707a-469f-b5dd-51a2df8ff201
```

下一步仍须完成正式会话/能力协商与代次配对、原生玩家输入/物理闭环和DC三维几何视觉；本片不授予控制，也没有测切关重连、深度合成、实体战斗、F7 Hero接管/恢复或全程性能。
