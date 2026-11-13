# Simulate Robot 第一阶段工程报告

**阶段：Webots R2025a + e-puck 真实运行 Demo**
**日期：2026-11-02**
**状态：完成（12/12 验收项通过）**

---

## 目录

1. [摘要](#1-摘要)
2. [验收清单](#2-验收清单)
3. [环境与安装](#3-环境与安装)
4. [WSL2 审计与网络](#4-wsl2-审计与网络)
5. [Webots 与 Python 控制器验证](#5-webots-与-python-控制器验证)
6. [Demo 架构与原理](#6-demo-架构与原理)
7. [传感器校准与实测结果](#7-传感器校准与实测结果)
8. [如何复现](#8-如何复现)
9. [目录与关键文件](#9-目录与关键文件)
10. [测试与回归](#10-测试与回归)
11. [问题与根因分析](#11-问题与根因分析)
12. [当前边界与风险](#12-当前边界与风险)
13. [下一阶段建议](#13-下一阶段建议)
14. [附录：哈希与路径](#14-附录哈希与路径)

---

## 1. 摘要

本阶段完成了从开发环境搭建到第一个真正运行的机器人 Demo：

- 在 Windows 原生环境安装官方 Webots R2025a。
- 在 WSL2 Ubuntu 24.04 中保留原有 Python 逻辑和测试。
- 使用官方 e-puck 模型和 Python 控制器，在 3D 场景中真实前进、读取距离传感器、在障碍前停车。
- Demo 可区分 `reached`、`blocked`、`stopped`、`timeout`、`error` 五种状态。
- 所有结果均来自实际运行日志和 Supervisor 真实位姿，不是静态代码推断。

核心数据：

| 场景 | 控制器结果 | Supervisor 真实位置 |
|---|---|---|
| 无障碍 | `reached traveled=0.770m` | x ≈ 0.7526 m（目标 0.8 m） |
| 有障碍 | `blocked front=134.7 traveled=0.338m` | x ≈ 0.3302 m（障碍物中心 0.45 m，约 24 mm 间隙） |

---

## 2. 验收清单

| 编号 | 验收项 | 结果 | 证据 |
|---|---|---|---|
| 1 | Webots R2025a 正常运行 | 通过 | `--version`、`--sysinfo`、实际仿真 |
| 2 | 官方 e-puck 示例可启动 | 通过 | 官方 C 控制器 `e-puck.exe` 启动 |
| 3 | Python 控制器正常运行 | 通过 | Python 3.12.10 导入 API，创建 `Robot()` |
| 4 | WSL2 开发环境审计 | 通过 | 网络、Python、Git、GPU、文件系统审计 |
| 5 | WSL 代理问题修复或明确诊断 | 通过 | localhost 代理不可达属 NAT 正常现象；直连可用，未改配置 |
| 6 | 原有 Python 测试无回归 | 通过 | Linux `unittest` 7/7 |
| 7 | e-puck 通过 Python 前进和停止 | 通过 | 实际移动 0.77 m，轮速 4.0 rad/s |
| 8 | 读取距离传感器 | 通过 | 36 个设备；`ps0`–`ps7` 实测 |
| 9 | 识别前方障碍并安全停止 | 通过 | 障碍前约 24 mm 停车 |
| 10 | 区分五种任务状态 | 通过 | 五种状态均有真实运行日志 |
| 11 | 可重复运行的 Demo | 通过 | `run_demo.ps1`，25 秒自动退出 |
| 12 | 清晰的项目文档和操作说明 | 通过 | 两份 README + `docs/webots_demo.md` |

---

## 3. 环境与安装

### 3.1 硬件与系统

| 项目 | 配置 |
|---|---|
| 操作系统 | Windows 11 Home 25H2，Build 26200 |
| CPU | Intel Core i7-14650HX |
| GPU | NVIDIA RTX 4070 Laptop |
| 内存 | 32 GB |
| 磁盘 | 1 TB SSD |
| WSL | WSL 3.0.3.0 |
| Linux | Ubuntu 24.04.5 LTS (Noble)，kernel 6.18.54.1，systemd |
| Linux 用户 | `airpen` |
| Linux 项目 | `/home/airpen/projects/simulate-robot` |
| Windows Webots 项目 | `D:\A.me\Simulate robot\webots` |

### 3.2 安装项

| 软件 | 版本/路径 | 说明 |
|---|---|---|
| Webots | R2025a，`C:\Program Files\Webots` | 官方 GitHub Release 安装包 |
| Windows Python | 3.12.10，`C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe` | 控制器实际解释器 |
| WSL Python | 3.12.3，项目 `.venv` | Linux 逻辑与测试 |
| Git | WSL 内已安装 | 项目已初始化，尚无首个 commit |

### 3.3 安装包校验

| 文件 | 大小 | SHA256 |
|---|---|---|
| `wsl.3.0.3.0.x64.msi` | 367,575,040 B | `AE977286974255BD26BF925F00F40F5692C6B2084155CBC0563C09AEA091F211` |
| `ubuntu-24.04.5-wsl-amd64.wsl` | 388,975,696 B | `BB415D824822C4B878125729AF451A5D18FB13D1CF5CBED9A7393AD64AC6039E` |
| `webots-R2025a_setup.exe` | 262,879,830 B | `9E326A54C104FC5FC88121E26014A409D1E35F0BBF30E23F3A712E7F842B08E7` |

Webots 安装包来自官方 GitHub Release，但 **没有 Authenticode 签名**；来源与 SHA256 已记录，作为已知风险保留。

---

## 4. WSL2 审计与网络

### 4.1 审计结论

- WSL 使用 NAT 网络，DNS 指向 `10.255.255.254`。
- 存在 `198.18.0.0/15` fake-IP 段。
- Windows 代理为 `127.0.0.1:7897`（verge-mihomo）。
- WSL 内不能把 `127.0.0.1:7897` 当作 Windows 代理直接使用；这是 NAT 下的正常现象。
- **GitHub HTTPS、PyPI、Ubuntu 软件源直连可用**，因此没有修改 WSL 代理、Windows 代理、DNS 或安全配置。
- WSL 侧未安装 CUDA，未做 GPU 计算验证；本项目当前不需要 CUDA。
- Windows 侧 Webots 已确认 RTX 4070 和 OpenGL 4.6 可用。

### 4.2 结论

WSL 网络没有被“修复”，因为没有发现需要修复的实际故障。代理 localhost 警告是环境现象，不是阻塞项；直连已经满足 GitHub、PyPI、apt 的需求。

---

## 5. Webots 与 Python 控制器验证

### 5.1 官方 e-puck 示例

官方世界：

```text
C:\Program Files\Webots\projects\robots\gctronic\e-puck\worlds\e-puck.wbt
```

使用官方 C 控制器 `e-puck` 启动，确认 `e-puck.exe` 进程运行，说明 Webots 仿真、场景和控制器机制正常。

### 5.2 Python 控制器

将官方世界复制到项目内，仅把控制器改为 `probe`，运行后确认：

```text
PYTHON: 3.12.10 C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe
PROBE: Webots import OK
PROBE: Robot created
PROBE: timestep=32
PROBE: devices=36
```

设备列表：

```text
0 left wheel motor
1 left wheel sensor
2 right wheel motor
3 right wheel sensor
4 ps0
5 ps1
6 ps2
7 ps3
8 ps4
9 ps5
10 ps6
11 ps7
12 ls0 ... 19 ls7
20 camera
21 led0 ... 30 led9
31 accelerometer
32 gyro
33 receiver
34 emitter
35 speaker
```

结论：Python 3.12、Webots R2025a、e-puck 设备 API 完全可用。

---

## 6. Demo 架构与原理

### 6.1 两层结构

```text
Linux（权威逻辑）
src/robot.py
  Point / World / Command / Result
  parse_command()
  Robot.move_to()
        │
        │ 字节级复制
        ▼
Windows（3D 适配）
controllers/robot_controller/logic/robot.py
        │
        ▼
controllers/robot_controller/robot_controller.py
  只负责 Webots 设备、传感器和 step 循环
```

3D 层没有复制命令解析逻辑，避免两套代码漂移。

### 6.2 世界与坐标

- 场地：3.0 m × 3.0 m `RectangleArena`。
- 机器人：官方 `E-puck`。
- 目标标记：(0.8, 0.02, 0)，半径 6 cm。
- 障碍物中心：(0.45, 0.05, 0)，尺寸 0.12 m × 0.10 m × 0.12 m。

关键：**这台 e-puck 的前进方向是 +X**，不是常见的 −Z 假设。因此 2D 逻辑中的 `y` 映射到 Webots 的 `+X`。

### 6.3 控制循环

```python
while robot.step(32) != -1:
    # 1. 轮式里程计
    traveled += |Δleft|  * 0.0205 / 2
    traveled += |Δright| * 0.0205 / 2

    # 2. 前方距离
    front = max(ps0.getValue(), ps7.getValue())

    # 3. 状态判定
    if front > 120:
        stop(); return "blocked"
    if traveled >= 0.8 - 0.03:
        stop(); return "reached"
    if robot.getTime() > 20.0:
        stop(); return "timeout"

    # 4. 前进
    left_motor.setVelocity(4.0)
    right_motor.setVelocity(4.0)
```

线速度：

```text
4.0 rad/s × 0.0205 m = 0.082 m/s
```

走 0.8 m 约 9.8 秒。

### 6.4 状态优先级

```text
blocked  >  reached  >  timeout
```

障碍优先，避免为了“到达”而穿过障碍。

### 6.5 Supervisor

`session_supervisor.py` 使用 `Robot { supervisor TRUE }`：

- 记录机器人真实位姿。
- 记录障碍物真实位置。
- 25 秒后调用 `simulationQuit(0)`，让每次 Demo 自动结束。

单独写 `Supervisor { ... }` 节点在这个世界里没有启动控制器；改成 `Robot { supervisor TRUE ... }` 后才工作。

---

## 7. 传感器校准与实测结果

### 7.1 校准数据

障碍物中心 x=0.45 m，箱体半宽 0.06 m，e-puck 半径约 0.036 m，理论接触点 x≈0.353 m。

实测 `ps0/ps7`：

| 里程计距离 | ps0 | ps7 |
|---|---|---|
| 0.333 m | 65.4 | 118.9 |
| 0.341 m | 70.5 | 153.9 |
| 0.348 m | 66.5 | 228.9 |
| 0.354 m | 67.5 | 353.4 |
| 0.359 m | 68.5 | 697.3 |
| 0.362 m | 72.1 | 1355.8 |

无障碍基线约 65–73。

### 7.2 阈值选择

最终阈值：`PS_STOP_THRESHOLD = 120.0`。

原因：

- 2×2 m 场地的前墙在约 0.4 m 处产生 60–80 读数；早期阈值 80 会把墙误判为障碍。
- 扩大到 3×3 m 后，阈值 120 在接触前约 15 mm 触发。
- 实测停车点 x≈0.330 m，相对障碍物面约 24 mm 间隙。

### 7.3 五种状态实测

| 状态 | 日志 | 说明 |
|---|---|---|
| `reached` | `RESULT: reached traveled=0.770m` | 实际 x≈0.7526 m |
| `blocked` | `RESULT: blocked front=134.7 traveled=0.338m` | 实际 x≈0.3302 m |
| `stopped` | `RESULT: stopped` | 位置不变 |
| `timeout` | `RESULT: timeout traveled=0.162m front=63.2` | 2 秒超时测试 |
| `error` | `RESULT: error ValueError("无法理解的命令：'fly to the moon'")` | 非法命令 |

### 7.4 里程计误差

轮式里程计报告 0.770 m，Supervisor 实际 0.7526 m：

```text
误差 ≈ (0.770 - 0.7526) / 0.7526 ≈ 2.3%
```

当前到达判定仍基于轮式里程计；目标标记半径 6 cm，机器人中心仍在标记内。

---

## 8. 如何复现

### 8.1 用户入口

在 `D:\A.me\Simulate robot\webots` 下：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Scenario clear
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Scenario blocked
```

每次运行约 25 秒后自动退出。

日志：

```text
logs\robot_controller.log
logs\session_supervisor.log
logs\results_clear.log
logs\results_blocked.log
```

### 8.2 自动状态测试

```powershell
# 停止
powershell -ExecutionPolicy Bypass -File .\tools\run_scenario.ps1 -Scenario clear -Command stop -WaitSeconds 5

# 非法命令
powershell -ExecutionPolicy Bypass -File .\tools\run_scenario.ps1 -Scenario clear -Command "fly to the moon" -WaitSeconds 6

# 2 秒超时
powershell -ExecutionPolicy Bypass -File .\tools\run_scenario.ps1 -Scenario clear -TimeoutSeconds 2 -WaitSeconds 6
```

控制器支持的环境变量：

- `SIMULATE_ROBOT_COMMAND`：覆盖默认命令。
- `SIMULATE_ROBOT_TIMEOUT`：覆盖超时秒数。

### 8.3 Linux 测试

```bash
cd /home/airpen/projects/simulate-robot
.venv/bin/python -m unittest discover -s tests -t . -v
```

---

## 9. 目录与关键文件

### 9.1 Windows Webots 工程

```text
D:\A.me\Simulate robot\webots\
├── run_demo.ps1
├── README.md
├── tools\
│   └── run_scenario.ps1
├── worlds\
│   ├── demo_clear.wbt
│   ├── demo_blocked.wbt
│   └── diagnostics\
│       ├── probe_https.wbt
│       ├── probe_official.wbt
│       └── probe.wbt
├── controllers\
│   ├── robot_controller\
│   │   ├── robot_controller.py
│   │   ├── runtime.ini
│   │   └── logic\robot.py
│   ├── session_supervisor\
│   │   └── session_supervisor.py
│   └── probe\
│       ├── probe.py
│       └── runtime.ini
└── logs\
    ├── robot_controller.log
    ├── session_supervisor.log
    ├── results_clear.log
    ├── results_blocked.log
    └── diagnostics\
```

### 9.2 Linux 项目

```text
/home/airpen/projects/simulate-robot/
├── README.md
├── src\
│   ├── robot.py
│   └── main.py
├── tests\
│   └── test_robot.py
└── docs\
    ├── design.md
    ├── first_steps.md
    └── webots_demo.md
```

### 9.3 逻辑同步

权威文件：

```text
/home/airpen/projects/simulate-robot/src/robot.py
```

Windows 副本：

```text
D:\A.me\Simulate robot\webots\controllers\robot_controller\logic\robot.py
```

当前 SHA256：

```text
e00ce50d2cd2f3c95fd9f3392fb01c1f63780e2f3a8cc6e9202f8730926b5ed0
```

不要在 Windows 侧手改 `logic/robot.py`；修改 Linux 源文件后重新复制。

---

## 10. 测试与回归

| 测试 | 结果 |
|---|---|
| Linux `unittest` | 7/7 通过 |
| Windows Python 控制器 `py_compile` | 通过 |
| `session_supervisor.py` `py_compile` | 通过 |
| `logic/robot.py` 哈希一致 | 通过 |
| `run_demo.ps1 -Scenario clear` | 退出码 0 |
| `run_demo.ps1 -Scenario blocked` | 退出码 0 |
| 运行后残留 Webots 进程 | 无 |

最终日志：

```text
# clear
RESULT: reached traveled=0.770m

# blocked
RESULT: blocked front=134.7 traveled=0.338m
```

---

## 11. 问题与根因分析

### 11.1 控制器完全不启动

**现象**：Webots 打开世界，但没有 `robot_controller.log`，没有 Python 子进程。

**排查**：

- 用官方 C 控制器世界做对照，`e-puck.exe` 正常启动，说明仿真和控制器机制正常。
- 用最小探针确认 Python 启动后会先写标记文件，因此“无标记”等价于“Python 没有被启动”。

**根因**：我们的世界使用 `webots://...` 形式的 `EXTERNPROTO`。窗口能打开，但 E-puck 没有真正实例化，控制器自然不会启动。

**修复**：改用官方 R2025a 的 HTTPS raw GitHub `EXTERNPROTO`。这是本次最关键的修复。

### 11.2 机器人从障碍物旁边驶过

**现象**：有障碍场景和无障碍场景的传感器日志完全相同，机器人继续前进并报告 `reached`。

**排查**：Supervisor 记录真实位姿，显示 x 递增、z 不变；障碍物在 −Z，机器人实际沿 +X 前进。

**根因**：误以为 e-puck 前进方向是 −Z。

**修复**：目标点和障碍物移到 +X 轴，2D `y` 映射到 Webots `+X`。

### 11.3 阈值 80 误判

**现象**：无障碍场景在 0.59 m 处报告 `blocked front=80.2`。

**根因**：2×2 m 场地前墙在近距离产生 60–80 读数；阈值 80 太低。

**修复**：场地扩大到 3×3 m，实测后阈值改为 120。

### 11.4 Supervisor 控制器不启动

**现象**：`session_supervisor.log` 不存在。

**根因**：单独写 `Supervisor { controller ... }` 节点在这个世界中没有启动控制器。

**修复**：改为 `Robot { supervisor TRUE controller "session_supervisor" }`。

### 11.5 PowerShell 参数拆分

**现象**：世界路径包含空格，早期 `Start-Process -ArgumentList` 把路径拆成多个参数，Webots 行为异常。

**修复**：用户入口使用调用运算符 `& $exe ... $world`，由 PowerShell 正确加引号。

### 11.6 其他环境问题

- `--minimize` 会自动使用快速模式并跳过欢迎界面；用户入口不再使用 `--minimize`，保持窗口可见。
- 手动运行 Python 控制器时需要 `WEBOTS_HOME`；Webots 内部启动会自动提供，手动测试需要自己设置。
- Webots 的 INFO 日志和控制器 stdout 在 `&` 调用下可见；早期 `Start-Process` 重定向会制造“没有输出”的假象。

---

## 12. 当前边界与风险

### 12.1 已实现

- 直线前进、停止。
- 左右轮电机控制。
- 轮式里程计。
- `ps0/ps7` 距离读取和阈值停车。
- 五种状态区分。
- Supervisor 真实位姿记录和自动退出。
- 可重复运行的 PowerShell Demo。

### 12.2 未实现

- 左右转、差速驱动转向、航向闭环。
- 绕障、路径规划、SLAM。
- 全局定位；当前只有轮式里程计。
- ROS 2、CUDA、Docker、LLM/Agent。

### 12.3 风险

- `PS_STOP_THRESHOLD=120` 只对当前 3×3 m 场地和 0.12 m 箱子校准。
- 轮式里程计约 2.3% 正误差；到达判定不是全局真值。
- Webots 安装包没有 Authenticode 签名（来源和 SHA256 已核对）。
- WSL 内 localhost 代理不可用；当前依赖直连，若网络环境变化可能需要重新配置。
- Linux Git 仓库尚未创建首个 commit（本轮未擅自提交）。

---

## 13. 下一阶段建议

1. **差速驱动转向与航向闭环**
   - 用左右轮差速实现原地转/弧线转。
   - 先用 Supervisor/GPS 做真值，再逐步替换为里程计+陀螺仪。

2. **从“停止避障”升级为“绕行”**
   - 基于 `ps0`–`ps7` 的方向差异做简单避障。
   - 保持“先安全停车，再尝试绕行”的优先级。

3. **自动化回归**
   - 解析 `logs/robot_controller.log` 和 `session_supervisor.log`。
   - 对每种状态断言最终结果和真实位姿。
   - 再考虑 ROS 2 或更复杂的导航栈。

---

## 14. 附录：哈希与路径

### 14.1 关键路径

```text
Webots 可执行文件:
C:\Program Files\Webots\msys64\mingw64\bin\webots.exe

Windows Python:
C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe

Windows Webots 工程:
D:\A.me\Simulate robot\webots

Linux 项目:
/home/airpen/projects/simulate-robot
```

### 14.2 校验值

```text
Webots 安装包 SHA256:
9E326A54C104FC5FC88121E26014A409D1E35F0BBF30E23F3A712E7F842B08E7

WSL MSI SHA256:
AE977286974255BD26BF925F00F40F5692C6B2084155CBC0563C09AEA091F211

Ubuntu 24.04.5 WSL 镜像 SHA256:
BB415D824822C4B878125729AF451A5D18FB13D1CF5CBED9A7393AD64AC6039E

logic/robot.py SHA256:
e00ce50d2cd2f3c95fd9f3392fb01c1f63780e2f3a8cc6e9202f8730926b5ed0
```

### 14.3 执行统计

```text
目标轮次：3 / 20
目标用时：约 3389 秒（约 56 分钟）
```

---

**报告结束。**
