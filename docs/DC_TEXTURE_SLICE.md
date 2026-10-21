# DC 原生纹理显示诊断（12帧上传与目视显示通过）

本片把已验证的12张MC原生GPU图像，作为**记录帧回放**送入DC自己的Heaps纹理和HUD Bitmap。不接实时协议、不使用窗口嵌入/桌面叠加，不授予Hero或MC输入控制。编译或upload调用返回不能代替目视显示验收。

## 已准备

- `src/dotnet/Mcdn.DcFrameProbe`：使用本机GameProxy的`Pixels.Class.alloc`、引擎已有的`Texture.Class.nativeFormat` RGBA对象、`Texture.Class.fromPixels/uploadPixels`、`Tile.Class.fromTexture`和`Bitmap`，父节点为原生`pr.Game.Class.ME.hud.root`。只读取GameProxy元数据，不复制游戏实现；签名报告`artifacts/dc-render-api/report.json`。
- `tools/stage_dc_frames.py`：只接收已通过的原生采集报告，逐张核对PNG SHA256，转换为有界top-down RGBA。原图不变；playlist明确`recorded-native-mc-world-color-diagnostic / eligibleForControl=false`，不冒充MCDF角色帧或实时world-color通道。
- `tools/build_dc_frame_probe.py`：编译本项目独立附加包，运行时GameProxy指纹与原探针一致。只分发自己的DLL/modinfo，不带游戏绑定或资源。
- 启动时固定playlist SHA256；后台解析其不可变私有副本，最多12帧、每边≤1024、每帧≤4MiB。文件长度/顺序/哈希验证和IO都在后台；一次仅投递一帧，真实上传回执之后才推进下一帧。
- DCCM游戏线程分配原生Pixels并复制到有效offset，首帧创建Texture/Tile/Bitmap，后续同尺寸复用纹理uploadPixels。显示宽220个HUD单位，位置(12,12)。不等待文件/另一进程；回执由后台写入JSON。
- Hero dispose时移除Bitmap并释放自有Texture；游戏退出只取消后台任务，避免在VM/driver销毁阶段调用原生对象。异常禁用该诊断并尝试清理，不接管Hero。

## 预检与当前实例

原存档/配置和DC实验存档备份于 `artifacts/backups/20261020T090112412513Z-dc-originals`。旧私有DC正常窗口关闭后，准备脚本加入独立附加包；原探针/守卫保持不变。新启动配置包含两个包的所有哈希和回放playlist摘要。

最初的正常原生启动预检同时看到save guard、FrameProbe、原地图Probe初始化，并在原游戏入口前正常Exit0；空加载器负测正常Exit2拒绝。当时仍待角色场景验证。晚间实机修复与最终显示证据见下文，不把preflight当GPU证据。

```powershell
python tools/stage_dc_frames.py
python tools/build_dc_frame_probe.py
# 先正常关闭已有私有DC，再执行：
python tools/prepare_dc_lab.py --include-frame-probe
python tools/start_dc_lab.py --preflight
python tools/start_dc_lab.py --preflight --missing-loader-check
python tools/start_dc_lab.py --launch
python tools/check_dc_frames.py
```

`check_dc_frames.py`核对本次启动、已加载包、源playlist与每张原生上传回执。两张以上仅报告`native-upload-pass-display-pending`，仍需实际查看DC窗口中的图像、颜色、方向和连续更新。记录帧播放完成不代表MC后台持续产生实时画面，也不代表三维DC世界/控制闭环。

## 2026-10-20 晚间实机结果

用户再次授权代理操作，并确认放开键鼠。控制通道恢复ready；前次MC/DC均已退出。本次目视Steam菜单并切入离线模式后启动私有DC，无需启动MC即可回放先前采集的图像。

首次进入角色场景实际触发`Cannot convert from RGBA to RGBA`，异常被诊断包捕获并停用显示，DC未崩溃。DCCM的枚举构造会分配新HashLink对象；据本机异常和公开包装器源码推断，其与引擎已有格式对象的身份比较不相同。修复为复用`Texture.Class.nativeFormat`，并要求其为RGBA，而不是重新构造枚举。修正版随后实机通过；没有修改公共加载器/游戏实现。

精确校验PID/创建时间/程序路径后WM_CLOSE正常退出，备份实验save/旧包/启动spec至`artifacts/backups/20261020T121428005072Z-dc-frame-replace`。`replace_dc_frame_probe.py`仅替换已固定摘要的自有附加包，保留既定原点和守卫，同时更新package_files/private_game_files两份摘要。正常预检Exit0、缺加载器负测Exit2均重新通过。

修正版包SHA256 `cdcef627bfc7d413ca89735fa6b964c198f995cdf2690d14883b5f76dba26f7a`，正式私有DC PID37492，创建时间20:15:36。20:16:13–20:16:25完成12张原生上传，20:16:26回放完成。实际窗口左上角显示原生MC天空、云、草地、右手和物品栏，方向与颜色正常；截图`artifacts/lab/dc-frame/visible-1792498611472977000.png`。静态场景在小预览中的逐帧差异没有独立分辨，连续更新由12张顺序上传回执证实。

`runtime-report.json`只报告native-upload-pass-display-pending；另外的`visible-report.json`绑定启动spec、playlist、上传报告与目视截图，报告visible-recorded-replay-pass。两类证据分开，避免自动检查器冒充目视验收。代理使用前台窗口校验的Esc扫描码进入暂停菜单，点击返回标题并确认；缩略图消失、日志无清理异常，截图`visible-1792498807364588300.png`。未测GPU分配统计，也不宣称释放计数已核验。

旧17:01原存档基线与晚间状态存在差异：旧自动备份缺失，18:47新自动备份与19:52两个其他模组配置已出现，后者时间早于本次20:10启动。因此不声称跨会话零变化、不还原用户文件。差异写入visible-report；新只读备份/基线`artifacts/backups/20261020-evening-original-baseline`之后的标题清理测试核对变化0。隔离守卫每次仍通过本机存档路径和云调用阻断检查。

桌面测试已由用户明确授权代理控制。`dc_lab_window.py`限定当前记录的实验进程、创建时间、可执行路径和唯一窗口；输入/截图还要求前台匹配。当前完成记录回放显示诊断，下一步需要独立的world-color通道语义与实时生产/失效处理，不能将完整场景塞进仅支持player/effects的MCDF槽。
