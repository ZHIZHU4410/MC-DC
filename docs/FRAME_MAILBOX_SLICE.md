# v0.6：原生跨进程帧邮箱

2026-10-20：Win64 文件映射和命名互斥的组件验证通过。Java25 JNI 写者与 .NET10 P/Invoke 读者运行于不同进程，输入为 96×64 合成 RGBA。没有调用游戏主程序、GPU 采集、窗口嵌入或 DC 绘制；游戏中仍运行 v0.5 诊断包，控制关闭。

## 实现

`src/native/mcdn_ipc.cpp` 统一拥有映射及锁；Java `NativeMailbox` 和 C# `FrameMailbox` 只传入/取回私有副本，不混用 Java/C# 的跨进程内存模型。双方加载前校验 DLL SHA256 与 ABI=1，句柄仅供创建它的线程使用。创建/打开文件、DLL 加载与目录准备属于启动阶段，不能放进逐帧游戏回调。

当前调用契约为一个写者、一个读者，各自固定拥有线程；协调器须保证角色唯一性。DLL 尚未提供角色认证或完整进程身份绑定，不可把它独立当作正式协调器。已有同名文件/命名对象的创建请求拒绝覆盖，读端检验文件大小、会话和布局。

每次锁均为 `WaitForSingleObject(...,0)`，忙则返回没有新帧，不推进已发布序号。写者跳过当前发布槽，在空闲槽锁内复制完整 MCDF，释放后短锁发布索引与无符号 u64 frameId。读者先取发布快照，再尝试槽锁，确认期望 frameId 未被复用后复制；托管完整布局和像素 CRC 校验在锁外进行。

遇到 `WAIT_ABANDONED` 时，先设置共享故障位，再释放操作系统授予的互斥所有权；当前读取失败，同一映射拒绝重新打开。完整帧解码失败也设置共享故障位。恢复要求协调器新建随机 session 和文件，不能把可能半写的槽重新标为有效。

目录及文件使用当前进程实际 TokenUser SID 与 SYSTEM 的保护 DACL；目录子项继承该权限。互斥对象使用相同用户权限，命名空间为 `Local\MCDN_<RFC UUID hex>_*`。不变更系统权限或游戏进程权限。

## MCDM 映射头

以下布局版本为 0.1，固定 64 字节；UUID 为 RFC 网络字节序，其余整数 little-endian。后接三个相同容量槽，每槽为既有 256 字节 MCDF 头及 RGBA 数据；slotBytes 上限为 256+1024×1024×4。未使用槽尾没有帧语义。

| 偏移 | 类型 | 含义 |
|---:|---|---|
| 0 | bytes[4] | MCDM |
| 4 / 6 | u16 / u16 | major=0 / minor=1 |
| 8 / 12 | u32 / u32 | headerBytes=64 / slotBytes |
| 16 | bytes[16] | sessionId |
| 32 / 36 | u32 / u32 | slotCount=3 / publishedSlot；初始 UINT32_MAX |
| 40 | u64 | publishedFrameId；初始 0，实际帧从非零开始 |
| 48 | 对齐 Win32 LONG | 故障位；仅由 DLL Interlocked 访问，0 正常、1 停用 |
| 52 / 56 | u32 / u64 | 保留，必须为 0 |

MCDF 中的脚底姿态、nativeTick、代次和像素保持一份不可变快照；邮箱不负责证明这些数据来自同次真实渲染。该证明属于下一切片的采集适配。

## 复现和证据

使用本机 MSVC 14.44.35207、Windows SDK 10.0.26100.0、.NET10。Java 类由 Microsoft25.0.1 编译并运行；该运行时缺少 include，显式使用本机完整 JDK21 的 `jni.h`/`jni_md.h`，只调用既有 JNI 接口，Java25 实际加载调用通过。JNI 接口表和线程局部约束参见 [Oracle JNI design](https://docs.oracle.com/en/java/javase/25/docs/specs/jni/design.html)。构建报告记录两套路径、头文件及代码 SHA256，不修改 JDK。

```powershell
python tools/verify_mailbox.py --java-home 'C:\Users\10113\AppData\Roaming\.minecraft\runtime\java-runtime-epsilon' --jni-home 'D:\Jdk\jdk-21'
```

沙箱曾阻止 Java25 读取自身 java.security；本地测试在只读放行后完成，没有改安全配置。Windows 子进程正常退出可能向测试 TCP 连接发出 reset；测试接受这个特定断开，再独立验证实际 abandoned mutex，并由 Python 核对双方正常退出码。

`artifacts/mailbox/report.json` 绑定 DLL、源码、头文件与帧夹具摘要，五种实际跨进程场景均通过：

1. 发布头忙、三个槽均忙时不发布；捕获后槽复用拒绝旧帧；5–2000 连续写入，读端允许跳帧但逐帧核验全部像素、姿态、时钟和单调序号；最后验证 u64 最大帧号及重复拒绝。
2. C# 发布、Java JNI 读取与重复拒绝，覆盖反方向原生入口。
3. 故意损坏像素后释放锁；CRC 解码拒绝且共享会话停用。
4. Java 持槽锁修改部分像素后正常退出，不解锁；C# 发现 abandoned 后拒绝读取及旧会话重开。
5. Java 持发布头锁修改索引后正常退出；C# 在使用该头之前拒绝并停用旧会话。

忙锁记录只是该次测试耗时，不是游戏帧率或延迟结果；尚未测满分辨率、GPU 等待、动态纹理或真实玩法。诊断 lock/corrupt 导出仅供这些测试，游戏适配不得调用。

## 接下来

核对本机 MC26.3 的渲染完成点、异步纹理读回和准确相机/玩家姿态；为每个 GPU 请求冻结上下文，返回时拒绝旧世界/相机代次。随后在 DC 游戏线程上传动态纹理并绘制，完成真实帧证据后再讨论控制门控。不得用桌面截图、独立 MC 窗口或合成图替代这一步。
