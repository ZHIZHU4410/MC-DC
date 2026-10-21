# DC 前台输入 → MC 原生玩家：有界集成实验

2026-10-21实施中。前置：真实DC实体子集的原生运动、MC GPU→DC内部全视图、仅Hero更新资格冻结与恢复均有实机归档。此片把它们接到实际前台键盘输入，使用现有Wire/control-1、InputInbox/BridgeInputBinding和250ms租约。它不是生产MODE；不伪造生产READY，也不声明完整物理隔离、战斗或世界编辑。

在标记的MC-DC-Physics-26.3/MCDN-Physics与带独立存档守卫的DC实例中运行。`live_color_session.py --physics --full-view --input-lab`生成私有ACL/15分钟过期的会话、一次性nonce、回环端口、实际双方包SHA256、原生场景digest/epoch。两端启动时核对自身实际加载包。DC监听127.0.0.1一个客体，MC HELLO/host ACK沿用control-1。双方world/mode上下文固定为已安装场景epoch/实验mode1；错误身份/序号/队列/租约终止。

仅实验端口接受type14 `native-input-lab-1`状态：state、geometry、tick、x/y/z、inputSeq、inputRestored（全部为严格ASCII字符串）。ready只由MC实际双侧安装/稳定站立后的游戏线程发布；MC预先切第三人称用于真实帧，但未装输入。DC收到匹配几何状态和0.5秒内原生帧后，F7才允许冻结原Hero的更新资格并发送20Hz前台白名单键。网络worker不读游戏对象，游戏线程不阻塞网络或文件。host队列过期100ms、客体队列128条/250ms租约；输入边沿与消费ACK沿用现有实现。

W/A/S/D、Space、Shift、Ctrl分别为原生前后左右、跳跃、潜行、疾跑。当前没有鼠标/视角转动、F5、库存/攻击或挖放输入；不把它称为最终可玩闭环。F7释放后MC恢复输入引用、相机并返回实验原位置/模式；DC待原生返回回执或0.4秒紧急等待后恢复Hero标记。失焦、暂停、陈旧帧/状态、连接结束、60秒上限触发同一释放。Hero.dispose事件在原生dispose之前恢复本次标记。外部冻结效果冲突、空中/切关/进程退出/伤害所有权仍需专项验证。

正常回切目前为独立实验的原位恢复，未把MC新位置映射给真实Hero；归档DC快照不随当前DC图变化。整个Game不暂停，其他实体逻辑可继续，因此生产伤害/交互不能忽略，也不会把本地实验授予正式MODE能力。后续必须接实时世界上下文、合法恢复空间和唯一伤害源，方可扩大范围。

实机验收：DC前台按F7后，只MC原生输入被消费，原Hero位置不叠加；前进/跳跃的真实客户端和集成服务器轨迹进入同场景实时DC图像；F7后客体/宿主分别恢复。保留实际包、nonce之外的运行证明、两端控制/消费日志、MC轨迹和DC窗口视频/截图。未实测分支不算通过。
