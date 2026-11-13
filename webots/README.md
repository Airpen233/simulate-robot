# Simulate Robot — Webots R2025a（阶段一 + 阶段二）

本目录包含 Simulate Robot 的两阶段 3D 仿真工程：

- **阶段一**：官方 e-puck 模型、Python 控制器、直线前进、距离传感器、遇障停止、Supervisor 真值验证。
- **阶段二**：差速驱动运动学、轮式里程计、航向角闭环、指定角度转向、指定距离运动、三方向目标点导航、基础规则式避障。

纯逻辑仍由 Linux 项目权威维护：

```text
/home/airpen/projects/simulate-robot/src/robot.py
/home/airpen/projects/simulate-robot/src/kinematics.py
```

Windows 控制器使用字节一致的副本：

```text
controllers/robot_controller/logic/robot.py
controllers/robot_controller/logic/kinematics.py
```

## 状态

本机已验证：

- Webots R2025a 安装于 `C:\Program Files\Webots`。
- Python 3.12.10 控制器能在 Webots 内启动并导入 `controller` 模块。
- e-puck 的 36 个设备可见（轮电机/编码器、ps0–ps7、ls0–ls7、相机、LED、加速度计、陀螺仪、接收器、发射器、扬声器）。
- 阶段一五种状态 `reached`、`blocked`、`stopped`、`timeout`、`error` 都由真实运行产生。
- 阶段二在 Webots 中实测：直行、左转、右转、原地旋转、90°/180°/30° 转向、0.25/0.50/0.80 m 距离、三方向目标点导航、基础避障。
- Python 测试 **22/22** 通过（阶段一 7 + 阶段二运动学 15）。
- 每次运行结束后无残留 Webots/Python 进程。

## 快速开始

### 初学者：一键打开随机多障碍实验（GUI）

双击 `START_RANDOM_AVOID.bat`。Webots 会以暂停模式打开，点顶部 **Run** 开始；详细步骤见 [docs/WEBOTS_BEGINNER_START.md](../docs/WEBOTS_BEGINNER_START.md)。

只想检查文件和参数、不启动仿真时：

```bat
cd /d "D:\A.me\Simulate robot\webots"
START_RANDOM_AVOID.bat --validate
```

### 阶段一：直线与遇障停止

```powershell
cd "D:\A.me\Simulate robot\webots"
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Scenario clear
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1 -Scenario blocked
```

### 阶段二：转向、距离、导航、避障

```powershell
# 开环标定：两轮 2 rad/s，跑 2 秒
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 `
  -Mode drive -Left 2 -Right 2 -Duration 2

# 指定角度（正数左转，负数右转）
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode turn -Angle 90
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode turn -Angle -90
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode turn -Angle 180

# 指定距离
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode forward -Distance 0.5

# 目标点导航（三个方向）
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode navigate -TargetX 0.8 -TargetY 0
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode navigate -TargetX 0.8 -TargetY 0.8
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 -Mode navigate -TargetX 0.8 -TargetY -0.8

# 基础避障
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 `
  -Mode avoid -WorldFile stage2_obstacle.wbt -TargetX 0.8 -TargetY 0
```

运行器会设置 `SIMULATE_*` 环境变量、清空旧日志、启动 Webots（`--batch --no-rendering --mode=realtime`），等待指定秒数后打印两份日志并清理进程。

结果写入：

```text
logs\motion_controller.log
logs\session_supervisor.log
```

## 实测结果

### 阶段一

| 场景 | 控制器结果 | Supervisor 最终 x | 说明 |
|---|---|---|---|
| clear | `reached traveled=0.770m` | 0.7526 m | 目标中心 0.8 m，仍在 6 cm 标记内 |
| blocked | `blocked front=134.7 traveled=0.338m` | 0.3302 m | 障碍中心 0.45 m，约 24 mm 间隙 |
| stop | `stopped` | 不变 | 无轮子运动 |
| timeout | `timeout traveled=0.162m` | — | 超时分支已执行 |
| error | `error ValueError(...)` | — | 非法命令被报告 |

### 阶段二

| 场景 | 控制器结果 | 实测值 | 误差 |
|---|---|---|---|
| 左转 90° | `turned` | +1.5712 rad | +0.0004 rad |
| 右转 90° | `turned` | −1.5712 rad | −0.0004 rad |
| 原地 180° | `turned` | 3.1376 rad | −0.0040 rad |
| 小角度 30° | `turned` | 0.4591 rad | −0.0645 rad（3.70°，在 5° 容差内） |
| 前进 0.25 m | `reached` | 0.2304 m | −1.96 cm |
| 前进 0.50 m | `reached` | 0.48128 m | −1.87 cm |
| 前进 0.80 m | `reached` | 0.78336 m | −1.66 cm |
| 目标 (0.8, 0) | `reached distance=0.018` | (0.78336, 0.00000) | 1.66 cm |
| 目标 (0.8, 0.8) | `reached distance=0.018` | (0.77439, 0.80255) | 2.57 cm |
| 目标 (0.8, −0.8) | `reached distance=0.018` | (0.77437, −0.80255) | 2.58 cm |
| 基础避障 | `reached distance=0.018` | (0.77745, −0.01687) | 2.81 cm；两次 `AVOID` |

证据日志：

```text
logs\stage2_nav_straight.log
logs\stage2_nav_straight_supervisor.log
logs\stage2_nav_left.log
logs\stage2_nav_left_supervisor.log
logs\stage2_nav_right.log
logs\stage2_nav_right_supervisor.log
logs\stage2_obstacle.log
logs\stage2_obstacle_supervisor.log
```

注意：导航/避障为 Supervisor 真值；转向/距离为当次运行记录，未单独保存 Supervisor 日志。

## 控制回路

### 阶段一：`controllers/robot_controller/robot_controller.py`

1. 创建 `Robot()`，使能两轮编码器和 `ps0`/`ps7`。
2. 通过共享的 `parse_command()` 解析命令：
   - 默认 `go to 0, 0.8`；
   - 可用 `SIMULATE_ROBOT_COMMAND` 覆盖。
3. 每个 `robot.step(32 ms)`：
   - 读取轮编码器增量，累计路程；
   - 读取 `ps0`/`ps7`；
   - `max(ps0, ps7) > 120` 时停车并报告 `blocked`；
   - 到达目标距离时停车并报告 `reached`；
   - 超过 `TIMEOUT_S` 时停车并报告 `timeout`。
4. 非法命令抛 `ValueError`，入口报告 `RESULT: error ...`。

### 阶段二：`controllers/motion_controller/motion_controller.py`

通过 `SIMULATE_MODE` 选择：

- `drive`：开环轮速、固定时长（标定）。
- `forward`：用累计路程闭环到指定距离。
- `turn`：用里程计航向闭环到指定角度（正数左转）。
- `navigate`：单目标点导航（距离 + 航向 + 前方传感器）。
- `avoid`：导航 + 固定“停—左转—前进—恢复”规则。

关键参数：

```python
WHEEL_RADIUS_M = 0.0200   # 有效值，不是名义 0.0205
WHEEL_BASE_M = 0.058      # 有效值，不是名义 0.052
MAX_WHEEL_SPEED = 4.0
SPIN_WHEEL_SPEED = 2.0
POSITION_TOLERANCE_M = 0.02
HEADING_TOLERANCE_RAD = math.radians(5.0)
PS_STOP_THRESHOLD = 120.0
TIMEOUT_S = 22.0
```

`session_supervisor` 读取真实位姿并每 0.5 s 记录一次；25 s 后 `simulationQuit(0)`，保证每次实验有界。

## 重要技术结论

这些是调试成本最高、最容易再次踩坑的点：

1. **`EXTERNPROTO` 在本机必须用 HTTPS。** 世界文件使用官方 R2025a raw GitHub URL；写成 `webots://...` 时窗口能开，但 e-puck 不实例化，控制器不启动。
2. **e-puck 前进轴是 +X，不是 −Z。** Supervisor 日志显示 x 增加、z 保持 0；目标标记和障碍物都在 +X 轴。
3. **平面运动是 X–Y，偏航绕 +Z。** Supervisor 旋转矩阵按行优先，`yaw = atan2(orientation[3], orientation[0])`，即 `atan2(R10, R00)`。
4. **不要用 `orientation[2]` 或 `orientation[1]` 算 yaw。** 前者是 Z 倾斜分量，后者是 `-sin(yaw)`，会把方向弄反。
5. **使用 `Robot { supervisor TRUE }`。** 裸 `Supervisor { ... }` 节点在本世界中不会启动控制器。
6. **世界路径含空格必须加引号。** `Start-Process -ArgumentList` 不会自动加引号；`run_demo.ps1` 用调用运算符（`&`）处理。
7. **Python 3.12 可用。** Webots 以 `python.exe -u ...` 启动；`runtime.ini` 固定解释器。
8. **里程计需要有效标定。** 名义 `r=0.0205`、`L=0.052` 下，直线约偏高 2.3%，旋转约偏高 10%；改用 `r=0.0200`、`L=0.058` 后，90°/180° 转向与 1.7–2.0 cm 距离误差达到本阶段水平。
9. **控制器 `reached` 不是验收证据。** 里程计会漂移；必须用 Supervisor 真值计算到目标的欧氏距离。
10. **证据日志不要复用文件名。** 每次运行结束立即复制到带场景名的文件；引用前 `grep` 检查目标坐标和 `RESULT` 是否匹配。本项目曾把右方向导航日志误存成避障日志，后已重跑并修正。

## 传感器阈值

第一阶段在早期 3×3 m 场地实测；阶段二场景为 4×4 m：

```text
travelled 0.333 m  ps0  65.4  ps7  118.9
travelled 0.341 m  ps0  70.5  ps7  153.9
travelled 0.348 m  ps0  66.5  ps7  228.9
travelled 0.354 m  ps0  67.5  ps7  353.4
travelled 0.359 m  ps0  68.5  ps7  697.3
travelled 0.362 m  ps0  72.1  ps7 1355.8
```

无遮挡基线约 65–73；`PS_STOP_THRESHOLD = 120` 大约在接触前 15 mm 触发。阈值只对当前场地、地面和 0.12 m 箱子校准，换场景需重测。

## 多障碍演示世界（新增）

为了更直观地观察“多次避障”，新增了：

```text
worlds\stage2_multi_obstacle.wbt
```

- 场地：2.4×2.4 m；e-puck 保持真实尺寸，不改轮半径/轮距。
- 障碍：3 个 0.18 m 立方体，初始位置 (0.32, 0)、(0.55, −0.01)、(0.76, 0.05)。
- 目标：(1.0, 0)；目标标记半径 0.07 m。
- 视角：近距离跟随，机器人/障碍在画面中明显变大。
- 机器人从原点开始，世界文件没有保存终点状态。

运行：

```powershell
$env:SIMULATE_TIMEOUT = "24"
powershell -ExecutionPolicy Bypass -File .\tools\run_motion.ps1 `
  -Mode avoid -WorldFile stage2_multi_obstacle.wbt -TargetX 1.0 -TargetY 0 -WaitSeconds 32
```

实测结果：

| 版本 | 障碍 3 位置 | AVOID 次数 | 控制器结果 | Supervisor 真值 | 真值误差 |
|---|---|---|---|---|---|
| v1 | (0.76, −0.02) | 2 | `distance=0.020` | (0.97307, 0.07107) | 7.6 cm |
| v2 | (0.76, 0.05) | 3 | `distance=0.019` | (0.97035, 0.11641) | 12.0 cm |

结论：**多次避障确实可以发生**；v2 连续触发了 3 次。但固定“停—左转—直走—恢复”规则在多次避障后会累积航向/里程计误差，最终真值误差从单障碍的 2.81 cm 退化到 7.6–12.0 cm。这个世界的用途是观察多次触发，不是精度验收；精度实验仍用 `stage2_lab.wbt` / `stage2_obstacle.wbt`。

注意：`stage2_obstacle.wbt` 当前保存了上次结束时的 e-puck 位姿（`translation` 约 `0.885, −0.357`，含 `hidden` 状态），直接重跑会从终点附近开始；我没有改它，避免动旧证据。需要复位或重建时告诉我。

## 随机多障碍与状态机避障（本轮）

新增可复现的随机多障碍世界、纯逻辑状态机和独立验证链路：

```text
worlds/stage2_random_obstacles.wbt        # 固定 seed=7，4 个障碍
worlds/stage2_random_seed_1..10.wbt       # 10 个随机种子
worlds/stage2_scenario_*.wbt              # clear/front/left_blocked/right_blocked/both_blocked/no_path
controllers/avoid_controller/             # 新控制器
controllers/avoid_supervisor/             # 真值 + 碰撞 + 障碍位置日志
controllers/robot_controller/logic/avoidance.py  # Linux src/avoidance.py 同步副本
tools/generate_random_world.py            # 2.2×2.2 m、4–6 障碍、BFS 通路检查
tools/run_avoid.ps1                       # 单场景运行
tools/run_avoid_suite.ps1                 # 固定/随机批量运行
tools/summarize_runs.py                   # CSV + Markdown 汇总
```

命令：

```powershell
python tools/generate_random_world.py --self-test
python tools/generate_random_world.py --scenario scenarios
python tools/generate_random_world.py --scenario fixed --seed 7
python tools/generate_random_world.py --scenario random --seed 1
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid_suite.ps1 -Mode all -Timeout 24
python tools/summarize_runs.py
```

状态机：`NAVIGATE → BRAKE → EVALUATE → TURN_LEFT/RIGHT → MOVE_AROUND → REASSESS → RECOVER`；重复失败且后向安全时进入一次短 `BACKUP`；超过次数进入 `STUCK`/`BLOCKED`。

传感器：前方 `ps0/ps7`，左侧 `ps5/ps6`，右侧 `ps1/ps2`，后方只有斜后 `ps3/ps4`（没有正后方传感器，后退不是绝对安全）。

实测（17 次：7 固定 + 10 随机）：

- 控制器 `reached`：14/17；Supervisor 真值 ≤3 cm：**11/17（64.7%）**
- 障碍物碰撞：**0**
- `timeout`：3（both_blocked、no_path、random_seed_9）
- 后退：2 次；避障尝试/转向计数见 `logs/random_avoid/summary.csv`
- 单障碍/左右镜像：真值误差 2.41–2.95 cm
- 随机种子：6/10 真值 ≤3 cm；seed 4 出现**假成功**：控制器自报 `reached`（估计 x=0.982），Supervisor 真值 x=0.55，误差 45 cm——轮子顶住障碍打滑，里程计虚增。这正是“不能只看 reached”的证据。

完整结果与失败原因见 `STAGE2_RANDOM_AVOID_REPORT.md` 和 `docs/stage2_random_avoid_learning.md`；Notion 页面：https://app.notion.com/p/40c3f761570d815b9de8edc9b4ff9a55

## 结构

```text
webots/
├── START_RANDOM_AVOID.bat           # 初学者一键启动（GUI，暂停开局）
├── run_demo.ps1                     # 阶段一运行器
├── README.md
├── tools/
│   ├── run_motion.ps1               # 阶段二运行器
│   ├── generate_random_world.py     # 随机世界生成器
│   ├── run_avoid.ps1                # 单场景运行器
│   ├── run_avoid_suite.ps1          # 固定/随机批量运行
│   ├── summarize_runs.py            # 汇总 CSV/Markdown
│   └── run_scenario.ps1             # 阶段一自动状态测试
├── worlds/
│   ├── demo_clear.wbt               # 阶段一：目标 only
│   ├── demo_blocked.wbt             # 阶段一：目标 + 障碍
│   ├── stage2_lab.wbt               # 阶段二：空地 + 目标
│   ├── stage2_obstacle.wbt          # 阶段二：空地 + 目标 + 障碍
│   ├── stage2_multi_obstacle.wbt    # 2.4×2.4 m + 3 个 0.18 m 障碍（多次避障演示）
│   ├── stage2_random_obstacles.wbt  # 固定 seed=7，随机多障碍
│   ├── stage2_random_seed_*.wbt     # 10 个随机布局
│   ├── stage2_scenario_*.wbt        # 6 个固定测试场景
│   └── diagnostics/                 # 早期诊断世界
├── controllers/
│   ├── robot_controller/
│   │   ├── robot_controller.py
│   │   ├── runtime.ini
│   │   └── logic/
│   │       ├── robot.py             # 同步自 Linux src/robot.py
│   │       └── kinematics.py        # 同步自 Linux src/kinematics.py
│   ├── motion_controller/
│   │   ├── motion_controller.py     # 阶段二适配层
│   │   └── runtime.ini
│   ├── avoid_controller/
│   │   ├── avoid_controller.py      # 随机多障碍状态机适配层
│   │   └── runtime.ini
│   ├── avoid_supervisor/
│   │   ├── avoid_supervisor.py      # 真值、障碍位置、碰撞日志
│   │   └── runtime.ini
│   ├── session_supervisor/
│   │   └── session_supervisor.py
│   └── probe/
│       ├── probe.py
│       └── runtime.ini
├── docs/
│   └── stage2_navigation_learning.md
└── logs/
    ├── motion_controller.log        # 生成
    ├── session_supervisor.log       # 生成
    ├── stage2_*.log                 # 阶段二证据
    └── diagnostics/                 # 调查产物
```

## 逻辑同步规则

权威 Linux 文件：

```text
/home/airpen/projects/simulate-robot/src/robot.py
/home/airpen/projects/simulate-robot/src/kinematics.py
```

Windows 副本：

```text
D:\A.me\Simulate robot\webots\controllers\robot_controller\logic\robot.py
D:\A.me\Simulate robot\webots\controllers\robot_controller\logic\kinematics.py
```

当前 `kinematics.py` 的 SHA256（两侧一致）：

```text
dd540fdceb5f6043d706f6de526e83c76258068d6e0f41500b75725275c98d71
```

刷新（Git Bash）：

```bash
cp /home/airpen/projects/simulate-robot/src/robot.py \
   "/mnt/d/A.me/Simulate robot/webots/controllers/robot_controller/logic/robot.py"

cp /home/airpen/projects/simulate-robot/src/kinematics.py \
   "/mnt/d/A.me/Simulate robot/webots/controllers/robot_controller/logic/kinematics.py"
```

不要手改 Windows 副本；先改 Linux 权威文件，再同步。

## 范围与限制

- 阶段二导航是“转向—直走”的 bang-bang 控制，没有 PID、速度规划或轨迹跟踪。
- 位置来自轮式里程计，没有全局定位/SLAM；导航真值误差约 1.7–2.8 cm，不能外推到长距离。
- 避障是固定左转规则，只验证一个障碍场景；不处理动态障碍、狭窄通道、死角。
- 30° 小角度转向受一步约 3.67° 的量化限制，实测差 3.70°。
- 只使用 `ps0`/`ps7` 两个前方传感器；没有侧后方感知。
- 没有 ROS 2、SLAM、CUDA、Docker、LLM 或多 Agent。
- Notion 学习文档已写入“项目 / Simulate Robot”项目页，含阶段一、阶段二两个子页；本地 Markdown：
  - 阶段一：`/home/airpen/projects/simulate-robot/docs/stage1_webots_learning.md`
  - 阶段二：`D:\A.me\Simulate robot\docs\stage2_navigation_learning.md`

## 下一步

1. 加入轮速闭环/PID 和接近目标减速，提高转向/距离精度。
2. 把基础避障升级为左右传感器比较 + 简单障碍记忆。
3. 做多航点导航和轨迹跟踪（Pure Pursuit 或简单曲线）。
4. 把 Webots 场景封装成一条命令跑完的自动化回归测试，自动解析 Supervisor 真值并断言误差。
5. 后续内容更新时同步本地 Markdown 与 Notion 项目页。
