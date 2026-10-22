# DC 前台输入 → MC 原生玩家：有界集成实验

2026-10-21 19:02更新：[原生库存开关/显示及输入隔离](NATIVE_INVENTORY_SLICE.md)已实机通过，按用户要求完成后停止。槽位点击、转移和合成未接入。

2026-10-21前台键鼠、F5相机、F7回切、当前DC实体格门控及错误地图拒绝均已实机通过。最新证据见[NATIVE_BLOCK_WORLD.md](NATIVE_BLOCK_WORLD.md)。此片使用现有Wire/control-1、InputInbox/BridgeInputBinding和250ms租约；实验视角字段只在私有manifest明确启用时解析，不改变生产control-1输入schema。它不是生产MODE，不声明战斗或双向世界编辑完成。

在标记的MC-DC-Physics-26.3/MCDN-Physics与带独立存档守卫的DC实例中运行。`live_color_session.py --physics --full-view --input-lab`生成私有ACL/15分钟过期的会话、一次性nonce、回环端口、实际双方包SHA256、原生场景digest/epoch。两端启动时核对自身实际加载包。DC监听127.0.0.1一个客体，MC HELLO/host ACK沿用control-1。双方world/mode上下文固定为已安装场景epoch/实验mode1；错误身份/序号/队列/租约终止。

仅实验端口接受type14 `native-input-lab-1`状态：state、geometry、tick、x/y/z、inputSeq、inputRestored（全部为严格ASCII字符串）。ready只由MC实际双侧安装/稳定站立后的游戏线程发布；MC预先切第三人称用于真实帧，但未装输入。DC收到匹配几何状态和0.5秒内原生帧后，F7才允许冻结原Hero的更新资格并发送20Hz前台白名单键。网络worker不读游戏对象，游戏线程不阻塞网络或文件。host队列过期100ms、客体队列128条/250ms租约；输入边沿与消费ACK沿用现有实现。

W/A/S/D、Space、Shift、Ctrl分别为原生前后左右、跳跃、潜行、疾跑。鼠标位移及F5边沿绑定同一inputSeq，原生消费后调用Player.turn及CameraType.cycle；E通过可选native-ui-lab-1边沿开关真实InventoryScreen，打开时抑制移动和相机输入。尚无槽位点击、攻击或挖放输入。仅DC前台接管且未打开库存时居中鼠标，F7恢复原指针位置；失焦不移动其它应用上的指针。F7后MC关闭本次持有的库存，恢复输入引用、相机及实验原位置/模式，DC等待原生恢复回执（正常最多1.5秒、通道故障0.4秒）再恢复Hero标记。失焦、暂停、陈旧帧/状态、连接结束及60秒上限触发释放。Hero.dispose前恢复本次标记。外部冻结冲突、空中/切关/任意进程故障及伤害所有权仍需专项验证。

正常回切目前为独立实验的原位恢复，未把MC新位置映射给真实Hero；归档DC快照不随当前DC图变化。整个Game不暂停，其他实体逻辑可继续，因此生产伤害/交互不能忽略，也不会把本地实验授予正式MODE能力。后续必须接实时世界上下文、合法恢复空间和唯一伤害源，方可扩大范围。

现增加真实DC实体子集门控：F7前验证当前MapUid、固定区域内全部实体格与私有source.mcdw/source.json证明一致，接管时每次输入采样再次验证，关卡存储指针或实体掩码变化即撤销。只比较Plain/Invisible实体语义；其它7格、敌人/交互不在此证明中。地图变化当前导致释放，不做动态重建或编辑同步。

端口启动已改为DC实际绑定127.0.0.1:0后在私有目录发布control-endpoint.json（session/实际dcBuild/port），MC worker核验后再做nonce握手，避免预选空闲端口的时序竞争。接管前等待最多10分钟，私有manifest仍15分钟过期，活动输入租约仍250ms。服务器正常关闭前恢复10060位置及玩家原位；实际server-stop兜底与重载实测通过，不声明任意崩溃恢复。

实机验收：DC前台按F7后，只MC原生输入被消费，原Hero位置不叠加；前进/跳跃的真实客户端和集成服务器轨迹进入同场景实时DC图像；F7后客体/宿主分别恢复。保留实际包、nonce之外的运行证明、两端控制/消费日志、MC轨迹和DC窗口视频/截图。未实测分支不算通过。

2026-10-21已通过会话`cf9f43fa-2fe6-4a70-b13e-e533091decbe`：85条真实前台输入；客户端100/服务器99采样，双方墙接触55采样，身体maxX均为0.949999988079071；原生跳跃峰值201.2522033403/201.2491870787，深度位移0.42689。Hero UID49在接管记录中位置/生命不变，Game.paused始终false；F7后原生输入引用、相机、位置/模式恢复，DC记录nativeReturnConfirmed=true后恢复Hero资格。358次MC发布、285次DC原生上传逐帧一致，接管时DC前台有22个不同帧。两进程正常退出0，配置已解除。可独立复核：`python tools/check_native_input_lab.py artifacts/native-input/cf9f43fa-2fe6-4a70-b13e-e533091decbe`。归档不含私有manifest/nonce。

实验期间发现安装环境已从DCCM35.13.9更新至35.14.1，GameProxy SHA256变为25867d0df217f0b2d0b1b6ee32d05e16379bf9c5dd60abdde4bd2946ac5fa727。旧指纹正确拒绝启动；新版移除了OnBeforeBroadcastEvent，存档守卫改为启动前构造int.MinValue优先级模块，末尾int.MaxValue资格检查保留。当前包已重新构建，私有缓存/包更新前完整备份，真实VM正常启动及缺失加载器拒绝均重新通过。原游戏目录没有回滚或改写。鼠标、切关、失焦/断连、伤害与世界编辑尚需后续验收。
