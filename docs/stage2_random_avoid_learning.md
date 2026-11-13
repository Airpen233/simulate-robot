# 阶段二改进：随机多障碍与基础自主避障

> 项目：Simulate Robot  
> 本轮目标：在已有差速运动学、里程计和目标点导航基础上，加入可复现的随机多障碍世界与有明确状态机的左右选择/受限后退避障。  
> 环境：Webots R2025a、e-puck、Python 3.12.10。  
> 日期：2026-11-02。  
> 文档状态：本地 Markdown；Notion 页面已写入并 fetch 校验：https://app.notion.com/p/40c3f761570d815b9de8edc9b4ff9a55  
> 配套报告：`STAGE2_RANDOM_AVOID_REPORT.md`

## 1. 本轮目标与原始问题

上一轮的多障碍实验暴露了两个问题：

1. 固定“停—左转—前进—恢复”规则虽然能重复触发，但多次避障后真实误差达到 7.6–12.0 cm，未达到 3 cm 目标。
2. 机器人没有真正的左右评估，也没有后退；它只是按固定动作重复，容易在障碍前振荡。

本轮要回答三个问题：

- 能否生成可复现、有安全间距、仍保留通路的随机多障碍世界？
- 能否用 `ps0–ps7` 做左右通行性比较，而不是无条件左转？
- 多次避障后误差如何变化？哪些失败是“控制失败”，哪些是“状态估计失败”？

本轮不引入 ROS 2、SLAM、视觉、LLM 或新依赖；不使用 Supervisor 真值参与控制。

## 2. 世界文件与障碍生成方式

### 2.1 场地尺寸冲突与最小调整

任务建议 1.6×1.6 m，但 `RectangleArena` 以原点为中心，1.6 m 场地的右墙在 x=0.8；目标 `(1.0,0)` 在墙外 0.2 m，物理不可达。经确认采用 **2.2×2.2 m**：目标距墙 0.1 m，再留机器人半径和安全余量。e-puck 模型、轮半径、轮距均未改。

### 2.2 文件

| 文件 | 内容 |
|---|---|
| `worlds/stage2_random_obstacles.wbt` | 固定 seed=7，4 个障碍 |
| `worlds/stage2_random_seed_1..10.wbt` | 10 个随机布局 |
| `worlds/stage2_scenario_clear.wbt` | 无障碍 |
| `worlds/stage2_scenario_front.wbt` | 单个正前方障碍 |
| `worlds/stage2_scenario_left_blocked.wbt` | 左侧偏移障碍 |
| `worlds/stage2_scenario_right_blocked.wbt` | 右侧偏移障碍 |
| `worlds/stage2_scenario_both_blocked.wbt` | 前 + 左右障碍，后向留空 |
| `worlds/stage2_scenario_no_path.wbt` | 近似包围的紧场景 |

生成器：`tools/generate_random_world.py`，只用标准库。

### 2.3 约束

- 4–6 个立方体，边长 0.12–0.18 m。
- 不与起点/目标/墙体重叠；障碍之间至少 0.08 m 表面间距。
- 随机布局必须至少有一个障碍位于起点—目标走廊附近（`0.2 ≤ x ≤ 0.9`、`|y| ≤ 0.22`），否则替换一个障碍，避免“随机世界完全没有挑战”。
- 用 0.05 m 网格 BFS 检查通路，障碍按 `robot_radius + 0.02 m` 膨胀；没有通路就拒绝重采样。
- 每个世界写 sidecar JSON：seed、障碍坐标/尺寸、目标、`path_found`。
- 生成 20 个种子的自检通过（`SELF_TEST_OK`）。

### 2.4 Webots 项目根目录的坑

Webots 打开 `worlds/scenarios/xxx.wbt` 时显示 **(No Project)**，不会到 `webots/controllers` 找控制器，导致没有日志。所有生成世界必须直接放在 `webots/worlds/` 下；本轮已改到根目录。

## 3. 状态机和状态转换图

### 3.1 状态

| 状态 | 作用 |
|---|---|
| `NAVIGATE` | 朝目标；航向误差大时原地转，否则前进 |
| `BRAKE` | 前方危险，停车 0.10 s |
| `EVALUATE` | 比较左右原始读数，选择方向/后退/失败 |
| `TURN_LEFT` / `TURN_RIGHT` | 原地转 0.90 s（约 103°） |
| `MOVE_AROUND` | 以 3.0 rad/s 轮速前进 2.50 s（约 0.15 m） |
| `REASSESS` | 停车 0.10 s，重读前方 |
| `BACKUP` | 仅后向安全时，低速后退 0.80 s（约 0.048 m） |
| `RECOVER` | 原地转回目标方向 |
| `REACHED` | 里程计距离 ≤ 0.02 m，停止 |
| `BLOCKED` / `STUCK` | 无法安全继续 / 超过尝试上限 |
| `TIMEOUT` / `ERROR` | 24 s 超时 / 异常 |

### 3.2 转换

```text
NAVIGATE --front>=120--> BRAKE --0.1s--> EVALUATE
EVALUATE --方向可选--> TURN_x --0.9s--> MOVE_AROUND --2.5s--> REASSESS
REASSESS --front>=120--> EVALUATE（记录 last_failed）
REASSESS --front<120--> RECOVER --航向对准--> NAVIGATE
EVALUATE --两侧都危险或重复失败且后向安全--> BACKUP --0.8s--> REASSESS
EVALUATE --后向不安全或后退上限--> BLOCKED
EVALUATE --尝试>8--> STUCK
NAVIGATE --距离<=0.02--> REACHED
任意 --24s--> TIMEOUT
```

### 3.3 防死循环

- `max_avoid_attempts=8`：EVALUATE 次数上限。
- `max_backup_attempts=1`：最多一次受限后退。
- `max_same_direction_attempts=2`：同一方向连续两次失败后，若另一侧可通行则换边；若一侧始终不可通行，则在允许时进入 BACKUP。
- `last_failed` 记录最近失败方向，下一轮优先另一边。
- 所有终止状态都先停车。

## 4. 传感器如何参与左右方向选择

### 4.1 官方 e-puck 布局

| 组 | 传感器 | 位置 |
|---|---|---|
| 前 | `ps0` / `ps7` | 前方右/左 |
| 左 | `ps5` / `ps6` | 左侧/左前 |
| 右 | `ps1` / `ps2` | 右前/右侧 |
| 后 | `ps3` / `ps4` | 斜后右/斜后左 |

原始读数越大越近。左右选择用“原始值越小越安全”，不是把读数当成米。

### 4.2 选择规则

1. 左 < `side_block` 且右 ≥ `side_block` → 左转。
2. 右 < `side_block` 且左 ≥ `side_block` → 右转。
3. 两侧都 ≥ `side_block` → 不转；后向安全则 BACKUP，否则 BLOCKED。
4. 两侧都可通行：
   - 若 `last_failed` 是目标侧，选另一侧；
   - 若目标侧连续两次，选另一侧；
   - 若一侧比另一侧低超过 `side_margin`，选更空的一侧；
   - 否则优先目标侧（航向误差符号）。
5. `side_block=200`、`side_margin=30` 是初始工程阈值，实际值由固定场景日志校准；不是物理距离。

### 4.3 限制

- 单障碍正前方时，左右读数通常都低（约 65–75），选择主要落在“目标侧”，不是真正比较出左右阻塞。
- 偏移 0.10 m 的障碍也不一定让侧向传感器明显升高；本轮 `left_blocked/right_blocked` 场景成功，但方向原因是“目标侧”，不是“侧向读数明显阻塞”。这点必须如实记录，不能宣称已实现强鲁棒侧向感知。

## 5. 后退安全条件与失败处理

### 5.1 后向传感器真相

e-puck 没有正后方传感器，只有 `ps3/ps4` 两个斜后传感器。`rear = max(ps3,ps4)` 只是“斜后方估计”，不是“后方无碰撞保证”。

### 5.2 BACKUP 条件

同时满足：

- `rear < rear_clear`（初始 80）；
- `backup_attempts < 1`；
- 状态机处于“两侧都危险”或“同一方向重复失败”；
- 低速 `-3.0 rad/s`（约 -0.06 m/s）、0.80 s、约 4.8 cm；
- 后退后立即 REASSESS。

如果 `rear ≥ 80`，不后退，直接 `BLOCKED`。绝不把“没有检测到后方障碍”表述成“后方安全”。

### 5.3 失败处理

- 尝试超过 8 次 → `STUCK`。
- 后退用尽且仍无法继续 → `BLOCKED`。
- 24 s → `TIMEOUT`。
- 所有情况都停车并写日志；不靠继续撞墙来“尝试”。

## 6. 关键代码逐段解释

### 6.1 纯逻辑 `src/avoidance.py`

- `SensorSnapshot.front/left/right/rear()`：把 8 个原始值分组；非有限值按 0 处理。
- `choose_turn_direction()`：先判单侧可通行，再判双侧；用 `last_failed`、`same_direction_count`、`side_margin` 避免死循环。
- `can_backup()`：只做后向阈值判断；注释明确“必要不充分”。
- `AvoidStateMachine.tick()`：时间驱动；返回 `AvoidDecision`，包含状态、动作、原因、原始读数、计数。
- 反转失败方向后，若同方向连续失败且后向安全，优先 BACKUP；这条规则是本轮针对“侧向看似可通行、实际反复卡住”的补丁。

### 6.2 适配层 `controllers/avoid_controller/avoid_controller.py`

- 读取 `ps0..ps7` 和轮编码器；`Odometry` 与上一轮相同（有效 `r=0.0200`、`L=0.058`，未改标定）。
- 每个 32 ms 调 `machine.tick(now, snapshot, distance, heading_error)`。
- 动作映射：`DRIVE`（对准目标或前进）、`SPIN_LEFT/RIGHT`、`SPIN_TO_TARGET`、`FORWARD_SLOW`、`BACKWARD_SLOW`、`STOP`。
- 日志：`SCENE`（sidecar JSON）、`CONFIG`、`SENSOR_MAP`、每次状态变化的 `DECISION`（原始 ps、front/left/right/rear、位姿、距离、误差、计数、原因）、每 0.5 s `TRACE`、终止 `SUMMARY` 和 `RESULT`。
- 超时 24 s；所有终止先停车。

### 6.3 Supervisor `controllers/avoid_supervisor/avoid_supervisor.py`

- 只做验证：读取 `E_PUCK` 真值、真实 yaw、障碍位置。
- 启用 `enableContactPointsTracking`，过滤掉轮-地面接触，只统计与 `OBSTACLE1..6` 的接触；这是避免“clear 场景 782 次假碰撞”的关键修复。
- 每 0.5 s 记录 `POSE`；25 s 输出 `RESULT: true_end pos=[...] yaw=... error=... collision_samples=...`。
- 不参与控制，不把真值写入控制器。

### 6.4 生成器、运行器、汇总

- `generate_random_world.py`：固定/随机/场景世界 + JSON；BFS 通路检查；20 个种子自检。
- `run_avoid.ps1`：只结束 Webots 进程，不误杀其他 Python；设置环境变量、启动、等待、复制日志。
- `run_avoid_suite.ps1`：固定 7 个和随机 10 个场景批量跑。
- `summarize_runs.py`：解析 `SUMMARY`、`RESULT`、`true_end`，输出 `summary.csv` 和 Markdown 表。

## 7. 实际实验数据和失败案例

### 7.1 测试

- 原有 22 个测试 + 新增 21 个避障测试 = **43/43 通过**。
- 生成器 20 个种子自检通过。

### 7.2 固定场景（7 次）

| 场景 | 控制器 | 真值误差 | AVOID/尝试 | 转向 | 后退 |
|---|---|---|---|---|---|
| clear | reached | 1.70 cm | 0 | 0 | 0 |
| front | reached | 2.95 cm | 1 | 1 | 0 |
| left_blocked | reached | 2.42 cm | 1 | 1 | 0 |
| right_blocked | reached | 2.41 cm | 1 | 1 | 0 |
| both_blocked | timeout | 74.68 cm | 5 | 4 | 1 |
| no_path | timeout | 81.01 cm | 5 | 4 | 1 |
| fixed seed7 | reached | 1.70 cm | 0 | 0 | 0 |

`fixed seed7` 虽然布局有 4 个障碍，但都不足以触发前向阈值，实际仍是直走；这说明“有障碍”不等于“有挑战”，随机布局必须检查是否覆盖走廊。

### 7.3 随机场景（10 次）

| seed | 控制器 | 真值误差 | 备注 |
|---|---|---|---|
| 1 | reached | 1.89 cm | 0 碰撞 |
| 2 | reached | 3.26 cm | 略超 3 cm |
| 3 | reached | 2.47 cm | 0 碰撞 |
| 4 | reached | **45.03 cm** | **假成功** |
| 5 | reached | 1.70 cm | 0 碰撞 |
| 6 | reached | 2.43 cm | 0 碰撞 |
| 7 | reached | 1.70 cm | 0 碰撞 |
| 8 | reached | 4.19 cm | 0 碰撞 |
| 9 | timeout | 44.64 cm | 4 次转向、0 后退 |
| 10 | reached | 1.70 cm | 0 碰撞 |

### 7.4 总体

- 测试总数：**17**（7 固定 + 10 随机）。
- 控制器 `reached`：**14/17**。
- Supervisor 真值 ≤3 cm：**11/17（64.7%）**。
- 碰撞：**0/17**。
- `timeout`：**3/17**（both_blocked、no_path、seed9）。
- 后退：2 次；避障尝试/转向计数见 `logs/random_avoid/summary.csv`。
- 真值误差（全部 17 次）：平均 **16.23 cm**，最大 **81.01 cm**。
- 真值误差（仅控制器 reached 的 14 次）：平均 **5.39 cm**，最大 **45.03 cm**。
- 真值 ≤3 cm 的 11 次：平均约 **2.10 cm**。

### 7.5 代表性失败：seed 4 假成功

控制器：

```text
RESULT: reached target=(1.0,0.0) pose_est=(0.982,0.000,0.000) distance=0.018
```

Supervisor：

```text
RESULT: true_end pos=[0.54969,-0.00043] yaw=0.0000
target=(1.0,0.0) error=0.45031 collision_samples=0
```

机器人实际只到 x≈0.55，但轮子顶住/擦过障碍时打滑，编码器仍在转，里程计把行程虚增到 0.982，于是控制器误判 `reached`。这不是“碰巧成功”，而是**状态估计失败**；Supervisor 真值把它抓住了。当前控制器没有独立的堵转/碰撞检测，因此会出现这种假成功。

### 7.6 both_blocked / no_path

两次都 timeout：5 次 EVALUATE、4 次转向、1 次 BACKUP、0 碰撞。侧向传感器在该布局下仍显示“可通行”，机器人反复左右转，无法脱困；后退 4.8 cm 也不足以改变局面。它们被保留为失败案例，不伪称通过。

## 8. 为什么多次避障会累积航向和里程计误差

1. **航向误差**：每次原地转 0.9 s 都靠编码器航向判断；转向停止有量化，反复转向后航向估计偏离真值。
2. **轮滑**：避障时轮子可能顶住障碍或擦边，编码器转但车体没走；里程计把轮子转动当成位移。
3. **停止判据**：控制器在“估计距离 ≤2 cm”就停；估计误差会直接变成真实误差。
4. **累积**：每次避障增加一次转向/直走，误差叠加；单障碍 2.95 cm，多障碍可到 7.6–12 cm，甚至 seed4 的 45 cm 假成功。
5. **没有外部定位**：没有 GPS/视觉/地图校正；Supervisor 只做事后验证，不参与控制。

## 9. 当前实现的能力边界

**已实现且已验证：**

- 2.2×2.2 m 随机/固定世界，4–6 个障碍，BFS 通路检查，固定种子可复现。
- 纯逻辑状态机 + 21 个新测试；43/43 全部通过。
- 左右传感器比较、目标侧优先、失败记忆、同方向上限。
- 受限后退（斜后传感器、低速、限次、立即重评估）。
- 独立 Supervisor 真值、障碍位置、过滤后的障碍碰撞日志。
- 17 次固定/随机实验全部保存日志、种子和布局。

**已实现但仅部分验证：**

- 单障碍/左右镜像避障成功；`both_blocked`/`no_path` 失败。
- 后向安全只有斜后 `ps3/ps4`，不是正后方保证。
- 随机 10 组中 6 组真值 ≤3 cm，成功率 60%；不能宣称鲁棒。
- 侧向“阻塞”在固定场景中并不总是明显，部分方向选择由目标侧决定。

**计划但未完成：**

- 堵转/碰撞检测与“假 reached”防护。
- 轮速闭环/PID、减速段、轨迹跟踪。
- 更多传感器/正后方距离、地图/路径规划。
- 10 组以上随机种子、重复实验统计。
- Notion 归档（本轮页面是否成功见最终报告）。

**受传感器/算法限制无法可靠实现：**

- 仅凭 8 个红外传感器做全局最优避障。
- 仅凭轮式里程计做 3 cm 级精确定位，尤其在多次碰撞/打滑后。
- 正后方绝对安全判断。

## 10. 下一步改进方向

1. **假 reached 防护**：监测“指令速度高但真实位移不增”的堵转；用接触/侧向高读数触发 BRAKE；不要只信里程计。
2. **轮速闭环**：编码器速度 PI 控制，降低打滑和起停冲击。
3. **接近目标减速**：分段速度或 PID，减小停止误差。
4. **更好的侧向感知**：使用 `ps1/ps2/ps5/ps6` 的连续值校准，建立“距离-读数”曲线；不要只用阈值。
5. **后退安全**：增加正后方距离传感器/超声波（仿真中可用 `DistanceSensor`），或只用“前进-转向”策略，不盲目后退。
6. **路径规划**：栅格/A* 或 Bug 算法；当前只是局部规则。
7. **定位**：GPS/compass 对照，再考虑 EKF/SLAM；3 cm 目标需要外部校正。
8. **自动化实验**：固定 20+ 随机种子、重复 3 次、自动统计成功率/碰撞/误差；失败样本必须保留。

## 11. 自测题与小型练习

### 自测题

1. 为什么 1.6×1.6 m 不能容纳目标 (1.0,0)？  
   答：场地以原点为中心，半宽 0.8；目标在墙外 0.2 m。
2. 为什么左右选择用“原始值更小”而不是“值更大”？  
   答：e-puck 红外读数越大越近；更小代表更空。
3. 为什么后向只有 `ps3/ps4` 时不能保证后退安全？  
   答：它们位于斜后方，正后方存在盲区；低读数只是“未检测到”，不是“没有障碍”。
4. 为什么 seed4 控制器 reached 但真值只有 0.55 m？  
   答：轮子打滑/顶住障碍，编码器仍转，里程计虚增；控制器没有独立堵转检测。
5. 为什么 `both_blocked` 会 timeout？  
   答：侧向传感器仍显示可通行，状态机反复转向；后退距离不足，无法脱困。
6. 为什么固定 seed7 有 4 个障碍却 0 次避障？  
   答：障碍不在前向触发走廊内；有障碍不等于有挑战。
7. 为什么碰撞统计要过滤接触点？  
   答：`getContactPoints` 包含轮-地面正常接触；不过滤会把正常接地当成碰撞（clear 场景曾出现 782 次假碰撞）。
8. 3 cm 目标为什么不能预先保证？  
   答：轮式里程计有滑移和累积误差；没有外部定位；多次避障会放大误差。

### 练习

1. 给 `SensorSnapshot` 增加一个 `rear_center` 字段（假设新增传感器），修改 `can_backup` 并补测试。
2. 把 `side_block=200` 改成 150/250，跑 `left_blocked/right_blocked`，记录方向选择原因变化。
3. 给控制器加“堵转检测”：连续 0.5 s 指令速度 >0 但编码器位移 <1 mm，则 BRAKE/STUCK；先写失败测试。
4. 把 `MOVE_AROUND` 改成按侧向传感器连续调节（比例转向），比较固定时长版本的误差。
5. 用 20 个新随机种子跑同一套流程，统计成功率、碰撞、误差；保留所有失败日志。
6. 把 `both_blocked` 设计成真正有后退+绕行通路的布局，验证 BACKUP 后能否脱困。
