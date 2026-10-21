# 真实 DC 实体几何 → MC 原生玩家切片

2026-10-21：**归档真实 DC 实体几何上的 MC 原生玩家运动与原生 GPU 可见性实机通过**。用户确认放开键鼠后，由启动器离线登录进入专用实例和已有实验世界。最终会话 `7232d58c-8a53-4a12-96a6-df789c91cebc`，MC PID31296；客户端200/服务器199采样，墙接触bodyMaxX均为0.949999988079071，自由跳跃脚底峰值均为201.25220334025371，真实碰撞查询1780/1232。170条输入消费、租约清键/原输入引用/相机/原位原模式恢复通过。最终目标仍是 DC 前台输入、MC 后台原生模拟/渲染、DC 内显示和双向交互。

最终实际加载JAR SHA256 `473630a7cb48273ba8cfae7bffde0038a28c9adb60001110c668098415b199dd`，替换前完整备份 `artifacts/backups/20261021T010404425777Z-dc-scene/lab-before.zip`。5张原生GPU图像分别配对客户端native tick180/220/260/300/340（原生渲染脚底允许tick内插值差）；5张像素文件摘要各异。已目视frame3的第三人称玩家、真实几何石质地面/墙体，夜间光照偏暗；并非完整DC素材或自由视角交互验收。

首次会话 `5830d1f3-53a7-4791-ba07-5a9450eb17e0` 运动通过，已独立归档，但画面存在旧合成场景遗留显示体。第二版仅在已备份的专用实验世界、指定空间内扫描并清理本项目标签BlockDisplay，实际移除5个，不触碰其它实体。首次GPU初始相机含Infinity导致导出停用；现跳过非有限原生样本，并只在Y≥195且第三人称时采图。真实Java25编译、Knot/渲染钩子变换、尺寸回归再次通过；只更新物理实验实例，未替换原桥接实例。

本片以真实 DC 导出替换上一片五块合成夹具。来源为已保留的 DC 会话 `8715c251-2940-400e-83d9-e0dae4b96b1f`，epoch 2、revision 1、MapUid 582914；原始摘要 `df7a2b81472a368dc9adfc262b2db7f9cf16a1827b206833cb3b9f78e3cefb8c`。这是归档实体子集，不是本轮运行中的 DC 会话。

`prepare_dc_scene.py` 保留全部 2515 个形状、ID、会话和修订，仅将 Y 刚性平移 +260 到原生空气区域。转换后摘要 `93cdd7a3860188a92d90005250f074c52c8a53b933557e7b0ccde8467662fc48`。四格深度、空洞和楼层结构原样保留；仍有 7 个未支持格，未补成墙或地板。脚本从原有几何选择地面 Y200、起点 X−4.5500000119/Z−1.5、右墙 X0.9499999881 的连续可走通道，不创建人工挡板。

`PhysicsProbe` 继续通过原生 `LocalPlayer`/`ServerPlayer` 解算，仅在建场和恢复时传送。两侧精确玩家碰撞查询使用相同世界快照，按查询体筛选形状。原生 `BlockDisplay` 以完全相邻的水平格合并为 72 个显示体，物理仍使用全部原始形状。显示体只是诊断可见体，不是可挖掘方块或完整 DC 材质。

复用专用 `MC-DC-Physics-26.3`/`MCDN-Physics`，不加载旧地图探针。安装器要求已记录自有包摘要、已验证新构建且没有运行中的 Java 游戏；先完整备份实验存档、旧包和配置，再替换自有包及两份实验配置。首次备份为 `artifacts/backups/20261021T004832165127Z-dc-scene/lab-before.zip`；后续安装的最新恢复路径在 `artifacts/dc-scene/install.json`。恢复前须正常退出实验实例。原 DC 和 MC-DC-Lab 包未改动。

预检通过实际 Knot 初始化/注入、真实 `CollisionGetter.noBlockCollision` 的地面接触、墙体重叠及深度空气查询。独立 Python 校验逐条比较原始记录与平移后记录、保留世界身份，并验证错误文件名、摘要和截断拒绝。这些检查不证明玩家已走动或游戏已显示。

实机验收顺序：离线启动专用实例，进入已有实验世界；等待真实地面稳定后写本次输出目录的 `begin` 标记。执行 200 tick 有界本地输入脚本，走到真实 DC 墙、自然跳跃、退后再跳；最后保持前进并停止供给，核验 250ms 租约清键及原输入对象恢复。分别记录客户端和集成服务器轨迹、碰撞查询、输入消费及位置/模式/相机恢复。GPU 诊断同时输出有限数量的真实帧供目视确认。

```powershell
python tools/prepare_dc_scene.py --metadata artifacts/lab/dc-probe/8715c2512940400e83d9e0dae4b96b1f/latest.json
python tools/build_physics_probe.py --java-home C:/Users/10113/AppData/Roaming/.minecraft/runtime/java-runtime-epsilon --mc-version-dir D:/MC/.minecraft/versions/MC-DC-Lab-26.3 --dc-scene
python tools/verify_dc_scene.py
python tools/install_dc_scene.py
# 仅在实验游戏正常关闭后执行实际安装：
python tools/install_dc_scene.py --install
# 有本轮真实 events.jsonl/complete.json 后运行；缺失时失败，不回退到旧证据：
python tools/check_dc_scene_runtime.py
python tools/check_dc_scene_render.py --frames artifacts/dc-scene/observations/world-color/22a965ec-1ffc-403d-852a-09f5990d050c
# 实际目视后另传 --observed 描述，不传则保留视觉待验收。
# 游戏正常退出后冻结实际包、源、日志和本轮证据：
python tools/archive_dc_scene.py
python tools/check_dc_scene_runtime.py --archive artifacts/dc-scene/observations/7232d58c-8a53-4a12-96a6-df789c91cebc
```

`verification.json` 只接受来源几何与原生预检。运行验收器需要真实双侧轨迹，检查全部身体样本不穿透 DC 几何、撞到指定真实墙、原生跳跃/落地、170 条输入消费、租约/原对象恢复和原位原模式恢复；不接受旧合成记录。

后续仍需：实时 DC 世界/控制上下文提交、原 Hero 旁路及 F7/断连/切关恢复、DC 前台输入、自由视角/第一第三人称、帧与几何/姿态配对并在 DC 内全视图显示。实体/流体/原生块状态完整隔离、单向平台/门语义、可编辑方块账本、库存和双向战斗均未完成。本片不授权生产 MODE。
