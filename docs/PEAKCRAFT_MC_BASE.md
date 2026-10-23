# PeakCraft MC 侧基线与 DC 适配边界

2026-10-23 用户指定 [PeakCraft](https://github.com/aeironnsarmiento/PeakCraft) 作为 MC 侧基础。固定源码提交 [`d07030ee527ee2a2facc989f5acae8a317968c02`](https://github.com/aeironnsarmiento/PeakCraft/commit/d07030ee527ee2a2facc989f5acae8a317968c02)，协议 v11，MC 26.3、Java 25。PeakCraft 是 SkyCraft 的移植；其 [MIT 许可证](https://github.com/aeironnsarmiento/PeakCraft/blob/d07030ee527ee2a2facc989f5acae8a317968c02/LICENSE) 保留 chasmlol 的版权声明。移植使用时保留原许可证和 PeakCraft、SkyCraft 署名。本仓库没有复制上游源码或游戏资产。

当前本机 `MC-PEAK-Bridge-26.3` 只含 `mcpeak-position-0.1.0.jar`（4166 B）和 Fabric API，不能当作 PeakCraft 的 MC 客体。PeakCraft 的 `fabric/` 提供原生玩家、镜像世界、三角面碰撞、输入、透明手臂/HUD、方块与角色网格导出；`peak/` 是 PEAK 的 Unity/BepInEx 宿主实现，不能原封不动加载进 DC。上游文档报告了 PEAK 实机结果；那些结果不等于本项目的 DC 验收。

| 能力 | 固定上游入口 | DC 适配结论 |
| --- | --- | --- |
| MC 原生玩家和库存 | `SkyClient`、`MirrorWorld` | 保留客体逻辑；使用隔离 MC 实例，不能与当前 MCDN physics 模组同时接管玩家。 |
| 厚度/楼层/斜坡碰撞 | `SkyCollision`、`TriCollider`，协议 `COL_REGION`/`COL_TRIS` | 保留原生运动解算。先从归档 DC 实体格产生协议夹具；之后改为 DC 地图 revision、关卡代次驱动的实时区域流。 |
| 第一/第三人称 | `SkyClient`、`AvatarExporter` | MC 拥有相机姿态与模型；DC 必须在自己的三维 pass 绘制模型和世界，不以全屏 MC 场景覆盖 DC。 |
| 画面边界 | `FrameExporter`、`WorldExporter` | 只把 MC 手臂、装备、HUD/屏幕用 alpha 叠在 DC；MC 方块/实体网格须进入 DC 场景深度和灯光。 |
| 挖放与战斗 | `SkyDig`、`SkyCombat`、event ring | DC 需定义改图事务、敌人 UID/伤害映射及拒绝/回滚；当前尚未接通。 |
| 所有权与恢复 | `SkyLink`、上游 [移植指南](https://github.com/aeironnsarmiento/PeakCraft/blob/d07030ee527ee2a2facc989f5acae8a317968c02/docs/PORTING-GUIDE.md) | DC 保持前台与关卡身份，MC 可先启动等待；DC 的 Hero 跟随、F7、切关和断连恢复仍需独立实现和实机验证。 |

本切片在 `tools/export_peakcraft_collision.py` 实现**归档 DC 几何 → 固定 PeakCraft v11 碰撞消息**的离线适配。它核验 MCDW 摘要、原生方块计划、上游提交和协议布局，拒绝非整数/重叠/异常体积，生成 `COL_CLEAR`、每 8³ 区域的完整占用格、暴露面三角形，保留原关卡 epoch；未支持区域不会被补成墙。输出只在私有 `artifacts/`，不提交 DC 地图或游戏图像。

本机固定归档场景的转换得到 10060 个实体方块、108 个区域、6558 个暴露面、13116 个三角形、217 条消息，流大小 1338096 B。单元测试覆盖跨区域相邻块内部面剔除、消息长度/占用、坏摘要拒绝。此证据只证明协议编码，**尚未证明真实 PeakCraft 客体消费、DC 实时地图、DC 内网格/HUD 绘制或完整三维闭环**。

固定上游的 `fabric/gradlew.bat build --no-daemon` 在本机 Java 25 完成，JUnit XML 记录 21/21 通过。生成的 `skycraft-0.1.2.jar` SHA-256 为 `0c99e5942d05356bf20b3496d308460d9df1c124f18c7e86889c4ebd49b8605c`。`tools/prepare_peakcraft_profile.py` 已从固定 MC 26.3 游戏 JAR、此模组和 Fabric API 0.161.0+26.3 创建全新的 `MC-DC-PeakBase-26.3` 私有实例，附上 MIT 许可证；没有替换现有 `MC-PEAK-Bridge-26.3` 或 MCDN 物理实例。它配置独立的 `Local\MCDN_PeakBase_v11` 映射名，供 MC 先进入后等待宿主。

2026-10-23 经用户批准，PCL 选择上述新实例并实机启动。MC 26.3 窗口进入主菜单；`latest.log` 记录 `skycraft 0.1.2`、SkyCraft 注册、SDL Windows 窗口创建及宿主共享内存尚未创建的等待消息。在无宿主的主菜单停留后，通过“退出游戏”正常关闭，日志末尾为 `Stopping!`。`tools/verify_peakcraft_client.py` 核对安装文件和这些加载/退出锚点，将日志摘要写入忽略提交的私有 `artifacts/peakcraft/client-load.json`。离线账户与 Realms 的 401/鉴权日志没有阻止主菜单加载。此实机证据只证明**客体独立加载并等待**；并未发送碰撞流、启动 DC 宿主或验证任何桥接画面。

接下来的顺序：先做仅 DC 宿主拥有映射的最小 `SkyState`/心跳/输入握手；随后发送当前关卡区域碰撞并量测原生走跳；再将 DC 原生 h3d 世界 pass 接受 MC 网格和透明 UI，最后处理挖放、敌人、交互及恢复。每步先有 DC/MC 可观察证据，旧 MCDN 帧覆盖方案只留作回退诊断。

