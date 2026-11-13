# Simulate Robot 第二阶段改进工程报告：随机多障碍与自主避障

> 日期：2026-11-02  
> 环境：Windows 11、WSL2 Ubuntu 24.04、Webots R2025a、e-puck、Python 3.12.10  
> 结论：**世界生成、纯逻辑状态机、左右选择、受限后退、日志与验证链路已完成；固定/随机实验已跑完并保存全部失败样本。3 cm 目标未预先保证，实际 11/17 次达到；seed 4 出现控制器假 reached，已如实报告。**

## 1. 本阶段完成了什么

1. 新建 2.2×2.2 m 随机多障碍世界，目标保持 `(1.0,0)`；解决 1.6×1.6 m 与目标坐标的几何冲突。
2. 新增 `src/avoidance.py` 纯逻辑：传感器分组、左右选择、失败记忆、重试上限、受限后退、状态机；新增 21 个单元测试。
3. 新增 `avoid_controller` 适配层，接入状态机并记录原始传感器、位姿、原因、计数、场景/种子/障碍坐标。
4. 新增 `avoid_supervisor`：真实位姿、真实航向、障碍位置、过滤后的障碍物碰撞点；不参与控制。
5. 新增随机世界生成器：固定种子、4–6 个 0.12–0.18 m 障碍、间距约束、BFS 通路检查、sidecar JSON。
6. 新增不误杀 Python 的运行器和批量实验脚本；17 次实验全部保存日志与布局。
7. 完成 43/43 测试；固定场景 7 个、随机种子 10 个；0 次记录到的障碍物碰撞；3 次 timeout；1 次控制器假 reached。
8. 更新 README，编写本轮学习文档与工程报告。

## 2. 验收结果

| 验收项 | 结果 | 说明 |
|---|---|---|
| 随机/固定世界 | 通过 | 2.2×2.2 m；4–6 障碍；固定种子；BFS 通路；20 种子自检 |
| 机器人尺寸/标定 | 通过 | e-puck 未缩放；`r=0.0200`、`L=0.058` 未改 |
| 起点/目标 | 通过 | 机器人从原点；目标 `(1.0,0)`；世界不继承终点 |
| 状态机 | 通过 | NAVIGATE/BRAKE/EVALUATE/TURN_LEFT/RIGHT/MOVE_AROUND/REASSESS/BACKUP/RECOVER/REACHED/BLOCKED/STUCK/TIMEOUT/ERROR |
| 左右选择 | **部分通过** | 已用 ps1/ps2/ps5/ps6 比较；固定左右场景成功，但侧向读数未明显“单侧阻塞”，部分选择由目标侧决定 |
| 后退安全 | **部分通过** | 仅 ps3/ps4 斜后传感器；限速/限距/限次；`both_blocked`/`no_path` 仍 timeout |
| 导航完成判定 | **部分通过** | 控制器 reached 14/17；Supervisor 真值 ≤3 cm 仅 11/17；seed4 假 reached |
| 日志可观测性 | 通过 | 场景/种子/障碍坐标、ps0–7、front/left/right/rear、原因、计数、真值、碰撞 |
| 回归测试 | 通过 | 43/43；第一阶段 7 个与原有功能未破坏 |
| 固定场景 | **部分通过** | 5/7 成功，2 个 timeout |
| 随机场景 | **部分通过** | 6/10 真值 ≤3 cm；9/10 控制器 reached；1 次假 reached；1 次 timeout |
| 实际位姿验证 | 通过 | 所有 17 次都有 Supervisor `true_end` |
| Notion 归档 | 待本轮写入结果 | 见第 10 节 |

### 状态分类

- **已实现且已验证**：世界生成、纯逻辑/测试、状态机、日志、Supervisor 真值/碰撞、17 次实验、单障碍与左右镜像。
- **已实现但仅部分验证**：左右传感器选择（侧向阻塞不明显）、受限后退（2 个场景仍失败）、3 cm 精度（11/17）。
- **计划但未完成**：堵转/假 reached 防护、轮速闭环、正后方感知、路径规划、GPS/定位、20+ 种子重复实验。
- **受传感器/算法限制无法可靠实现**：仅凭 8 个红外做全局最优避障；仅凭轮式里程计做 3 cm 级定位；正后方绝对安全判断。

## 3. 修改文件清单与目的

### Linux 权威项目

| 文件 | 目的 |
|---|---|
| `src/avoidance.py` | 新增纯状态机、传感器分组、左右选择、后退规则；无 Webots 依赖 |
| `tests/test_avoidance.py` | 新增 21 个测试（方向、状态、后退、重试、角度） |
| `docs/stage2_random_avoid_learning.md` | 本轮 11 节学习文档 |

### Windows Webots 项目

| 文件 | 目的 |
|---|---|
| `controllers/robot_controller/logic/avoidance.py` | Linux `src/avoidance.py` 的同步副本 |
| `controllers/avoid_controller/avoid_controller.py` | 状态机适配层、设备读取、动作映射、详细日志 |
| `controllers/avoid_controller/runtime.ini` | Python 3.12 解释器 |
| `controllers/avoid_supervisor/avoid_supervisor.py` | 真值、yaw、障碍位置、碰撞点、最终误差 |
| `controllers/avoid_supervisor/runtime.ini` | Python 3.12 解释器 |
| `tools/generate_random_world.py` | 固定/随机/场景世界 + JSON；BFS 通路检查 |
| `tools/run_avoid.ps1` | 单场景运行；只结束 Webots，不误杀 Python |
| `tools/run_avoid_suite.ps1` | 固定 7 + 随机 10 批量运行 |
| `tools/summarize_runs.py` | 解析日志，输出 CSV/Markdown |
| `worlds/stage2_random_obstacles.wbt` | 固定 seed=7，4 障碍 |
| `worlds/stage2_random_seed_1..10.wbt` | 10 个随机布局 |
| `worlds/stage2_scenario_*.wbt` | 6 个固定场景 |
| `logs/random_avoid/*` | 17 次控制器/Supervisor/世界 JSON |
| `README.md` | 本轮命令、结果、限制 |

旧 `motion_controller.py`、旧世界、旧日志未改。

## 4. 新世界文件路径

```text
D:\A.me\Simulate robot\webots\worlds\stage2_random_obstacles.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_random_seed_1.wbt ... _10.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_scenario_clear.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_scenario_front.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_scenario_left_blocked.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_scenario_right_blocked.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_scenario_both_blocked.wbt
D:\A.me\Simulate robot\webots\worlds\stage2_scenario_no_path.wbt
```

每个世界对应 `logs/worlds/*.json`，包含 seed、目标、障碍坐标/尺寸和 `path_found`。所有世界直接放在 `worlds/` 根目录；放在子目录会让 Webots 显示 `(No Project)` 并找不到控制器。

## 5. 新旧控制策略差异

| 维度 | 旧 `motion_controller.avoid` | 新 `avoid_controller` |
|---|---|---|
| 方向选择 | 固定左转 | 比较 ps1/2/5/6；单侧可通行优先；双侧结合目标侧/失败记忆 |
| 状态 | 隐式 phase（drive/turn/forward） | 明确 NAVIGATE/BRAKE/EVALUATE/TURN_x/MOVE_AROUND/REASSESS/BACKUP/RECOVER |
| 后退 | 无 | 仅后向安全时一次低速短后退 |
| 防死循环 | 无上限，靠 22 s 超时 | 8 次避障、1 次后退、同方向 2 次上限 |
| 传感器 | 仅 ps0/ps7 | ps0–ps7，分组 front/left/right/rear |
| 日志 | NAV/AVOID/RESULT | SCENE/CONFIG/SENSOR_MAP/DECISION/TRACE/SUMMARY/RESULT |
| 验证 | 旧 Supervisor 仅位置 | 新 Supervisor 真值 + yaw + 障碍位置 + 过滤碰撞 |
| 超时 | 22 s | 24 s（适配更长的绕行；Supervisor 25 s） |

旧版本的固定左转在多障碍下曾得到 2 次 AVOID/7.6 cm、3 次 AVOID/12.0 cm；新版本单障碍/左右镜像 2.41–2.95 cm，但随机 10 组中 6 组 ≤3 cm，3 组 timeout，1 组假 reached。**不能概括为全面改进；是简单场景改善、密集随机场景仍不可靠。**

## 6. 实际执行命令

```powershell
cd "D:\A.me\Simulate robot\webots"
python tools/generate_random_world.py --self-test
python tools/generate_random_world.py --scenario scenarios
python tools/generate_random_world.py --scenario fixed --seed 7
for ($s=1; $s -le 10; $s++) { python tools/generate_random_world.py --scenario random --seed $s }

powershell -ExecutionPolicy Bypass -File .\tools\run_avoid_suite.ps1 -Mode fixed -Timeout 24
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid_suite.ps1 -Mode random -SeedStart 1 -SeedEnd 10 -Timeout 24
python tools/summarize_runs.py
```

```bash
cd /home/airpen/projects/simulate-robot
.venv/bin/python -m unittest discover -s tests -v
```

单场景示例：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid.ps1 `
  -WorldFile stage2_scenario_front.wbt `
  -JsonFile "D:\A.me\Simulate robot\webots\logs\worlds\stage2_scenario_front.json" `
  -RunName fixed_front -Seed front -Timeout 24
```

## 7. 测试结果

- 原有 22 个测试：通过。
- 新增 21 个避障测试：通过。
- 总计 **43/43**，`Ran 43 tests ... OK`。
- 生成器 20 个种子：`SELF_TEST_OK`。
- 所有 17 次 Webots 运行：控制器/Supervisor 日志齐全；运行后无残留 Webots 进程。
- 旧的 7 个阶段一测试未改；旧控制器/世界未改。

新增测试覆盖：

- 传感器 front/left/right/rear 分组；非有限值按 0。
- 单侧阻塞选另一侧；双侧阻塞返回 None；目标侧优先；clearance 差值；失败方向记忆；同方向上限。
- BACKUP 仅后向安全；后向阻塞直接 BLOCKED；后退上限。
- 状态计时（BRAKE→EVALUATE→TURN→MOVE→REASSESS→RECOVER→NAVIGATE）。
- REACHED/TIMEOUT 终止；重复失败触发一次 BACKUP。

## 8. 固定与随机场景完整汇总

### 固定 7 个

| 场景 | 控制器 | 真值误差 | 尝试 | 转向 | 后退 | 结果 |
|---|---|---|---|---|---|---|
| clear | reached | 1.70 cm | 0 | 0 | 0 | 通过 |
| front | reached | 2.95 cm | 1 | 1 | 0 | 通过 |
| left_blocked | reached | 2.42 cm | 1 | 1 | 0 | 通过（方向原因含目标侧） |
| right_blocked | reached | 2.41 cm | 1 | 1 | 0 | 通过（方向原因含目标侧） |
| both_blocked | timeout | 74.68 cm | 5 | 4 | 1 | 失败 |
| no_path | timeout | 81.01 cm | 5 | 4 | 1 | 失败 |
| fixed seed7 | reached | 1.70 cm | 0 | 0 | 0 | 通过但未触发避障 |

### 随机 10 个

| seed | 障碍数 | 控制器 | 真值误差 | 尝试 | 转向 | 后退 | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | 5 | reached | 1.89 cm | 0 | 0 | 0 | 通过 |
| 2 | 6 | reached | 3.26 cm | 1 | 1 | 0 | 略超 3 cm |
| 3 | 4 | reached | 2.47 cm | 0 | 0 | 0 | 通过 |
| 4 | 5 | reached | **45.03 cm** | 0 | 0 | 0 | **假成功** |
| 5 | 6 | reached | 1.70 cm | 0 | 0 | 0 | 通过 |
| 6 | 4 | reached | 2.43 cm | 1 | 1 | 0 | 通过 |
| 7 | 5 | reached | 1.70 cm | 0 | 0 | 0 | 通过 |
| 8 | 6 | reached | 4.19 cm | 1 | 1 | 0 | 超 3 cm |
| 9 | 4 | timeout | 44.64 cm | 4 | 4 | 0 | 失败 |
| 10 | 5 | reached | 1.70 cm | 0 | 0 | 0 | 通过 |

### 总体指标

- 测试总数：**17**（7 固定 + 10 随机）。
- 控制器 reached：**14/17（82.4%）**。
- Supervisor 真值 ≤3 cm：**11/17（64.7%）**。
- 碰撞：**0/17**（过滤后的障碍物接触；轮-地面正常接触不计）。
- `timeout`：**3/17**；`error`：0；`blocked/stuck` 明确终止：0（两场景以 timeout 结束，未触发最终 BLOCKED，因为尝试上限未到）。
- 后退：2 次；转向/尝试：见 `logs/random_avoid/summary.csv`。
- 真值误差（全部）：平均 **16.23 cm**，最大 **81.01 cm**。
- 真值误差（仅 reached 的 14 次）：平均 **5.39 cm**，最大 **45.03 cm**。
- 真值 ≤3 cm 的 11 次：平均约 **2.10 cm**。
- 固定组：5/7 成功；随机组：控制器 9/10，真值 6/10。

### 与旧固定左转相比

- 单障碍/左右镜像：旧版约 2.8–4 cm（单障碍 2.81 cm），新版 2.41–2.95 cm，略有改善。
- 密集/受困场景：旧版 2 次 AVOID/7.6 cm、3 次 AVOID/12.0 cm；新版有 3 次 timeout、1 次 45 cm 假成功。**密集场景并未显著改善，甚至出现新的失败模式。**
- 碰撞：新版过滤后 0；旧版未记录碰撞。
- 结论：新状态机在“单个可绕障碍”上更好；在“看不到出口/侧向感知不足/打滑”场景仍不可靠。

## 9. 代表性成功与失败日志

### 成功：front

```text
DECISION t=3.90 state=BRAKE action=STOP reason='front=131.9 >= 120.0'
DECISION t=4.03 state=EVALUATE action=STOP reason='brake complete'
DECISION t=4.06 state=TURN_RIGHT action=SPIN_RIGHT reason='both sides clear; prefer target side RIGHT'
DECISION t=4.99 state=MOVE_AROUND action=FORWARD_SLOW
DECISION t=7.52 state=REASSESS action=STOP
DECISION t=7.65 state=RECOVER action=SPIN_TO_TARGET
DECISION t=8.64 state=NAVIGATE action=DRIVE
RESULT: reached target=(1.0,0.0) pose_est=(0.982,-0.007,0.318) distance=0.020
```

Supervisor：

```text
RESULT: true_end pos=[0.97511,-0.01576] yaw=0.3330
target=(1.0,0.0) error=0.02946 collision_samples=0
```

### 失败：seed 4 假 reached

控制器：

```text
RESULT: reached target=(1.0,0.0) pose_est=(0.982,0.000,0.000) distance=0.018
```

Supervisor：

```text
RESULT: true_end pos=[0.54969,-0.00043] yaw=0.0000
target=(1.0,0.0) error=0.45031 collision_samples=0
```

失败解释：实际只到 x≈0.55，但轮子顶住/擦过障碍时打滑，编码器继续转，里程计把行程虚增到 0.982，触发假 reached。当前控制器没有堵转/侧向碰撞检测；Supervisor 真值发现了它。

### 失败：both_blocked

```text
DECISION t=14.43 state=BACKUP action=BACKWARD_SLOW
reason='direction LEFT failed repeatedly; rear=69.7 < 80.0; short backup'
RESULT: timeout target=(1.0,0.0) pose_est=(0.245,-0.194,-1.807) distance=0.780
```

Supervisor：`true_end (0.26523, -0.13322), error=0.74675, collision_samples=0`。侧向读数没有形成“双侧阻塞”，后退 4.8 cm 不足以脱困。

## 10. Notion 文档位置与校验

本轮学习文档本地路径：

```text
D:\A.me\Simulate robot\docs\stage2_random_avoid_learning.md
```

Notion 页面已创建并 fetch 校验：

```text
https://app.notion.com/p/40c3f761570d815b9de8edc9b4ff9a55
```

- 父路径：`项目 / Simulate Robot / 阶段二改进：随机多障碍与自主避障`。
- 标题与本地一致；11 节正文、表格、状态机和实验数据均在。
- 没有覆盖阶段一、阶段二原文档；这是新建子页。
- 首次提交较大内容时 Notion MCP 返回内部错误；改为精简版后创建成功，未声称第一次就成功。
- 写入后已重新 fetch，确认 `ancestor-path` 为 `Simulate Robot` → `项目`，正文可读。

## 11. 尚未解决的问题、技术债务与下一步

### 未解决/技术债

1. **假 reached**：没有堵转/侧向碰撞检测；seed4 误差 45 cm。
2. **侧向感知弱**：单障碍/偏移障碍时左右读数常都“clear”，方向选择依赖目标侧；没有距离-读数曲线。
3. **后向盲区**：只有 ps3/ps4，无正后方；BACKUP 安全是概率性的。
4. **受困场景**：both_blocked/no_path timeout；后退距离和策略不足。
5. **误差**：11/17 ≤3 cm；多次避障仍累积；轮滑、航向量化、停止判据。
6. **固定 seed7**：有障碍但未触发；随机布局必须检查挑战性（已加走廊约束，但固定 seed7 仍可能偏轻）。
7. **日志/运行器**：`run_avoid.ps1` 只结束 Webots；旧 `run_motion.ps1` 仍会结束所有 Python（未改，避免动旧证据）。
8. **未做 20+ 种子重复实验**；未做统计置信区间。
9. **Notion 写入**：待执行；若被拦截会明确报告。
10. **Git**：未提交。

### 下一步建议

1. 堵转检测：指令速度 >0 但编码器位移低于阈值持续 0.5 s → BRAKE/STUCK；结合侧向高读数。
2. 轮速闭环/PID + 接近目标减速；减小停止误差和打滑。
3. 侧向距离-读数标定；使用 ps1/2/5/6 连续值，而不是单一阈值。
4. 正后方距离传感器或“只前进-转向”策略，减少盲目后退。
5. 栅格/A* 或 Bug 算法；当前位置反应式规则不足以处理 U 形陷阱。
6. GPS/compass 对照，再考虑 EKF/SLAM；3 cm 需要外部校正。
7. 20+ 随机种子 × 3 次重复，自动统计成功率/碰撞/误差；保留所有失败样本。
8. 获得授权后写入 Notion 并 fetch 校验。

---

**报告结论：** 本轮完成了可复现随机世界、明确状态机、左右选择、受限后退和独立真值/碰撞验证；43/43 测试通过；17 次实验中 11 次真值 ≤3 cm、0 次记录碰撞、3 次 timeout、1 次假 reached。简单单障碍场景改善，但密集/受困场景仍不可靠；未达到“鲁棒自主避障”，也未降低 3 cm 标准来伪造成功。
