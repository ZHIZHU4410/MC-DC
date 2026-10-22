# DC 前台打开 Minecraft 原生库存

2026-10-21 19:02 实机验收通过，按用户要求完成此片后停止。会话 `5e8efaec-2655-4515-bd4d-cfdfa28ad03a`，DC PID38484、MC PID43652，两进程正常退出码均0。实验配置已解除，私有邮箱停止。GitHub仍只有之前一次推送c03f316795799f950aecf4016563017363896fa5，本片仅在本地。

E边沿随同一inputSeq传给后台MC，在游戏线程通过26.3的 `Minecraft.gui.screen()/setScreen()` 创建和关闭真正的 `InventoryScreen(LocalPlayer)`。私有manifest需同时启用inventoryControl与viewControl，实验扩展使用严格的native-ui-lab-1字段，不扩展生产control-1。状态与GPU帧日志记录实际界面类型。界面打开时继续消费协议输入，但原生BridgeClientInput将移动/跳跃掩码清零；鼠标不再被DC居中或转动相机。F7只关闭本次创建且仍由本次持有的界面，再恢复原生输入、相机、位置/模式和Hero。

真实DC前台挑战顺序：原生走跳/撞墙、深度移动、鼠标与F5三个相机，然后E打开库存；保持W+Space约0.8秒；E关闭；E再次打开；直接F7回切。不是调用测试命令代替实际前台按键。窗口截图 `artifacts/native-input/5e8efaec-2655-4515-bd4d-cfdfa28ad03a/input-inventory.png` 已目视确认DC标题栏内显示MC原生人物、装备槽、库存和合成格。

独立归档验收结果：

- 186条发送、185条原生实际消费，末尾1条全零快照由RELEASE取消并由原生ACK确认；185条视角/UI消费逐序号对应。
- 3个E边沿产生inventory → none → inventory；16个库存期间客户端采样held=17，但实际nativeForward/nativeJump均false、原生移动向量为0，XYZ变化不超过0.001。
- 255张MC GPU发布、254次DC原生上传全部匹配；DC接管前台记录50个不同帧，其中12个实际库存帧。不是截图回放。
- 客户端212/服务器211轨迹采样，墙接触各56次，双方原生跳峰201.25220334025371；诊断碰撞查询均0，10060个原生方块全部回滚。
- F7后实际界面为none、原生输入引用/相机/原位/模式恢复；DC收到原生返回确认后恢复同一Hero，接管期间Hero位置/生命不变，Game未暂停。

复核命令：`python tools/check_native_input_lab.py artifacts/native-input/5e8efaec-2655-4515-bd4d-cfdfa28ad03a`。归档包含自有包、源码、构建摘要、真实场景、日志和窗口截图，不含私有manifest/nonce。构建包含实际Knot/Mixin转换、11项帧尺寸边界、真实MC Input/Vec2及世界适配检查；DC正常与缺失加载器的原生启动门禁均通过。

本片只完成原生库存开关、显示和输入隔离。没有接入槽位鼠标点击、拖放/合成/物品转移，也没有挖掘放置、DC敌人与双向战斗、实时几何编辑提交或生产MODE。已通过的错误世界拒绝、正常关闭保存前回滚和同存档重载见NATIVE_BLOCK_WORLD.md；切关、断连、失焦、空中及崩溃恢复仍需专项验收。底部任务栏遮挡、低分辨率和夜间暗场仍存在。
