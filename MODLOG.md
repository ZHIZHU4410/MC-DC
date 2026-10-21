# 原生 MC/DC 桥接工程日志

2026-10-21 09:44 当前：合并显示43帧及Hero旁路前置验证通过，详见docs/COMBINED_SCENE_SLICE.md。最终合并会话5a49540a-3258-4260-bd56-be37a17b774b（DC8060/MC41192），43张真实GPU/原生DC上传匹配、24次DC前台背景推进样本，MC实际归档DC几何200/199轨迹、走跳/墙限位/恢复通过；全窗口目视/停供撤图/正常退出/归档独立复核通过。初轮40帧截图裁切来自Python窗口GetWindowRect未设150%DPI感知，已修正，不当成原生缩放失败；增加原生逆变换并读回scene/window/local2538x1546 scale1证据。底部任务栏遮挡窄条、夜间暗/低分辨率限制保留。临时会话指针/环境均解除，辅助进程停止。

继续推进Hero职责入口：先Game.paused独立校准ff20c41a 120帧/键盘挑战/恢复通过但会冻结世界而不采用。选择性Hero资格校准6b6b231d PID19028通过：仅自有原Hero isFreeze=true/isAlwaysUpdated=false，native canUpdate拒绝；120帧Game.paused=false，Hero坐标/生命不变，Hero资格查询213、其他实体允许资格1042；两个标记原值恢复，Exit0。代码仍为有界独立前置探针，不是MC控制/F7/伤害旁路完成。原生伪代码.bc生成体的近似表达式不能当准确源码；私有反编译在Temp，未进工程。通过实际native值与查询/输入挑战判定。

新工具：live_color_session --physics --full-view、configure_live_color允许两个标记实例；observe_combined_scene有界13s记录前台/帧/完整截图；archive_combined_scene/verify_combined_archive保存可离线复核证据。PauseLab.cs/配置/exercise/archive工具支持有界整个Game暂停和只Hero资格两种前置校准；当前配置已解除。下一步持续接真实DC前台输入→MC原生租约及选择性Hero恢复，不把MCWC诊断当生产MODE。

2026-10-21 09:05 当前切片实机通过：用户确认键鼠后，PCL离线启动专用MC-DC-Physics-26.3/MCDN-Physics；最终会话7232d58c-8a53-4a12-96a6-df789c91cebc/PID31296，实际JAR473630a7cb48273ba8cfae7bffde0038a28c9adb60001110c668098415b199dd。客户端200/服务器199样本，DC墙maxX0.949999988079071、跳跃峰值201.25220334025371两侧一致；查询1780/1232；170输入、租约/原输入/相机/原位survival恢复通过。5张真实GPU帧与native tick180/220/260/300/340配对，目视frame3为玩家/石质地面墙体，无旧金块玻璃。正常WM_CLOSE退出后归档复核。真实DC实体子集→原生物理→MC原生渲染已接通；未接DC前台输入、DC内显示或生产MODE。

首次5830d1f3会话运动通过并独立归档，但旧合成场景遗留5个自有BlockDisplay干扰视觉，且初始GPU相机Infinity使导出失败。修复仅扫描专用已备份实验世界/受限区域/项目标签BlockDisplay并移除，帧采集跳过非有限样本并可配置Y/相机门控；不开放NaN/Infinity序列化。实际API为entityTags()，经javap核验。重新编译/Knot渲染及物理变换/尺寸回归通过；最终备份20261021T010404425777Z-dc-scene。下面保留前期状态，不作为当前待确认状态。

2026-10-21 当前推进：真实 DC 实体几何接入原生玩家，见 docs/DC_SCENE_SLICE.md。归档2515格原样保留身份/ID并Y+260平移，72个原生显示体；Java25/Knot/原生碰撞查询/来源复核通过。实验实例备份替换完成；等待本轮键鼠确认，实际走跳/GPU可见性未验收。不是生产MODE或实时DC输入闭环。下述“当前推进”作为历史记录。

本轮最终实验JAR SHA256 `44eb4701edaf1dc3bf1ff6d9bc56bff5787a8a3124608e694b9ac9da8e1cb4ef`。最终替换前备份 `artifacts/backups/20261021T005024658271Z-dc-scene/lab-before.zip`，首次旧合成版本备份 `artifacts/backups/20261021T004832165127Z-dc-scene/lab-before.zip`。仅替换MC-DC-Physics-26.3自有包/mcdn-physics.json/mcdn-lab.json；原DC/MC-DC-Lab未替换。普通沙箱Java安全配置加载失败后，经自动批准的本机Java25离线预检通过，未改安全属性。旧a7415741归档验收器复核仍通过。新check_dc_scene_runtime.py已就绪，尚无本轮原生轨迹，不能将预检写成运动通过。当前工具目录没有聊天记录读取工具，以工程日志/切片/归档续接。

当前推进：实时完整场景诊断，合约/边界与验收预先记录在docs/LIVE_COLOR_SLICE.md。MCWC独立于MCDF角色层，复用三槽同步算法但保持通道类型隔离，先测试再实机；Hero与输入关闭。

该片已于2026-10-20晚间完成：626张真实GPU帧配对上传及目视显示，后台推进、真实快照占用故障注入和主动断流撤图通过；两款游戏正常保存退出、临时会话解除，详见文末及LIVE_COLOR_SLICE.md。

项目迁移：用户指定独立目录 D:/steama/steamapps/common/Dead Cells/coremod/MC-DC；从 DCCMDEAD CELLS/MinecraftNativeBridge 整体迁入，包含研究源码快照、文档与来源指纹。不迁移旧 ReverseStrongCompat，不改动 ICEY 工程。

2026-10-19（Asia/Shanghai）

- 用户授权本轮 GitHub 预研、设计与工作区产物；先研究后写协议。未据此安装MC模组、重启或操作游戏。
- 先完成 research/GITHUB_RESEARCH.md，再编写 docs/PROTOCOL_DRAFT.md 与 docs/MINIMUM_LOOP_PLAN.md。
- 固定提交：crossover d1723873ec8f370389cf19f74fac455b9e581321；DCCM 343ee7ea8b90572e11999fd26c3efc1a9136f2de；DC Multiplayer 7ed82513b71a0d947d628764b0b72450be3e0aa8；MineCells 317eac3152b23b5332dc12c2d69a919bca21a62b。
- 四仓库克隆在 research/upstream，已gitignore，未执行上游代码。补充SkyCraft协议、Skyring schema、SekiroCraft和ProtoInput的阅读层级记录在研究报告。
- 明确研究范围没有 DC 世界身份 + MC 原生玩家的完整先例；相邻项目只能提供组件经验。
- 用户异步确认最终产品是可转动视角的三维DC地图、MC第一/第三人称操作。侧视运动平面只能作为首切片验证，不是最终产品限制。
- 首个闭环未通过前不启用完整挖放/库存/战斗承诺。三维深度与DC二维AI/交互、实际原墙体编辑、MC26.3原生工具链均列为未验证。
- 历史资料沿用指定两线程及ICEY本地仓库1d4c4f4，公开v1.0.11与本机v1.0.12候选分开，不修改既有工程。
- 当前仅研究文档；本项目编译、模拟端点、真实游戏证据均未进行。旧窗口原型不能计入本项目证据。
- 完成来源manifest：4个固定提交、22个实际阅读文件的SHA256与永久源码链接；补充网页资料单独标记阅读深度。完成文档布局一致性检查：64字节信封和256字节帧头连续无重叠；这不是codec、模拟端点或实机验证。

## 后续推进：v0.2.0-protocol

- 用户要求阅读项目、参考六个相邻项目并开始推进，范围从研究扩展到工作区代码和只读核验；此前“本轮仅研究”作为历史记录保留。
- 路线仍是双原生进程：MC原生模拟/渲染，DC输入/世界/最终显示，像素+逻辑桥。Windows需要自己的DC/MC、DCCM及匹配26.3的Fabric/Java25；不同于crossover，DC前台生产输入，不让MC持焦点。
- 新增Java/C#精确64字节信封、1MiB单包限制、TCP增量拆包、poison-on-error、会话/代次/无符号序号过滤、256字节不可变帧快照及CRC校验。
- tests两端和tools/verify_protocol.py：Python独立struct黄金字节；每语言39组正常/错误样本、切分/合包、代次/重放/帧配对通过；256条Java→C#→Java实际loopback TCP逐字节一致。报告artifacts/protocol/report.json；不是游戏验收或共享映射压力测试。
- tools/inspect_environment.py定位MC26.3/Fabric0.20.0/API0.164.0+26.3；配置Java25、抽样class major69。PATH Java21.0.9只作codec验证。DCCM35.13.9及ModCore/Common/GameProxy摘要写入artifacts/environment.json。
- CIM命令行查询被系统拒绝，未提升权限。启动器Java25、MDK/build/加载身份仍未绑定。NuGet用户配置受限，改用项目离线配置及子进程私有APPDATA/CLI_HOME后构建通过。
- 当前目录无.git，未初始化或提交；报告记录源码/样本摘要。研究快照保持只读。
- 未安装/操作游戏、改存档、安装loader或触碰ICEY。后续补Java25/26.3入口、语义握手/输入租约及三槽原生IPC，见docs/IMPLEMENTATION_STATUS.md。

## 下一切片：v0.3.0-control

- 用户要求进入下一切片。沿用双原生进程像素+逻辑桥，先做匹配入口和可验证控制基础；无新增安装或游戏操作。
- um kb search Minecraft/Dead Cells无匹配笔记。只读启动器日志定位C:/Users/10113/AppData/Roaming/.minecraft/runtime/java-runtime-epsilon，Java/Javac25.0.1实际可用，不另行安装。
- tools/inspect_mc_api.py以本机JAR+javap记录LocalPlayer.input/aiStep/applyInput/sendChanges、ClientInput/KeyboardInput、输入包setLastClientInput、位置包handlePlayerPositionChange、Entity/CollisionGetter形状入口。完整字节码输出存项目外mc26-private-bytecode，项目仅保存引用/摘要。
- 新增Control.cs/Control.java：control-1严格schema、nonce/构建/role/版本能力绑定、一次性握手、精确u64、消费ACK窗口。Java InputInbox为128条SPSC队列，保留边沿、排队/租约250ms、错误/溢出/EOF/释放终止；稳定held可同tick有界消费，防host帧率积压。没有完整WORLD/MODE提交或Hero恢复。
- 新增BridgeClientInput：只写原生Input与Vec2，不传送坐标或重写物理。对实际26.3 JAR编译通过；真实ClientInput/Input/Vec2夹具验证全部7按键、归一化、撤销和过期清键。不安装、不自动替换LocalPlayer.input。
- 首次原生夹具失败：Java launcher @argfile受GBK路径编码影响，改用结构化Unicode参数；Java25 java.security的toRealPath被沙箱拒绝，读内容本身成功。只读放行运行后通过；不修改安全属性/签名验证/系统环境。报告artifacts/mc-api/report.json。
- tools/verify_control.py：原39组codec/256条TCP回归通过；每语言50组控制样本、握手不可重用/错误头、消费ACK、租约/队列/边沿/重放/代次/安装失败矩阵及10000次双线程SPSC通过。实际Java↔C# TCP验证握手、按下、消费、RELEASE、新mode与EOF清键；错误nonce收到任何响应前被拒绝。报告artifacts/control/report.json。
- PID/创建时间仍是声明，实际加载构建和协调器描述文件未核验；测试build是假值，随机nonce不写报告。输入安装ACK不等于物理提交；服务端碰撞镜像、动态真帧、Hero旁路/恢复及三维玩法未验收。
- 下一切片为世界几何版本应用与完整MODE交接，以及原生锁三槽邮箱。详见docs/CONTROL_SLICE.md。
- 用户截图反馈dotnet.exe应用程序错误。定位为错误nonce的负向测试让InvalidDataException逃出测试main，引起Windows错误报告弹窗并令父测试等待退出超时。修复为握手拒绝分支正常关闭连接/退出，所有其它测试失败由main顶层捕获、记录简短错误并设置非零退出码；不改系统错误报告策略。父runner验证正常退出+拒绝标记+无stderr，不再将崩溃退出当作通过。修复时测试进程已被runner的finally按所属PID结束，进程扫描未见dotnet/WerFault残留；桌面工具因用户正在操作而返回USER_CONTROL，没有强行点击。

## 2026-10-20：v0.4.0-world

- 用户要求下一切片。继续双原生进程像素+逻辑桥，先完善完整几何与客体接管条件；不更改三维、原生MC玩家与DC最终显示的目标。
- World.cs/World.java新增96字节MCDW头+64字节solid AABB记录，最多4096形状；session/epoch/revision、记录区SHA256与完整blob摘要，保留小数坐标和u64。FromDc处理Y翻转与显式深度，不以整block四舍五入代替碰撞。
- World.Transfer实现≤1024字节有序分块、总量上限、重复/越界/截断/hash拒绝；失败不可复用，不暴露半份世界。尚未接入WORLD_*网络消息或能力协商，control-1仍为capabilities=1。
- ModeGate仅客体游戏线程拥有；client/server同Stamp几何确认、同frameId/nativeTick身体空间确认、帧/相机/代次和QPC新鲜度、载体准备和匹配InputInbox齐备后才安装输入。覆盖幂等提交、旧mode/帧、超时、世界修订作废、输入故障撤销与恢复失败重试。
- BridgeGeometry对真实MC26.3 AABB/VoxelShape构建形状；两个角色线程夹具得到相同回执/原生解算。Shapes.collide验证x=2.25墙允许移动1.4、落地-1、前后深度±0.95、顶棚1.95；原生形状相交验证站立合法/墙内受阻。不是实际client/server Level或Entity.move运行。
- BridgeInputBinding保存原ClientInput，接管时安装BridgeClientInput，退出先清键再恢复原引用；setter部分安装抛错可回滚，恢复失败保持RECOVERING可重试，不覆盖其它所有者。不包含DC Hero恢复。
- tools/verify_world.py包含原codec/control/TCP/SPSC回归；Python独立23组world样本，C#精确重编码并导出，Java检查24份（含C#导出）并验证分块/ModeGate，通过。报告artifacts/world/report.json。
- tools/inspect_mc_api.py --world-fixture-root artifacts/world/vectors经只读放行运行Java25原生类型夹具，通过；报告artifacts/mc-api/report.json。完整游戏字节码仍在项目外私有目录。不改JDK安全配置、不关闭校验，不安装/加载/操作游戏，不改ICEY或存档。
- 本片的几何、帧与carrier确认仍是测试输入。真实DC导出器、MC隔离世界/双侧查询替换、WORLD/MODE网络分发、DCCM载体、真实帧邮箱及实机运动尚未接入。后续工作和边界见docs/WORLD_MODE_SLICE.md。

## 2026-10-20：持续推进中的v0.5接入（尚未最终验收）

- 用户要求下一切片且无阻碍则一直推进，不在单个组件通过后停止。当前继续在工作区实现、编译和夹具验证；实机操作前准备具体可审阅包和隔离离线实验方案。
- 已新增world-1(capabilities=3，layout/schema独立)，保持旧control-1=1兼容；WorldMessages.cs、WorldCommands.java定义WORLD_BEGIN/CHUNK/END、PREPARE/COMMIT等JSON；SessionFlow维护共享收包顺序和只越过已消费/取消项的前缀ACK；GuestSession将socket解析和有界游戏线程分发分开。分块1024、总量原上限；WORLD_BEGIN/RELEASE优先撤销并取消之前尚未消费命令。
- tools/verify_pipeline.py已完成一次全回归及真实C#↔Java管线：独立reader/writer/consumer线程，几何应用回执、prepare/ready/commit、输入消费ACK及release/EOF通过。此时仍是合成帧/载体和输入sink。
- 新增Mcdn.DcProbe直接引用本机ModCore/GameProxy，已.NET10编译0警告0错误。不依赖MDK下载、不自动安装。只读导出局部实际collisions，并在后台写快照；通过IOnHeroInit/Dispose、地图UID/碰撞指针分代。不改变Hero/物理/输入/存档。
- 本机ColType静态证据：Empty=0、Plain=3、OneWay=11、Ladder=16、RollZone=65、Invisible=35、SlopeRight=512、SlopeLeft=1536。仅3/35进入solid诊断blob，其余非0编码计为unsupported；元数据eligibleForControl始终false。避免旧(cell&1)!=0把单向平台/翻滚通道误实体化。
- 正在准备Fabric真实加载模块/隔离lab入口与打包；Mixin本机0.17.5+mixin0.8.7确有INJECTORS_IN_INTERFACE_MIXINS特性，官方源码显示接口注入受其开关约束，尚须实际加载验证。未启动游戏或修改游戏安装。
- Fabric 诊断包已构建；用户确认准备自行离线启动 26.3 主菜单验证后，已通过带备份/哈希记录的脚本安装单个 mcdn-lab-probe-0.5.0.jar。安装摘要4707be392043189578f4f09ceb136cee7ccea3db85083879934fb8ad73d5ef80，previous=null。未改其它模组/启动器/存档，未自行启动游戏。当前等待新日志，不把旧日志当本次证据。
- 新增 PipelineFaultBench：消费 ACK 空洞/上限/倒退、世界能力、旧世界取消、原生 sink 跨 tick 短按、优先释放、坏流清键和线程所有权通过；verify_pipeline 完整回归及实际 TCP 再次通过。仍为替身输入/几何/帧/载体。
- 新增 tools/check_mc_load.py：核对安装哈希、实际来源、Mixin 合并与实际 tick 标记；只保存本项目标记。离线状态由用户声明，不读取账号或完整日志。实机状态与独立实验步骤见 docs/LAB_SLICE.md。
- 用户首次离线启动失败，提供 D:/MC/错误报告-2026-10-20_10.27.17.zip。只读取 crash/latest，不读含账号参数的启动脚本/启动器日志。根因 IllegalClassLoadError：FabricProbe 位于配置声明的 dev.mcdn.fabric Mixin 保留包；是本项目打包错误。
- 修复：两只注入类移至 dev.mcdn.fabric.mixin，入口及辅助类保留外部；构建使用新临时 class 输出目录，避免重命名残留。构建/安装加入包检查；原包明确被拒绝，修复包通过。
- 新增 tests/fabric/FabricTransformBench + tools/verify_fabric_transform.py。真实本机 Knot.init + Mixin 能实例化 FabricProbe，并确认 CollisionGetter/Minecraft 的注入 handler 合并；不调用游戏 main/构造器，不运行 tick/世界。Java25 自身安全配置真实路径仍需只读放行；未改安全配置。报告 artifacts/fabric-transform/report.json。修复包主菜单需用户再次离线启动验证。
- 类加载检查进一步执行实际 onInitializeClient，初始化正常、两个 handler 合并通过。已安装修复包摘要 f595c665f9e35764a0c70adb43d3cd470639e96678bb061498901d8e460f3336，与被测包相同；原错误包备份于 artifacts/backups/20261020T022957437614Z。错误归因/来源摘要写 artifacts/lab/load-failure-20261020.json，不保存启动脚本或账号参数。未调用 MC 游戏主程序，等待用户重试主菜单。
- 用户重试成功报告主菜单。实际日志10:31:42初始化和来源、collisionMixin=true/tickMixin=true、10:31:44 Render thread tick 已核验。来源路径包含本机GBK字节，修复日志检查器严格UTF8/GB18030解码后精确匹配；未用损坏字符模糊匹配。artifacts/lab/mc-load-report.json=pass。
- 新增 tools/prepare_mc_lab_profile.py，仅创建新的 MC-DC-Lab-26.3 版本目录，复制本机相同JAR+探针，独立存档/标记/manifest，不改原版本或账号；既有目标目录拒绝覆盖。已通过放行安装，逐文件摘要记录在 artifacts/lab/mc-profile-install.json。参考PCL官方ModLaunch参数逻辑，隔离键与用户已正常隔离的原实例相同。
- 实验实例配置经真实Fabric类加载预检，onInitializeClient接受manifest与目录标记，labConfigured=true，两个handler通过；这不是实验世界/物理验收。等待用户自行切换实验实例离线创建一次性MCDN-Lab世界。另确认DC的SaveRoot仅覆盖modded附加存档，不能据此断言原生存档/Steam Cloud隔离；DC启动前须解决原生File.PATH/Cloud路径，不贸然启动。
- 用户报告进入过实验世界，随后要求重新生成误删的MC-DC-Lab-26.3。检查发现原 D:/MC/愚者/懒人包/.minecraft 根目录不在原路径，当前 D:/MC/.minecraft 的版本目录为空；回收站未找到匹配的D:/MC记录，没有可保留的实验存档。未将用户报告当作已核验的世界/物理证据。
- 新增 tools/restore_mc_lab_profile.py，从项目保留的完整版本元数据恢复独立实例到 D:/MC/.minecraft/versions/MC-DC-Lab-26.3，仅创建缺失目录，存在则拒绝覆盖。由固定piston-data.mojang.com地址恢复用户原游戏JAR，size/SHA1及原SHA256 4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d全部匹配；探针仍为已验证f595c665...。所有生成文件哈希、游戏目录、隔离标记及JVM配置核验通过；旧安装记录已备份，新记录artifacts/lab/mc-profile-install.json。未读取账号、启动游戏或打开世界；PCL首次启动需补全被删的公共依赖和资源。

## 2026-10-20：v0.5 实机诊断推进

- 用户离线进入重建的 MCDN-Lab，15:12:56初始化/来源/双Mixin及15:13:03实际tick通过。原生观察持续刷新，独立gameDir及集成服务器生效。
- 先发布 kind=synthetic-mc-runtime-smoke 地板/墙，锚于实际 MC 玩家(0.5,-60,-1.5)，双侧同digest并有实际查询；不是DC地图证据。报告mc-native-query-report.json。
- 新增DC独立实验资源副本/私有存档/缓存/配置/模组目录，原save和coremod/config先zip+SHA256备份。源码新增LabSaveGuard；只在标记实验目录启用，阻断Cloud使能/读写删除/双向传输，固定原生File.PATH，并用真实原生接口写/查/读/删唯一临时文件自检。声明不接管Hero/输入/画面。
- 直接GameProxy引用在Hook委托/Nullable上因System.Private.CoreLib作用域不兼容失败；参照本机DCCM MDK GenerateGamePersudoCommand实现私有编译引用重定向。tools/dotnet/GameProxyRef只改引用副本，运行时原GameProxy SHA256 c51cf932...不变，不把绑定或游戏资源打入模组包。build_lab --dc-only构建通过。
- 初次DC隔离启动漏复制DefaultModLoader插件，报Unknown mod type，探针/保护未运行。核对PID/启动时间后停止自己的dotnet PID20076（沙箱终止权限被拒绝后经精确放行完成），不结束MC/Steam。原本地存档/配置完整性核对无新增修改；云端未独立核验，不作保证。记录dc-first-start-integrity.json。
- 修复为复制原装DefaultModLoader并通过DCCMShell自定义启动提前装入LabStartup：广播前装原生保护、所有普通模组初始化后确认必须探针。DCCM OnAfterBroadcastEvent实际为每个receiver后触发，不能当广播结束；改为事先注册int.MaxValue优先值receiver最后核验。未就绪则正常Exit(2)，不继续Boot.main、不制造未捕获异常弹窗。
- start_dc_lab --preflight正常原生加载/存档自检通过并在原始游戏入口前Exit(0)；--preflight --missing-loader-check以空插件目录重现缺失加载器并确认Exit(2)拒绝，均不进入角色场景。两份报告绑定同一包/启动配置哈希，正式实验入口要求其匹配。
- 用户第二次离线启动DC进入角色场景；guard ready/probe ready/original entry released均出现。真实会话e334a067-fcaa-45e4-892c-853a762b7ae9导出MapUid582910、epoch3/rev1，2555个solid，7格unsupported(1/33/11)。MC两侧同摘要1997970b...并有实际查询。首份证据另存dc-mc-native-query-baseline-report.json；非合成DC数据。
- DC导出锚点固定映射到本次MC静止玩家位置，保留小数/Y翻转/±2深度。eligibleForControl与physicsIsolationComplete仍false；不能由计数/onGround推断完整物理、输入或画面通过。
- 用户在实验DC移动并重开一局；有界只读记录证实同epoch revision1→7，世界epoch3→7且MapUid改变，两侧匹配应用并被查询。world-lifecycle-runtime-report.json保存实际applied_source而非把最新源误配为原生回执。当前检查新图2515形状/7格unsupported，原本地存档/配置仍零变化。
- 当前真实入口仍是文件诊断，与GuestSession TCP未整合；无生产输入接管/载体恢复/真实帧邮箱/最终DC显示。详见docs/DC_RUNTIME_SLICE.md。

## 2026-10-20：v0.6 Win32 帧邮箱组件通过

- src/native/mcdn_ipc.cpp 统一拥有三槽文件映射、发布头/每槽命名互斥、共享 Interlocked 故障位及 QPC；Java JNI/C# PInvoke 仅传私有副本。单写者/单读者固定线程调用，所有互斥等待 timeout=0。忙锁不推进已发布 frameId，槽复用核对原 frameId 后才能复制。
- abandoned mutex 获得所有权后先停用共享会话再释放；坏帧解码同样停用。同 session 文件不能重开，须新建随机 session。目录/文件/命名互斥使用实际 TokenUser SID 与 SYSTEM DACL，不变更系统安全策略。
- tools/build_mailbox.py 使用本机 MSVC14.44.35207、SDK10.0.26100.0、Java25 javac。Java25 运行时没有 JNI include，显式 --jni-home D:/Jdk/jdk-21；构建记录两个路径与头文件哈希，Java25实际加载/调用验证。未下载依赖。
- tools/verify_mailbox.py 五项独立进程用例通过：忙头/三槽均忙、捕获后槽复用、5..2000 最新帧压力与完整像素/姿态/QPC核验、u64最大值和重复拒绝；C#写/Java读；损坏像素CRC拒绝；Java持槽锁半写退出；Java持发布头锁半写退出。两种退出均正常System.exit(0)，C#检测真实WAIT_ABANDONED，没有故意触发未捕获异常/崩溃弹窗。
- 初次Java运行被沙箱阻止读取自带java.security；仅放行本地测试命令后运行，未改安全配置。测试修正Windows正常进程退出的TCP reset识别，随后独立检查内核锁和双方退出码。
- 证据 artifacts/mailbox/report.json，源码/夹具/DLL摘要绑定。只有96x64合成RGBA，没有原生GPU帧、DC纹理或玩法延迟结论。当前两游戏仍保留v0.5探针，没有替换运行中的包或改变输入。见 docs/FRAME_MAILBOX_SLICE.md。

## 2026-10-20：原生 GPU 帧诊断接入（待实机验收）

- 延续用户无阻碍持续推进的授权，读取本机25个渲染相关类型。MC26.3使用renderpearl API，MainTarget=RGBA8_UNORM；GameRenderer.render后由Minecraft提交命令。Screenshot.takeScreenshot使用GPU拷贝+fenced callback；完整反汇编仍在工作区外，仅API签名/摘要在artifacts/render-api/report.json。
- 新增独立src/frameprobe，最大12次/至少2秒间隔/单GPU在途；主渲染完成时冻结原生tick、partial foot、CameraRenderState及矩阵，GPU返回检查对象/目标身份尺寸与时限；后台写PNG和元数据。不修改现有碰撞探针/计数、输入、焦点或存档。
- 全场景含HUD，当前MC视觉不含导入DC网格。明确playerLayer=false / bridgeContextPaired=false / eligibleForControl=false，不把完整场景伪装MCDF角色层，也不声称正式世界/相机代次已配对。正式三维世界色彩/深度通道与DC内显示另须接入。
- build_frame_probe编译通过，真实Knot/Mixin初始化与GameRenderer钩子合并通过，无游戏main/client/GPU调用；报告artifacts/frame-probe/build-report.json。原MC字段screen在26.3不存在，按实际API使用isPaused过滤；编译只排除第三方缺注解classfile lint，源警告仍为错误。
- 新增install_frame_probe，单个新JAR CREATE_NEW，固定已验证游戏/旧探针/新包/变换预检哈希。第一次备份因MC session.lock读锁失败，目标未创建；用户确认正常退出后，完整备份实验存档并安装成功。备份20261020T082244346679Z，包SHA256 8a5c619e4fb8cf7ef2245755b53bc559d579eb9f291a6fd1f7ba2017eaec74e7。旧探针不变，不自动启动游戏。
- 用户已获离线重开同一实验世界、MC前台未暂停约30秒的验证步骤。check_frame_probe只看自身标记/产物，要求实际来源、PNG摘要尺寸、非单色、冻结有限姿态/矩阵及推进tick；仍需目视实际图像。当前仅见新初始化/渲染钩子标记，尚无GPU帧证据。详见docs/NATIVE_FRAME_PROBE.md。
- 首次GPU实机尝试：新包真实初始化/渲染hook生效，原生世界/玩家tick推进，但没有采集。定位为本项目错误地把GameRenderState.readyForLevelRendering用作门控；扫描全JAR只有定义类包含该字段名，没有普通写入，字段一直为false。移除此条件，改用原生GameRenderer同样读取的shouldRenderLevel。诊断保存no-capture-diagnosis.json；修正版编译和真实Knot变换通过，SHA256 4f480434806ede592ba5cd8d8ec134628b49705e14fbd87310ad692761232f40，待用户再次退出后按旧清单哈希备份/替换。没有热替换运行中代码。
- 首次移除未使用字段后的实机仍无帧。对用户已离线启动、PID53968/启动时间16:28:26匹配的MC做一次只读Java诊断：不注册transformer，字段读取提交Render thread；实际门控均通过，但目标2560×1494没有满足≤1024的整数下采样因子。live-gates.properties保存原值。
- 临时调用游戏Window.setWindowed后恢复，最大化状态保持了旧实际尺寸，未产帧。随后从桌面识别MC HWND395300，校验PID/启动时间后原生ShowWindowAsync还原最大化、SetWindowPos缩小，5秒取得3张GPU帧，finally恢复原最大化。基线native-baseline-report.json；已打开frame-3.png确认天空/草地/手/HUD及方向正常，不是桌面截图。
- 用户明确要求精确测试由代理控制电脑。后续无需用户重复手动退出/重启。已目视确认PCL离线登录、选中MC-DC-Lab-26.3；对精确MC窗口WM_CLOSE正常保存退出，备份20261020T084546680906Z后安装任意尺寸修正版f212d225c6716b7af6f4f2a719acf7bd3532d2be19e54b56ac3fabdec51c166d。旧Java诊断代理随进程退出结束，没有HotSwap或游戏字节码改写。
- 修正版完整有界GPU读回，后台NativeImage.resizeSubRectTo/STB CPU线性缩放；FrameSizeBench 2560×1494等12项边界回归和真实Knot变换通过。代理通过同一离线PCL正常启动并进入MCDN-Lab，最大化复现2560×1494，12张真实图像输出1024×598全部核验通过、目视确认。当前runtime-report.json；源目录e04726bb-80bb-49e1-837f-0d49f84a9603。源图≤3840×2160像素预算、单GPU在途、待写1份；最多12次，不做性能承诺。
- check_dc_lab再次通过，2515形状/7未支持，原本地存档配置变化0。MC场景仍是原生超平坦视觉，不是DC网格；fullScene=true/playerLayer=false/bridgeContextPaired=false/eligibleForControl=false，未写MCDF邮箱、未做DC绘制或输入接管。
- 已新增tools/dotnet/RenderSymbols和inspect_dc_render_api，只用Cecil读取GameProxy元数据，不加载VM。确认dc.hxd.Pixels.Class.alloc、PixelFormat.RGBA嵌套构造、Texture.Class.fromPixels/uploadPixels、Tile.Class.fromTexture、Bitmap及pr.Game.Class.ME/hud/root的本机绑定，继续DC原生纹理显示诊断。

## 2026-10-20：DC原生纹理显示切片（构建/预检完成，待角色场景与目视验收）

- 继续用户授权的精确桌面测试。新增Mcdn.DcFrameProbe独立附加模组，对本机绑定编译通过；Pixels.Class.alloc+PixelFormat.RGBA嵌套枚举构造，Texture.Class.fromPixels/uploadPixels，Tile.Class.fromTexture，Bitmap挂到pr.Game.Class.ME.hud.root。首次编译Core.InMainThread为internal不可访问，改为捕获初始化线程并在帧回调检查同一managed thread，不使用反射越过Core权限。
- stage_dc_frames逐张核对原生MC采集PNG与报告SHA，再转换top-down RGBA、固定12帧记录回放playlist。不是实时通道，不借用MCDF player flag。worker长度有界/原始数据hash验证/唯一pending，原生游戏线程真实上传后才确认并发下一张，所有文件IO与回执落盘在后台。Hero dispose清理自有Bitmap/Texture，退出仅取消worker，避免VM关闭后原生调用。
- 用户原私有DC PID56212/启动15:37:50/HWND2295946精确匹配，WM_CLOSE正常退出。prepare_dc_lab --include-frame-probe备份原save/config与实验save到20261020T090112412513Z-dc-originals，新增附加包、原探针/守卫不变，spec绑定两个包及playlist SHA。
- 正常原生preflight同时确认saveguard、FrameProbe与原Probe初始化，原游戏入口前Exit0；缺DefaultModLoader的负测在原入口前Exit2拒绝，两者通过并匹配同spec。正式私有实例已启动PID52908，17:02:11 guard/frame-probe/base-probe/original-entry-release均出现。当前无角色场景上传证据，check_dc_frames输出pending 0，不能声称DC已显示。
- 桌面工具持续返回USER_CONTROL，暂缓键鼠而继续文件/日志检查；已请求用户区分真实键鼠占用与MC鼠标回中误报。无自动审批拒绝，不以其它输入方式绕过人工占用判断。

## 2026-10-20 晚间：代理操作与DC原生记录帧显示验收

- 用户确认放开键鼠并再次要求代理操作；ControlStatus恢复ready，旧MC/DC均已退出。目视Steam菜单发现当前在线，正常点击进入离线模式，随后只启动带既有隔离守卫的项目DC实例。没有读取账号令牌/启动命令行。
- 实际进入角色场景，首版捕获HashLink异常`Cannot convert from RGBA to RGBA`并停用诊断，DC未崩溃。DCCM公开包装器CreateEnumInstance会分配新对象，结合实际错误推断同名RGBA的身份比较问题。改为读取Texture.Class.nativeFormat并验证RGBA，同时增加原生字节指针非零检查；编译通过。
- 新增dc_lab_window.py，PID+创建时间+程序路径+唯一窗口校验，WM_CLOSE正常退出；仅前台匹配时发送一次Esc扫描码或保存窗口截图。MCP点击可用于DC菜单，普通快捷键没有触发SDL确认，因此改用受限扫描码。没有抢占人工输入保护。
- replace_dc_frame_probe.py先校验旧包、新构建来源/绑定/文件集合，备份实验存档、旧包/spec后只替换自有包，保留地图原点/守卫。备份20261020T121428005072Z-dc-frame-replace。首次发现private_game_files也固定了自有DLL，启动检查正确拒绝不一致；修复替换器同步更新两份摘要，未放宽检查。
- 正常/缺失加载器原生预检重新通过Exit0/Exit2。修正版DLL SHA256 cdcef627bfc7d413ca89735fa6b964c198f995cdf2690d14883b5f76dba26f7a；正式私有DC PID37492，创建20:15:36，20:16:13–25完成12帧原生纹理上传，20:16:26回放完成。
- 实际目视MC天空/云/草地/右手/物品栏在DC角色场景左上角呈现，颜色方向正常。visible-1792498611472977000.png与单独visible-report.json绑定上传报告/spec/playlist。小预览未独立分辨每帧差异，连续推进由12条原生回执证明。不是实时通道或玩家接管。
- 代理Esc进入暂停，点击退出游戏并确认返回标题，缩略图消失，日志无清理异常；visible-1792498807364588300.png。未测GPU分配数量。DC当前停在标题画面，MC本轮未重开。
- 历史17:01原存档基线与晚间状态有旧自动备份缺失及18:47/19:52已出现的用户文件差异，不把跨会话变化归因于本轮、不恢复用户文件、不沿用零变化结论。记录差异并创建新只读备份artifacts/backups/20261020-evening-original-baseline；之后标题清理测试核对该基线变化0。隔离守卫仍每次通过。下一步为独立world-color实时通道/失效处理，MCDF仍仅player/effects。

## 2026-10-20：MCWC原生实时场景诊断（626帧验收）

- 按用户下一切片指令继续代理操作，先写LIVE_COLOR_SLICE合约。新增MCWC384字节不可变帧：UUID/原生流代次/帧号、源尺寸、RGBA/flags7、冻结脚底/相机/矩阵、请求/读回完成QPC和CRC。独立于MCDF角色帧，无DC world/mode/camera配对或MODE授权。
- NativeMailbox/FrameMailbox与原生同步算法新增类型入口，MCWC用MCDM0.2/channel1与独立锁名；旧MCDM0.1/MCDF保持兼容。MSVC/JDK25构建通过，新DLL SHA256 3d155cff02593abd0d7e6438104688a9d1d66bac705771a7110eec288de3f57f。旧五项真实跨进程故障测试全过，基线DLL/报告保留mailbox/v0.6-baseline。33组MCWC黄金/坏包两语言通过、20帧真实JNI→映射→C#一致，类型混读拒绝。
- MC live模式单GPU请求、单待处理NativeImage，冻结同次原生提取状态与QPC，独立worker最大边512缩放并发布有类型映射；最长180秒、目标5fps，另写首张原生PNG/有界回执。DC独立Thread拥有邮箱，解码/CRC/身份/帧序/流代次/时钟/新鲜度校验后投递一个不可变像素快照，游戏线程上传原生Texture/HUD，超1.5秒撤图。
- 两端原生代码保持原绑定和存档守卫。DC把已测邮箱/codec源码链接进自有附加包，基础探针/Protocol DLL不变。MC真实Knot变换、尺寸夹具及DC源警告为错误的编译通过。替换前两游戏都正常关闭，备份实验存档/选项/旧自有包。
- 首次映射在codexsandboxoffline SID1003创建，私有ACL正确阻止桌面用户SID1001访问。停止自有helper，用桌面用户权限重新创建，没有放宽DACL。初始沙箱会话feb77fd1-5d78-45a2-8589-1c685e7a97c5未进入游戏。
- 第一实机会话bd5c729a-5cc2-4675-a7d3-adbd13c09846接通实时GPU→DC数百帧；Windows文件读者禁止delete sharing导致producer-latest原子替换AccessDenied而停用，DC按时清理。保留该次日志/身份/回执。改为append-only JSONL权威回执，可选latest快照的占用不终止数据流。
- 修正版MC JAR b5d0c934257bf38727277743148e777734a35f541ffe93662717aa2ff2ae69d1；DC DLL 0c9f8a377b4c58e6f2ab736083f60bc0a7918c5db5dce0f952befbb7531ea843。替换备份DC 20261020T124423127306Z-dc-frame-replace、MC 20261020T124425393266Z，session配置备份20261020T124450971551Z-live-color-config；相应DC正负预检Exit0/Exit2重新通过。
- 目视PCL离线登录/正确实例，Steam离线标记。最终会话9dcf6a08-707a-469f-b5dd-51a2df8ff201，DC PID24996/创建20:45:18，MC PID34412/创建20:46:38；进入MCDN-Lab与DC实验角色场景。普通SetForegroundWindow和App名称匹配不总能切DC，临时最小化/恢复MC会引起Surface暂停；最终通过Win开始菜单释放MC锁定再点DC任务栏，MC保持后台渲染，不把最小化当正常后台路径。
- 626张发布与626张原生上传逐帧UUID/原生流代次/tick/尺寸/像素SHA/完整帧SHA/QPC配对，626不同像素SHA；512×299首张NativeImage PNG解码像素SHA与传输完全相同。DC前台PID24996的4个样本，两端帧号587→597→606→616。实际DC左上角MC天空/云/草地/右手/HUD颜色方向正常，仍是MC原生超平坦视觉，不是DC三维网格。
- 实机故障注入：同时用Win32 CreateFile禁止两份latest快照的delete sharing，保持5秒；快照帧号不变而producer563→587、consumer562→587，证明修复后帧流不因观察工具占用停止。随后明确写stop-producer，两游戏保持存活；约1.4896444秒后观察到DC清理日志，截图预览消失。软件捕获请求至原生上传返回中位67.08345ms、最大212.2922ms，不宣称输入/present/光子延迟。
- check_live_color自动报告live-native-upload-pass-visual-pending，单独visible-report绑定目视截图/故障注入/断流/运行摘要。真实2515形状/7未支持仍在MC双侧匹配被查询；晚间新原存档基线变化0。旧17:01基线的4项跨会话差异继续保留，不归因于本轮或恢复用户文件。
- 两游戏已按记录PID/创建时间/路径WM_CLOSE正常保存退出。配置清理备份20261020T125436335235Z-live-color-config，删除仅自有摘要匹配的MC会话指针、解除DC两项环境；实验pauseOnLostFocus:false保留用于未来后台桥接。helper停止，普通实验模式正负预检再次通过。verify_live_archive在已关闭游戏后独立通过626帧的日志/包/可见证据摘要核验。
- 下一片应继续正式会话/能力与上下文配对、原生MC玩家操控/物理和DC三维几何视觉。当前没有输入接管、Hero旁路/F7恢复、重连/切关实时画面、深度合成或原生战斗验收，不将HUD诊断预览作为最终架构完成。

## 2026-10-20：独立原生玩家物理切片（实机待执行）

- 新增PhysicsProbe、客户端/服务器tick与精确玩家碰撞查询注入，以及原生BlockDisplay访问器。合成MCDW夹具含地板、X=2.25小数墙、Y=202.5低顶及深度边界；BlockDisplay只显示相同AABB。原生LocalPlayer/ServerPlayer负责运动，没有逐tick位置覆写。
- 使用现有BridgeClientInput/InputInbox/BridgeInputBinding执行200tick有界本地脚本，记录双侧实际位置/速度/身体范围/原生tick/消费序号；停供输入测试250ms租约及原输入引用恢复，结束还原服务器位置/模式并移除自有显示实体。仅本地schema peer，不作DC身份、MODE或完整世界隔离的声明。
- build_physics_probe.py对实际26.3 JAR以Java25编译，并在真实Knot初始化后验证客户端、服务器、碰撞与显示访问器的变换。组合包只复用已有自有GPU诊断编译类，不加载旧地图探针。当前JAR df4aac13049d3c235e0db5191703e456fc55a152cb1a88fb8ddc4a80fe735f41；23份源文件摘要绑定构建报告。
- 创建新实例MC-DC-Physics-26.3，不合并原实例或复制旧世界。配置来源备份20261020T133911794675Z-new-physics-profile；随后自有包替换备份20261020T134401332075Z-physics-own-replace。原MC-DC-Lab与DC包未替换。新增check_native_physics.py核验实际轨迹、墙/低顶/跳跃、消费170条输入、租约清键与位置/模式/对象恢复；Python语法检查通过，尚未执行实机验收器。
- 桌面ControlStatus连续返回user，Snapshot拒绝USER_CONTROL；当前没有运行MC/DC，已请求用户暂时放开键鼠且未绕过占用保护。新世界MCDN-Physics尚不存在，无实机通过结论；等待桌面可用后继续已授权的离线验证。

## 2026-10-20 晚间：原生玩家物理实机验收通过

- 用户确认放开键鼠后ControlStatus恢复ready，代理通过PCL目视离线模式选择新MC-DC-Physics-26.3实例；未读取启动命令或账号。单人建世界UI的clear未清空默认中文名称，生成新的世界MCDN-Physics，严格存档路径检查正确拒绝。原生WM_CLOSE正常退出后备份全部新测试存档，才将该目录改为MCDN-Physics；显示名称保留。恢复备份20261020T141104526657Z-physics-world-name/world-before.zip，未动其它实例。
- 初次MCP快捷键Alt+F4没有关闭MC，随后复核进程仍在，未修改存档；dc_lab_window.py新增--physics，沿用PID/创建时间/程序路径/唯一窗口检查发送WM_CLOSE，确认正常退出后才修改/替换。原生进程对象可能仍被启动器持有，归档器用GetExitCodeProcess=0核实退出，不能把OpenProcess成功当成游戏仍在运行。
- 70093908会话读取到真实原生玩家health0，建场及返回teleport均拒绝；用户指出此前被史莱姆击杀。新增活着且站稳的客户端/服务器检查，限制恢复重试，不修改生命值。按用户要求在严格核验的唯一测试存档主线程设置PEACEFUL，再等待原生重生。修正版安装前均备份实验存档与旧自有包。
- 2a536eae会话成功建场，但原生F3显示(.5,200.5,.5)未落地。实际26.3 CollisionGetter.noBlockCollision仅检查返回形状是否非空，要求上游已按查询AABB过滤；全量形状不能直接作为该查询结果。新增BridgeGeometry.intersecting及物理Mixin传入query bounds。真实原生默认方法回归覆盖站立接触、远处空气和墙体重叠；编译/Knot注入预检通过。旧Fabric地图探针未替换，不把此前查询证据升级为运动证据。
- 7f3f5ce9实际运动、墙/两次跳跃与输入租约通过，但恢复点来自中断实验遗留的空中位置，客户端返回后继续下落，验收器正确拒绝。保留轨迹/diagnosis，不放宽恢复阈值；改为客户端连续10tick着地、服务器活着且onGround后才保存原生返回点。bcb04e49修正版完整通过，原生退出0并独立归档。
- 最终把运行时存档realpath磁盘访问移到文件worker，客户端等待已核验身份；服务器只做规范路径比较，worker不触碰游戏对象。备份20261020T144534994976Z-physics-own-replace/lab-before.zip后替换自有包，最终JAR dd15b93616b9a1d02172bfd64c49c806c7898a356091e212d13467cd05c8742e。实际加载器/原生query预检通过后再跑实机。
- 最终会话a7415741-533b-42ba-87ed-9983cb904177，PID20392；真实客户端200/集成服务器199采样，夹具查询1098/767。两侧墙接触bodyMaxX=2.25、脚底自由峰值201.25220334025371/低顶200.70000004768372、落地Y200一致，角色不是flying/noPhysics，原世界下方是空气、health20。170条输入实际消费，停供后input-lease-expired、held0及原KeyboardInput引用恢复；相机恢复FIRST_PERSON，原生返回(1.5,-60,4.5)/survival，客户端10tick后站稳满血。5个本次BlockDisplay调用discard并清空本次列表；0是该列表计数，不作历史遗留实体的全世界扫描声明。
- 最终原生GPU frame3=playerTick84，与client phase40脚底xyz精确匹配。目视原生第三人称玩家在石质通道、金色小数墙前，低顶玻璃边可见；PNG/JSON及配对说明保存evidence/fixture-gpu-3.*、render-evidence.json。前版bcb04e49的辅助GPU在死亡等待阶段采集，未当作运动证据。
- 最终恢复窗口截图visible-1792507781716591900.png，随后WM_CLOSE正常退出码0。archive_native_physics.py保存真实来源/和平/脚本/恢复标记、自有JAR、23源文件与工具、夹具和摘要；check_native_physics.py --archive在无需当前安装情况下完整复核通过。修复归档检查循环变量遮蔽导致的报告摘要差异，未改原始轨迹。原MC两只自有JAR及DC frame DLL最终摘要仍为f595c6/b5d0c9/0c9f8a，与切片开始一致。
- 本片仅合成MCDW固体场景和本地脚本输入，不是DC输入、真实DC地图运动、生产ModeGate、完整世界隔离、Hero旁路/F7或三维DC视觉。中断/卸载完整恢复仍需另验；下一片按正式会话与实际DC几何/输入接入推进。
