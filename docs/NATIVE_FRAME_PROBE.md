# 真实 MC 渲染目标诊断（实机采集通过）

2026-10-20，继 v0.6 原生邮箱组件后，新增独立 `mcdn-frame-probe-0.1.0.jar`。已对实际 MC26.3 编译并通过真实 Knot/Mixin 入口初始化及 GameRenderer 钩子合并预检。它不是 DC 绘制模块，也不证明输入接管。

实机：修正版 f212d225... 在最大化 2560×1494 下完成12张原生GPU读回，后台拟合为1024×598。完整PNG/SHA256、姿态、矩阵和推进tick通过检查，已目视确认图像内容/方向。当前证据 `artifacts/frame-probe/runtime-report.json`，目录 `artifacts/lab/observations/world-color/e04726bb-80bb-49e1-837f-0d49f84a9603`。仍未进入原生邮箱或DC绘制。

## 本机入口与范围

只读本机游戏 JAR SHA256 `4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d`；26.3 的 GPU API 位于 `com.mojang.renderpearl`。`MainTarget` 使用 RGBA8_UNORM；`GameRenderer.render` 完成后，Minecraft 随后提交命令及 present。`Screenshot.takeScreenshot` 使用 GPU buffer/纹理拷贝和异步完成回调，不是桌面截图。OpenGL 本机实现通过 RenderSystem fenced task 回调；没有调用无限等待或阻塞等 GPU 的新代码。

`tools/inspect_render_api.py` 记录25个实际类型的 API 签名/文件指纹。完整反汇编存放在工作区外私有可视化目录，不复制到模组包或仓库。`artifacts/render-api/report.json` 只记录 API 与私有路径。

此包从主场景采集**含 HUD 的完整原生 MC 图像**。当前碰撞导入不生成 DC 的可见网格，因此该图仍是 MC 自己的实验场景。既有 MCDF 协议定义角色/特效层，不能以 player flag 填入整场景图；本诊断只写 PNG+JSON，不写 MCDF/帧邮箱，不提交 MODE/READY。未来完整三维显示须另行协商 world-color/depth/相机矩阵通道。

## 有界执行

- 只接受已有 `mcdn.lab.manifest` 和标记实验 gameDir；要求单人集成服务器与原生玩家，暂停时跳过。不更改焦点、输入、世界、碰撞计数、存档或既有探针代码。
- GameRenderer.render TAIL 请求采集；请求前冻结原生 gameTime/playerTick、partial tick 插值脚底、当帧 CameraRenderState 位置/角度/投影和视图旋转矩阵。
- GPU 完成时仅检查 Level/Player/Server 对象身份、相机类型、渲染目标身份/尺寸及5秒时限；不重新读取最新姿态配旧像素。没有正式 DC 世界/相机代次配对，`bridgeContextPaired=false`，永远 `eligibleForControl=false`。
- 最多12次请求，间隔至少2秒，最多一个GPU读回在途；源像素数最多3840×2160。后台用NativeImage.resizeSubRectTo/STB的CPU线性缩放保持比例、输出边长≤1024，不依赖源尺寸公因数；最小输出边长1。每个原始CPU/GPU表面≤约32MiB，另有最多一份待写图像及一份正在写的图像。不以该诊断路径声明实时帧率。
- 回调把 CPU NativeImage 所有权交给后台线程，最多一份待写；后台 PNG 编码/文件 I/O，写临时文件后原子提交。全部图像在消费/替换/拒绝时关闭。GPU失败停止捕获而保留游戏。
- 时间记录是同一 JVM nanoTime 的诊断顺序，不能与 C# Stopwatch 相减，也不是输入到显示延迟。

## 构建、安装与验收

```powershell
python tools/build_frame_probe.py --java-home 'C:\Users\10113\AppData\Roaming\.minecraft\runtime\java-runtime-epsilon' --mc-version-dir 'D:\MC\.minecraft\versions\MC-DC-Lab-26.3' --transform
python tools/install_frame_probe.py --mc-version-dir 'D:\MC\.minecraft\versions\MC-DC-Lab-26.3' --install
python tools/check_frame_probe.py
```

构建以源代码警告为错误；只关闭安装依赖 JAR 的 classfile lint（JOML/Gson/游戏携带未随启动器分发的可选注解），不降低字节码校验。Java25 sandbox 读取自身安全配置的放行同前几片，不改 JDK 安全文件。

安装时固定游戏/原探针/构建和真实 loader 预检哈希，先备份实验 saves/options/manifest，再 CREATE_NEW 新 JAR；任何已有同名文件都拒绝替换。第一次备份被运行中的 session.lock 阻止，安装尚未发生；用户正常退出 MC 后重试成功。完整备份 `artifacts/backups/20261020T082244346679Z/mc-frame-lab-backup.zip`，安装清单 `artifacts/frame-probe/install.json`。原 `mcdn-lab-probe-0.5.0.jar` 保持 f595c665...，本次新包 8a5c619e...；不自动恢复或删除用户实验存档。

用户自行离线重启同一实例，进入实验世界，MC 保持前台、关闭暂停菜单约30秒。`check_frame_probe.py` 只读取本项目加载标记与输出，核对实际加载来源、包摘要、图像 SHA256、尺寸、非单色、冻结姿态/矩阵和时序；至少两帧且原生 playerTick 推进后才报告采集通过。随后仍须打开实际 PNG 检查图像内容。

## 实机修复与桌面接管

首次无帧来自本项目误用从未写入的 readyForLevelRendering 字段；扫描完整JAR仅定义类引用该名字，修正为原生渲染使用的 shouldRenderLevel。第二次无帧由2560×1494无法用整数因子缩到≤1024导致。只读诊断代理未注册字节码 transformer，把门控值读取提交到MC Render thread后确认原因；输出 live-gates.properties。临时 Window API 请求被最大化状态保留，未产出帧；后来通过精确HWND/PID/启动时间校验，Win32临时还原并缩小窗口，取得3帧基线，finally恢复最大化。该基线保存 native-baseline-report.json。

用户明确授权代理控制电脑完成精确测试后，代理目视确认PCL选择离线登录与MC-DC-Lab-26.3，向精确MC窗口发送正常关闭请求，确认保存退出后备份并安装CPU拟合修正版。备份20261020T084546680906Z，旧包可恢复；原碰撞探针未变。代理在同一离线启动器进入MCDN-Lab并最大化，12张连续原生帧通过。未使用强杀、HotSwap或游戏类重写；诊断代理随旧MC正常退出而结束。

FrameSizeBench覆盖实际2560×1494、纵向、无需放大、极细尺寸和非法/超量输入共12项；真实Knot/Mixin再验证通过。旧首次安装/修复的记录保留在备份及MODLOG，不代表当前包。当前安装SHA256 `f212d225c6716b7af6f4f2a719acf7bd3532d2be19e54b56ac3fabdec51c166d`。

PNG 采集通过不等于原生 IPC、DC 动态纹理、可玩三维 DC 世界或输入闭环通过。下一步是DC原生纹理上传/显示诊断，并为完整场景另立world-color协议。
