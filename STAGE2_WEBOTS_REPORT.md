# Simulate Robot 第二阶段工程报告

> 阶段：第二阶段 — 差速驱动运动学、航向角与基础自主导航  
> 日期：2026-11-02  
> 环境：Windows 11、WSL2 Ubuntu 24.04、Webots R2025a、Python 3.12.10、e-puck  
> 结论：**工程目标已完成；导航与避障已用 Supervisor 真值验证，转向/距离为当次实测记录；Notion 学习文档已归档；障碍物处理为“基础尝试/部分通过”。**

---

## 1. 本阶段完成了什么

本阶段把机器人从“只会直行、遇障停止”推进到“能估计自身位姿、按指定角度转向、按指定距离前进、走向不同方向的目标点，并做一次基础绕障尝试”。

完成的主要内容：

1. **检查第一阶段工程**：确认 Linux 权威逻辑、Windows 逻辑副本、7 个原有测试和第一阶段 Webots 场景仍可用。
2. **建立差速驱动实验**：直线、左转、右转、原地旋转，全部在 Webots 中实际运行。
3. **实现独立运动学模块**：`src/kinematics.py`，包含正/逆运动学、角度归一化、目标方位、位姿积分；新增 15 个单元测试。
4. **实现轮式里程计与航向估计**：用左右轮编码器有符号增量积分位姿，并用 Supervisor 真值标定有效轮半径/轮距。
5. **实现指定角度转向**：90°、−90°、180°、30° 四组闭环测试。
6. **实现指定距离运动**：0.25 m、0.50 m、0.80 m 三组闭环测试。
7. **实现三方向目标点导航**：正前方、左前方、右前方，全部用 Supervisor 真值验证。
8. **实现基础规则式避障**：一个障碍场景，检测—停止—左转—前进—恢复，最终到达目标。
9. **完成回归测试**：22/22 Python 测试通过；第一阶段 `blocked` 场景复跑成功；运行后无残留 Webots/Python 进程。
10. **完成学习文档和工程报告**：阶段二学习文档 18 节；本报告 11 节。阶段一、阶段二已写入 Notion 的“项目 / Simulate Robot”下。

本阶段**没有**引入 ROS 2、SLAM、视觉、CUDA、Docker、LLM 或大型深度学习框架；没有修改 WSL 网络/代理/系统配置；没有安装新软件；没有提交或推送 Git。

---

## 2. 每项验收结果

| # | 验收项 | 结果 | 证据与说明 |
|---|---|---|---|
| 1 | 第一阶段回归 | 通过 | 22/22 单元测试通过；`demo_blocked` 复跑得到 `RESULT: blocked front=134.7 traveled=0.338m`；无残留进程 |
| 2 | 差速驱动 | 通过 | 两轮同速直行；左慢右快左转；左快右慢右转；方向与公式一致 |
| 3 | 原地旋转 | 通过 | +90° 实测 1.5712 rad；−90° 实测 −1.5712 rad；180° 实测 3.1376 rad（当次记录） |
| 4 | 运动学计算 | 通过 | `src/kinematics.py` + 15 个单元测试；正/逆运动学、角度、位姿积分覆盖 |
| 5 | 航向角 | 通过 | `atan2(R10, R00)` 提取 Supervisor yaw；最短角误差；左/右目标航向符号正确 |
| 6 | 里程计 | 通过 | 有符号编码器增量 + 中点积分；与 Supervisor 真值对比，导航终点误差 1.66–2.81 cm |
| 7 | 转向控制 | 通过 | 90°、−90°、180° 准确；30° 实测 0.4591 rad，差 3.70°，在 5° 容差内但接近一步分辨率 |
| 8 | 距离控制 | 通过 | 0.25/0.50/0.80 m 实测误差 1.96/1.87/1.66 cm（当次记录） |
| 9 | 目标点导航 | 通过 | 三个方向均到达；Supervisor 真值到目标 1.66/2.57/2.58 cm |
| 10 | 障碍物处理 | 部分通过 | 一个固定场景成功（两次 `AVOID`，真值误差 2.81 cm）；只验证了左转固定规则，未覆盖复杂/动态障碍 |
| 11 | 实际位姿验证 | 通过 | 每个导航/避障场景都有独立 Supervisor 日志和最终 `POSE` |
| 12 | 文档归档 | 通过 | 已在“项目 / Simulate Robot”下创建阶段一、阶段二子页，并 fetch 校验 |

### 结论口径

- 运动学、转向、距离、三方向导航、回归：**通过**。
- 基础避障：**部分通过**，符合任务书“至少完成基础避障尝试”的最低要求，但不宣称鲁棒避障。
- Notion 文档：**通过**（项目页 + 两个阶段子页，已 fetch 校验）。
- 因此整体状态是“**工程验收通过、文档已归档**”；基础避障仍为“部分通过”。

---

## 3. 新增和修改的文件

### 3.1 Linux 权威项目

根目录：`/home/airpen/projects/simulate-robot`

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/kinematics.py` | 新增 | 纯运动学/位姿逻辑，132 行；SHA256 `dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71` |
| `tests/test_kinematics.py` | 新增 | 15 个单元测试，覆盖正/逆运动学、角度、位姿 |
| `docs/stage1_webots_learning.md` | 新增（上一阶段末尾） | 阶段一学习文档；已写入 Notion |
| `docs/stage2_navigation_learning.md` | 新增 | 阶段二 18 节学习文档（本轮同时复制到 Windows 项目） |
| `README.md` | 修改 | 增加阶段二结构、命令、结果和限制 |

### 3.2 Windows Webots 项目

根目录：`D:\A.me\Simulate robot\webots`

| 文件 | 类型 | 说明 |
|---|---|---|
| `controllers/motion_controller/motion_controller.py` | 新增 | 阶段二适配层：`drive`/`forward`/`turn`/`navigate`/`avoid` |
| `controllers/motion_controller/runtime.ini` | 新增 | 固定 Python 3.12.10 解释器 |
| `controllers/robot_controller/logic/kinematics.py` | 新增 | Linux `src/kinematics.py` 的同步副本，SHA256 与 Linux 完全一致 |
| `worlds/stage2_lab.wbt` | 新增 | 4×4 空地、e-puck、Supervisor、目标标记 |
| `worlds/stage2_obstacle.wbt` | 新增 | 在 `stage2_lab` 基础上增加 0.12 m 立方体障碍 |
| `tools/run_motion.ps1` | 新增 | 阶段二实验运行器，支持模式/目标/角度/距离/轮速/时长 |
| `controllers/session_supervisor/session_supervisor.py` | 修改 | 增加完整旋转矩阵、`yaw`、真实位置日志；仍为 25 s 限时退出 |
| `logs/stage2_nav_straight*.log` | 新增 | 正前方导航证据 |
| `logs/stage2_nav_left*.log` | 新增 | 左前方导航证据 |
| `logs/stage2_nav_right*.log` | 新增 | 右前方导航证据 |
| `logs/stage2_obstacle*.log` | 新增/重跑 | 避障证据，含两次 `AVOID`；已修正此前误复制为右方向导航的问题 |
| `docs/stage2_navigation_learning.md` | 新增 | 阶段二学习文档（Windows 可读副本） |
| `STAGE2_WEBOTS_REPORT.md` | 新增 | 本报告（项目根目录） |

### 3.3 同步校验

```text
Windows: dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71
Linux:   dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71
```

两份 `kinematics.py` 字节一致。修改规则仍然是：**先改 Linux 权威文件，再同步到 Windows，不手改 Windows 副本。**

---

## 4. 关键代码设计

### 4.1 分层

```text
src/kinematics.py                 纯逻辑，无 Webots 依赖
        │
        ├── tests/test_kinematics.py       单元测试
        │
        └── controllers/robot_controller/logic/kinematics.py   同步副本
                    │
                    ▼
controllers/motion_controller/motion_controller.py   设备适配 + 控制循环
                    │
                    ▼
worlds/stage2_lab.wbt / stage2_obstacle.wbt         场景
                    │
                    ▼
controllers/session_supervisor/session_supervisor.py  真实位姿验证
```

### 4.2 模式选择

`motion_controller.py` 用环境变量 `SIMULATE_MODE` 选择模式：

| 模式 | 作用 | 关键反馈 |
|---|---|---|
| `drive` | 开环轮速、固定时长 | 无（标定用） |
| `forward` | 指定距离直线 | 累计里程计路程 |
| `turn` | 指定角度原地转向 | 里程计航向 |
| `navigate` | 单目标点导航 | 距离 + 航向 + 前方传感器 |
| `avoid` | 导航 + 基础避障 | 距离 + 航向 + 前方传感器 + 定时状态机 |

同一个控制器复用五种模式，避免为每个实验复制一份代码。

### 4.3 参数集中管理

关键参数集中在 `motion_controller.py:36-55`：

```python
TIME_STEP_MS = 32
WHEEL_RADIUS_M = 0.0200
WHEEL_BASE_M = 0.058
MAX_WHEEL_SPEED = 4.0
SPIN_WHEEL_SPEED = 2.0
POSITION_TOLERANCE_M = 0.02
HEADING_TOLERANCE_RAD = math.radians(5.0)
PS_STOP_THRESHOLD = 120.0
TIMEOUT_S = float(os.environ.get("SIMULATE_TIMEOUT", "22.0"))
```

`TIME_STEP_MS` 当前未被使用（技术债），实际步长从 `robot.getBasicTimeStep()` 读取。

### 4.4 里程计

```python
left_delta = (left_value - previous_left) * WHEEL_RADIUS_M
right_delta = (right_value - previous_right) * WHEEL_RADIUS_M
distance_m += (left_delta + right_delta) / 2.0
pose = advance_pose(pose, left_delta, right_delta, WHEEL_BASE_M)
```

- 第一帧只记录初值，不积分。
- 有符号增量支持倒车。
- 位姿积分使用中点航向。
- `distance_m` 是累计路程，只用于直线距离模式。

### 4.5 转向与导航

转向：

```python
error = angle_error(target_heading, pose.heading_rad)
if abs(error) <= HEADING_TOLERANCE_RAD:
    stop()
angular = SPIN_WHEEL_SPEED if error > 0 else -SPIN_WHEEL_SPEED
```

导航：

```python
distance = hypot(target - pose)
desired = heading_to_target(...)
error = angle_error(desired, pose.heading)
if distance <= POSITION_TOLERANCE_M: stop()
elif abs(error) > HEADING_TOLERANCE_RAD: spin
else: drive
```

- 位置优先于朝向：进入 2 cm 即停止。
- 每步重算，不是开环定时。
- 任何终止分支都先停车。

### 4.6 避障状态机

```text
drive --front>120且冷却结束--> turn(1.0 s) --> forward(1.2 s) --> drive
```

- 固定左转，不判断左右空间。
- 1.5 s 冷却防止连续触发。
- 只使用 `ps0`/`ps7` 两个前方传感器。
- 这是“基础尝试”，不是路径规划。

### 4.7 Supervisor 独立验证

`session_supervisor.py`：

```python
orientation = robot_node.getOrientation()
yaw = math.atan2(orientation[3], orientation[0])
log(f"POSE t={now:.2f} pos={robot_node.getPosition()} yaw={yaw:.4f} ori={orientation}")
```

Supervisor 不把真值写给控制器，只写入独立日志。这样控制器仍然只依赖机载编码器，实验验证才成立。

---

## 5. 实际仿真数据

### 5.1 转向

| 目标 | 实测航向 | 误差 | 结论 |
|---|---|---|---|
| +90° | +1.5712 rad | +0.0004 rad（0.02°） | 通过 |
| −90° | −1.5712 rad | −0.0004 rad | 通过 |
| 180° | 3.1376 rad | −0.0040 rad（−0.23°） | 通过 |
| 30° | 0.4591 rad | −0.0645 rad（−3.70°） | 在 5° 容差内；接近一步 3.67° 的量化极限 |

### 5.2 指定距离

| 目标距离 | 控制器里程计 | 实测距离（当次记录） | 误差 |
|---|---|---|---|
| 0.25 m | 约 0.230 m | 0.2304 m | −1.96 cm |
| 0.50 m | 约 0.481 m | 0.48128 m | −1.87 cm |
| 0.80 m | 约 0.783 m | 0.78336 m | −1.66 cm |

控制器在 `target − 0.02 m` 停止，因此系统性欠走约 2 cm，符合设计。转向和距离实验的独立 Supervisor 日志未逐次保存；表中数值来自当次实际运行记录，不声称存在独立 Supervisor 文件。

### 5.3 三方向导航

| 目标点 | 控制器结果 | 里程计终点 | Supervisor 真值 | 真值到目标距离 |
|---|---|---|---|---|
| (0.8, 0.0) | `reached distance=0.018` | (0.782, 0.000) | (0.78336, 0.00000) | 1.66 cm |
| (0.8, 0.8) | `reached distance=0.018` | (0.790, 0.785) | (0.77439, 0.80255) | 2.57 cm |
| (0.8, −0.8) | `reached distance=0.018` | (0.790, −0.785) | (0.77437, −0.80255) | 2.58 cm |

### 5.4 基础避障

障碍物中心 `(0.45, 0, 0)`，边长 0.12 m。

| 事件 | 数据 |
|---|---|
| 第一次触发 | `AVOID: obstacle front=136.4`，x≈0.327 |
| 第二次触发 | `AVOID: obstacle front=128.4`，约 (0.331, 0.085) |
| 控制器终点 | `pose=(0.784, 0.009, -0.448)`，`distance=0.018` |
| Supervisor 终点 | `(0.77745, −0.01687)`，yaw −0.5040 |
| 真值到目标 | 2.81 cm |
| 结果 | `RESULT: reached target=(0.8,0.0)` |

轨迹概要：直行→第一次左转约 1.92 rad→向 +Y 走约 9 cm→恢复→第二次左转约 1.9 rad→向 +Y 到 y≈0.18→从障碍上方绕过→到达目标。总仿真时间约 18.5 s（25 s Supervisor 上限内）。

### 5.5 第一阶段回归

```text
RESULT: blocked front=134.7 traveled=0.338m
```

第一阶段遇障停止功能未退化；运行结束后无残留 Webots/Python 进程。

### 5.6 数据可信度说明

- 导航与避障数据来自独立保存的日志，可用 `grep` 复核。
- 转向和距离数据来自当次实际运行记录，但**没有逐次保存独立日志**；这是本阶段的证据缺口，已列入技术债。
- 所有 Webots 运行使用 `--no-rendering --batch`，没有录制视频；验证依据是控制器日志 + Supervisor 真值，不是肉眼观看。

---

## 6. 单元测试和回归测试结果

### 6.1 Python 测试

命令：

```bash
cd /home/airpen/projects/simulate-robot
.venv/bin/python -m unittest discover -s tests -v
```

结果：

```text
Ran 22 tests in 0.001s

OK
```

构成：

| 测试文件 | 数量 | 内容 |
|---|---|---|
| `tests/test_robot.py` | 7 | 命令解析、到达、停止、障碍 |
| `tests/test_kinematics.py` | 15 | 正/逆运动学、角度、目标方位、位姿积分、非法参数 |
| 合计 | 22 | 全部通过 |

说明：项目使用标准库 `unittest`，没有安装 pytest；`python -m pytest` 会报 `No module named pytest`，属于环境事实，不是测试失败。

### 6.2 Webots 场景回归

| 场景 | 结果 |
|---|---|
| `stage2_lab.wbt` 正前方导航 | `reached`，真值误差 1.66 cm |
| `stage2_lab.wbt` 左前方导航 | `reached`，真值误差 2.57 cm |
| `stage2_lab.wbt` 右前方导航 | `reached`，真值误差 2.58 cm |
| `stage2_obstacle.wbt` 避障 | `reached`，两次 `AVOID`，真值误差 2.81 cm |
| `demo_blocked.wbt` 第一阶段回归 | `blocked`，front=134.7，traveled=0.338 m |

### 6.3 进程清理

每次运行结束后检查：

```powershell
Get-Process | Where-Object {
  $_.ProcessName -like '*webots*' -or $_.ProcessName -like 'python*'
}
```

返回空结果。运行器启动前也会清理残留进程，避免日志和端口互相污染。

### 6.4 同步校验

```text
Windows kinematics.py SHA256 = dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71
Linux   kinematics.py SHA256 = dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71
```

完全一致。

---

## 7. 未完成事项及原因

### 7.1 Notion 学习文档（已完成）

用户已明确授权并指定“项目页 + 两个子页”。已在“📁 项目”下创建“Simulate Robot”项目页，并挂载：

- 阶段一：https://app.notion.com/p/40c3f761570d8154b710fe3a9e66132d
- 阶段二：https://app.notion.com/p/40c3f761570d812e977ecd7007217d32

写入后已通过 Notion fetch 校验父子层级、标题、正文和代码块；阶段一覆盖 12 个主题，阶段二覆盖 18 节。本地 Markdown 保留为更详细的版本。

### 7.2 避障只完成基础尝试（部分通过）

- 只验证了一个固定障碍、一个固定目标、固定左转规则；
- 没有测试障碍在右侧、狭窄通道、多个障碍、动态障碍、死角；
- 前方只有 `ps0`/`ps7` 两个传感器，没有左右空间比较；
- 避障动作使用固定时长，不是传感器闭环；
- 因此标记“部分通过”，不宣称鲁棒避障。

### 7.3 转向/距离实验日志未逐次归档（证据缺口）

- 导航和避障有独立日志；
- 转向和距离的独立日志没有逐次保存，只保留了当次运行记录；
- 影响：报告中的数据可追溯到会话记录，但不能像导航那样直接从文件复核；
- 修复方式：下一阶段把每种模式都自动归档到 `logs/stage2_<mode>_<params>.log`。

### 7.4 小角度转向接近量化极限

- 30° 目标实测 0.4591 rad，差 3.70°；
- 在 5° 容差内，但只比一步 3.67° 略小；
- 不是公式错误，是“固定 2 rad/s + 32 ms 采样 + 5° 容差”的结果；
- 本阶段不降低标准把它说成“精确”，而是记录为“通过容差、接近极限”。

### 7.5 未提交 Git

任务书明确当前不要擅自提交或推送；本阶段保持未提交状态，等待用户许可。

### 7.6 未做可视化/视频验证

- 所有运行使用 `--no-rendering --batch`，没有录屏；
- 证据是控制器日志和 Supervisor 真值；
- 如果用户需要“肉眼可见”的演示，需要另开 GUI 运行并录屏，本阶段未做。

---

## 8. 当前技术债务

| 债务 | 影响 | 建议 |
|---|---|---|
| `TIME_STEP_MS` 未使用 | 轻微混淆 | 删除或真正用于步长校验 |
| `r`/`L` 分散在控制器和测试中 | 修改时容易不同步 | 抽到共享配置/常量模块 |
| 通过 `sys.path` 共享 `logic` 目录 | 目录结构脆弱 | 打成小包或用 `PYTHONPATH` 明确管理 |
| 避障固定左转、固定时长 | 鲁棒性差 | 比较左右传感器，加入简单记忆/栅格 |
| 只使用 `ps0`/`ps7` | 侧后方盲区 | 使用 `ps1`/`ps6` 等更多传感器 |
| 位置容差 2 cm、速度固定 | 精度和冲击不可调 | 加入减速段/PID/速度规划 |
| Supervisor 固定 25 s | 远目标可能不够 | 按场景配置时限 |
| 运行器清理所有 `python*` | 可能误杀其他 Python | 按 PID/路径精确清理 |
| 日志不自动归档 | 证据易覆盖 | 运行时自动生成带参数的文件名 |
| Webots 场景测试未全自动 | 需要人工跑多条命令 | 写一键脚本并解析 Supervisor 真值断言 |
| Notion 写入 | 已完成 | 项目页 + 两个阶段子页，已 fetch 校验 |
| 没有外部定位 | 长距离漂移 | 下一阶段引入 GPS/compass 对照，再考虑 SLAM |

---

## 9. Notion 文档链接或写入结果

### 9.1 搜索结果与层级

- 工作空间中存在 `PS_Projects` 数据源（`collection://a70445bf-000b-4c2e-8b2c-69f80fe5ca6a`）和 `PS_Knowledge` 数据源（`collection://c7c22441-ca82-4a55-aa77-ccd430a1d986`）；
- 现有“📁 项目”页面（ID `3fd3f761570d815a819bd432152cf943`）作为父页面；
- 其下原先没有 Simulate Robot 项目页，本次创建后层级为：项目 / Simulate Robot / 阶段一、阶段二。

### 9.2 写入结果

已创建并校验：

| 页面 | URL |
|---|---|
| Simulate Robot 项目页 | https://app.notion.com/p/40c3f761570d8110b6e7e0691f9fdc2e |
| 阶段一学习文档 | https://app.notion.com/p/40c3f761570d8154b710fe3a9e66132d |
| 阶段二学习文档 | https://app.notion.com/p/40c3f761570d812e977ecd7007217d32 |

校验方式：Notion fetch 返回 `ancestor-path` 为“项目 / Simulate Robot”，标题与本地文档一致；阶段一覆盖 12 个主题，阶段二覆盖 18 节；正文包含表格、代码块、实际数据和自测题。写入过程中一次 `update_content` 调用返回 MCP 内部错误，改用最小替换后成功修正公式记号；未删除或重建页面。

### 9.3 本地文档

| 文档 | 本地路径 | 状态 |
|---|---|---|
| 《阶段一：Webots 机器人仿真与 Python 控制器入门》 | `/home/airpen/projects/simulate-robot/docs/stage1_webots_learning.md` | 已完成，作为详版 |
| 《阶段二：差速驱动运动学、航向角与基础自主导航》 | `D:\A.me\Simulate robot\docs\stage2_navigation_learning.md` | 已完成，作为详版 |
| 第二阶段工程报告 | `D:\A.me\Simulate robot\STAGE2_WEBOTS_REPORT.md` | 已完成 |

---

## 10. 用户应该掌握的核心知识

1. **差速驱动的本质是速度差**：同速直行，右快左转，左快右转，反向原地转；`v = r(ωR+ωL)/2`，`ω = r(ωR−ωL)/L`。
2. **坐标系必须先实测**：本项目 e-puck 前进 +X，平面 X–Y，yaw 绕 +Z；Supervisor yaw 用 `atan2(R10, R00)`。套用其他约定会把方向弄反。
3. **角度要归一化**：`atan2(sin, cos)` 取最短路径；否则 350°→10° 会绕 340°。
4. **里程计是航位推算**：编码器增量积分，误差会累积；轮滑、有效半径/轮距、采样、量化都是误差源。
5. **标定是控制的一部分**：有效 `r=0.0200`、`L=0.058` 不是数据手册值，而是让里程计更接近真值的工程参数；换场景要重标。
6. **闭环优于定时**：转向和距离都用反馈判断结束，不靠固定等待。
7. **`reached` 不是验收证据**：控制器报告的是里程计距离；必须用 Supervisor 真值计算到目标的欧氏距离。本阶段控制器说 0.018 m，真值误差可达 2.57 cm。
8. **容差与采样要匹配**：2 rad/s + 32 ms 一步约 3.67°；5° 容差能避免抖动，但小角度会有接近一步的误差。
9. **基础避障不是路径规划**：固定“停—左转—前进—恢复”只能算尝试，复杂环境需要地图、规划和更多传感器。
10. **分层让系统可验证**：纯逻辑可单元测试，适配层只碰设备，Supervisor 只做独立验证。

---

## 11. 下一阶段建议

### 11.1 优先做“运动控制质量”，而不是堆功能

1. **速度闭环/PID**：用编码器估计实际轮速，控制直线更直、转向更稳。
2. **接近目标减速**：解决 30° 转向和 2 cm 停止的量化问题。
3. **轨迹跟踪**：从“转向—直走”升级到 Pure Pursuit 或简单曲线跟踪。
4. **多航点**：按顺序访问多个目标，处理到达后的朝向。
5. **自动化 Webots 测试**：一条命令跑完所有场景，自动解析 Supervisor 真值并断言误差。

### 11.2 避障升级

1. 使用 `ps1`/`ps6` 等更多传感器，比较左右空间；
2. 加入障碍记忆和简单的 Bug/栅格算法；
3. 测试右侧障碍、狭窄通道、多个障碍、动态障碍；
4. 明确失败判据：卡住、超时、碰撞都算失败，不粉饰。

### 11.3 定位与地图

1. 先用 Webots 的 GPS/compass 与里程计对比，量化漂移；
2. 再考虑 EKF/UKF 融合；
3. 最后才引入 SLAM，避免在基础控制不稳时堆复杂系统。

### 11.4 文档与工程管理

1. 后续内容更新时同步本地 Markdown 与 Notion 项目页。
2. 把每种实验的日志自动归档，报告只引用可复核的文件；
3. 在用户许可后完成 Git 首次提交，按阶段拆分提交；
4. 保持 Linux 权威逻辑 + Windows 同步副本的规则，不双维护。

---

## 附录 A：复现命令

```powershell
cd "D:\A.me\Simulate robot\webots"

# 转向
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode turn -Angle 90
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode turn -Angle -90
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode turn -Angle 180

# 距离
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode forward -Distance 0.5

# 导航
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode navigate -TargetX 0.8 -TargetY 0.8
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode navigate -TargetX 0.8 -TargetY -0.8

# 避障
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode avoid -WorldFile stage2_obstacle.wbt -TargetX 0.8 -TargetY 0
```

```bash
# 单元测试
cd /home/airpen/projects/simulate-robot
.venv/bin/python -m unittest discover -s tests -v
```

## 附录 B：关键文件 SHA256

```text
kinematics.py (Linux/Windows 同步)  dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71
```

## 附录 C：证据日志清单

```text
webots/logs/stage2_nav_straight.log
webots/logs/stage2_nav_straight_supervisor.log
webots/logs/stage2_nav_left.log
webots/logs/stage2_nav_left_supervisor.log
webots/logs/stage2_nav_right.log
webots/logs/stage2_nav_right_supervisor.log
webots/logs/stage2_obstacle.log
webots/logs/stage2_obstacle_supervisor.log
```

日志中的最终 Supervisor 行示例：

```text
POSE t=24.61 pos=[0.7743870861537567, 0.8025485813827526, -6.395006364261907e-05] yaw=0.9827 ...
```

---

**报告结论：** 第二阶段的运动学、里程计、转向、距离、三方向导航和回归测试均已完成；导航/避障用 Supervisor 真值验证，转向/距离为当次实测记录；基础避障完成一次成功尝试但鲁棒性不足；阶段一、阶段二学习文档已写入 Notion 的“项目 / Simulate Robot”下。未完成项已如实标注，没有降低验收标准。
