# Simulate Robot · 项目记忆（本地工作草稿）

> **⚠️ 本文件已降级为本地工作草稿，不再承载项目事实的权威副本。**
> 权威副本：Notion `PS_Knowledge`《技术·Simulate Robot·Webots 避障工程事实》
> https://app.notion.com/p/4173f761570d81c580a8ebd8b592b914
> 迁入日期 2026-11-13，内容一致。本文件保留以便离线查看与快速 grep，**冲突时以 Notion 为准**。
>
> **规则层不在这里，也不在本地任何 AGENTS.md**：系统规则唯一源是 Notion《🏠 工作台》（v1.5 / 2026-11-04）。原「0.2 规则链的真实状态」一节所述指向已失效，保留仅为历史。
> 项目卡：https://app.notion.com/p/4173f761570d81f5b170cbf87cceca1a
> 代码仓库：https://github.com/Airpen233/simulate-robot（私有，首次提交 0864dcc）
> 最后核对：2026-11-09（实跑验证，见 0.4）。

---

## 0.1 这是什么项目

Webots R2025a + e-puck 差速小车的**两阶段仿真工程**，本质是一门机器人入门课/自学项目：

- **阶段一**：官方 e-puck 模型、Python 控制器、直线前进、距离传感器、遇障停止、Supervisor 真值验证。
- **阶段二**：差速运动学、轮式里程计、航向角闭环、指定角度/距离、目标点导航、规则式避障。
- **阶段二改进**：可复现随机多障碍世界 + 显式状态机避障（NAVIGATE/BRAKE/EVALUATE/…/BACKUP）+ 独立真值验证。

目标点始终是 `(1.0, 0.0)`，场地 2.2×2.2 m。**不涉及** ROS 2 / SLAM / 视觉 / LLM / 多 Agent。

## 0.2 规则链的真实状态（重要，别被误导）

1. `D:\A.me\AGENTS.md` → 指向 `D:\A.me\airpen-toolbox\AGENTS.md` 当「唯一规则源」。
2. 但 `airpen-toolbox\AGENTS.md` 文件头自己声明：**它已不是规则源，只作草稿与历史**；现行唯一规则源是 Notion《Personal OS 系统规则（Agent 必读）》`https://app.notion.com/p/4063f761570d81a5b1e0cfc7c0332eb7`（2026-10-30 裁定），**云端为准，本地不具效力**。
3. 因此：只管本项目事实，规则去 Notion 读；本地那两份文件不提供效力。

从章程沿用、与本项目直接相关的三条：**① 一个内容只有一个唯一可写源 ② 删除/移动、改计划、花钱须主人确认 ③ 降级不编造，抓取失败就说哪项没查**。

## 0.3 目录地图

```
D:\A.me\Simulate robot\
├── AGENTS.md                       ← 本文件（本地草稿；权威副本在 Notion 知识库）
├── STAGE1_WEBOTS_REPORT.md         ← 阶段一工程报告（验收清单/环境/校准）
├── STAGE2_WEBOTS_REPORT.md         ← 阶段二工程报告（含技术债、未完成项）
├── STAGE2_RANDOM_AVOID_REPORT.md   ← 随机多障碍改进报告（17 次实验完整数据）
├── docs\
│   ├── WEBOTS_BEGINNER_START.md    ← 初学者一键启动/观察/取日志（给非技术读者）
│   ├── stage2_navigation_learning.md   ← 阶段二详版教材（1454 行，18 节 + 自测题）
│   └── stage2_random_avoid_learning.md ← 随机避障详版教材（334 行，11 节）
└── webots\
    ├── README.md                   ← 工程主 README（结构/结果/10 条技术结论）
    ├── START_RANDOM_AVOID.bat      ← 初学者一键启动（GUI，暂停开局）；--validate 只做静态检查
    ├── run_demo.ps1                ← 阶段一运行器
    ├── controllers\                ← robot_controller / motion_controller / avoid_controller /
    │                                  avoid_supervisor / session_supervisor / probe
    │   └── robot_controller\logic\ ← robot.py / kinematics.py / avoidance.py（**Linux 权威副本**）
    ├── worlds\                     ← 所有 .wbt 必须在**这一层**（放子目录会 (No Project)）
    ├── tools\                      ← 生成器 / 运行器 / 汇总脚本
    └── logs\                       ← 运行日志；random_avoid\ 是归档区；worlds\ 是 sidecar JSON
        └── random_avoid\INDEX.md   ← **全部 33 组运行的索引与参数代分析**（自动生成，勿手改）
```

**Linux 权威项目**（逻辑的源头，Windows 侧只是副本）：
`\\wsl$\Ubuntu-24.04\home\airpen\projects\simulate-robot\`（`src/*.py`、`tests/`、`.venv`）

## 0.4 环境事实（已实测）

| 项 | 值 |
|---|---|
| Webots | R2025a，`C:\Program Files\Webots\msys64\mingw64\bin\webots.exe` |
| Python | 3.12.10，`C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe`（两个 runtime.ini 都指向它） |
| PowerShell | 5.1.26100 |
| WSL | Ubuntu-24.04（`wsl -d Ubuntu-24.04 -e bash -lc ...`）；输出有 NUL/乱码需 `2>&1 \| tr -d '\000'` |
| 测试 | WSL `.venv/bin/python -m unittest discover -s tests` → **Ran 43 tests, OK**（2026-11-09） |
| 生成器自检 | `python tools/generate_random_world.py --self-test` → `SELF_TEST_OK` |
| Git | **已建立**：`Airpen233/simulate-robot`（私有），Windows 侧首次提交 `0864dcc`（2026-11-13）。仓库级代理需设 `http.proxy=127.0.0.1:7897`（全局配置指向失效端口 31180/31181）。WSL 纯逻辑仓 `/home/airpen/projects/simulate-robot` 仍零 commit |

## 0.5 关键常量（改动前先看这里）

```
WHEEL_RADIUS_M = 0.0200      # 有效值，非名义 0.0205
WHEEL_BASE_M   = 0.058       # 有效值，非名义 0.052
MAX_WHEEL_SPEED = 4.0   SPIN_WHEEL_SPEED = 2.0   SLOW = 3.0
POSITION_TOLERANCE_M = 0.02     HEADING_TOLERANCE = 5°
PS_STOP_THRESHOLD = 120.0       TIMEOUT_S = 24（控制器）/ 25（Supervisor simulationQuit）
side_block = 200   side_margin = 30   rear_clear = 80
turn 0.90 s(≈103°)  move_around 2.50 s(≈0.15 m)  backup 0.80 s(≈0.048 m)
max_avoid_attempts = 8   max_backup_attempts = 1   max_same_direction = 2
```

## 0.6 结果现状（不要重新编，也不要美化）

17 次固定+随机实验：控制器自报 `reached` **14/17**；Supervisor 真值 ≤3 cm **11/17（64.7%）**；障碍碰撞 **0**；`timeout` **3**（both_blocked、no_path、seed9）；**1 次假 reached**（seed 4：控制器估 x=0.982，真值 x=0.55，误差 45.03 cm，因轮子顶障碍打滑使里程计虚增）。

结论口径：**单障碍/左右镜像场景可用（2.41–2.95 cm），密集与受困场景不可靠**。不得概括为「已实现鲁棒自主避障」，也不得下调 3 cm 标准来伪造通过。

> 全部数字已用 `summary.csv` 复核：17 行 / 固定 7 / 随机 10 / reached 14 / ≤3cm 11 / 碰撞 0 / timeout 3。超 3 cm 的 3 次 = `random_seed_2`(3.26cm)、`random_seed_4`(45.03cm 假成功)、`random_seed_8`(4.19cm)。

**归档区里有三代参数混放**（这是个真陷阱）：`logs/random_avoid/` 33 组运行中，验收数据全是 **A 代**（turn 0.90 / move 2.50 / backup 0.80，与当前 `AvoidConfig` 默认一致）；`test_*` 系列是 **B/C 代**早期调参（`move_duration_s=0.5` 等）。**B/C 代数字不能与 A 代对比**——例如 `test_front` 的 timeout 是在绕行距离只有 A 代 1/5 的参数下发生的，不代表当前参数也失败。详见 `webots/logs/random_avoid/INDEX.md`。

## 0.7 校准过的坑（按踩坑成本排序，来自 README + 学习文档 14 节）

1. **`EXTERNPROTO` 必须 HTTPS**（用 R2025a raw GitHub URL）；写 `webots://` 时窗口能开但 e-puck 不实例化、控制器不启动。
2. **e-puck 前进轴是 +X**，平面是 X–Y，yaw 绕 +Z；Supervisor yaw = `atan2(R10, R00)` = `atan2(orientation[3], orientation[0])`。用 `orientation[1]/[2]` 会把方向弄反。
3. **必须 `Robot { supervisor TRUE }`**；裸 `Supervisor {}` 节点在本世界不启动控制器。
4. **世界文件路径含空格必须加引号**（`Start-Process -ArgumentList` 不会自动加）。
5. **`.wbt` 必须直接放 `worlds/`**，放 `worlds/scenarios/`、`worlds/generated/` 会让 Webots 显示 `(No Project)` 且找不到控制器。这两个子目录是历史残留，不要用。
6. **控制器 `reached` 不是验收证据**，只认 Supervisor `true_end ... error=`。
7. **证据日志不要复用文件名**：每次运行结束立即归档到带场景名+时间戳的文件；引用前 `grep` 核对目标坐标和 `RESULT` 是否匹配（本项目曾把右方向导航日志误存成避障日志）。
8. **碰撞统计必须过滤轮-地面接触**（`enableContactPointsTracking` + 只看 `OBSTACLE*`），否则 clear 场景会报 782 次假碰撞。
9. **`run_avoid.ps1` 只结束 Webots 进程**（安全）；但旧的 `run_motion.ps1` 会杀掉所有 python——不要用它跑新实验。
10. **里程计标定不可跳**：名义 r/L 会带来直线 +2.3%、旋转 +10% 的偏差。
11. **`stage2_obstacle.wbt` 保存了上次终点位姿**（translation ≈ `0.885, -0.357`，含 `hidden` 状态），直接重跑会从终点附近开始。这是旧证据，**未经确认不要改**。
12. Webots 启动慢是正常的（联网拉官方 PROTO）。

## 0.8 常用命令（全部已验证）

```powershell
# 静态检查（不启动仿真，安全）
cd "D:\A.me\Simulate robot\webots"
cmd /c "START_RANDOM_AVOID.bat --validate"        # 结尾出现 VALIDATE_OK

# 单场景无头运行（推荐给 agent 用；约 34 s）
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_avoid.ps1 `
  -WorldFile stage2_scenario_front.wbt -RunName <自定名> -Timeout 24 -WaitSeconds 34

# 批量：固定 7 + 随机 10
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid_suite.ps1 -Mode all -Timeout 24
python tools/summarize_runs.py                    # 出 summary.csv + Markdown

# 初学者 GUI 观察
双击 START_RANDOM_AVOID.bat → 点 Webots 顶部 Run
```

成功判据：输出里同时有 `CONTROLLER_RESULT=RESULT: ...` 和 `SUPERVISOR_RESULT=RESULT: true_end ... error=...`，`STILL_RUNNING=False`。

## 0.9 当前技术债 / 下一步（按优先级）

1. **假 reached 防护**：指令速度 >0 但编码器位移 <1 mm 持续 0.5 s → BRAKE/STUCK；这是最大风险点（seed 4）。
2. **轮速闭环/PID + 接近目标减速**，减小停止误差与打滑。
3. **侧向感知标定**：ps1/ps2/ps5/ps6 建距离-读数曲线，别只用阈值 200；目前左/右场景的成功其实部分靠「目标侧优先」而非真正比较出阻塞。
4. **正后方盲区**：只有 ps3/ps4，BACKUP 的安全性是概率性的，不能宣称「后方安全」。
5. **受困场景**：both_blocked / no_path 仍 timeout（5 次 EVALUATE、4 次转向、1 次后退）。
6. 20+ 随机种子 × 3 次重复 + 自动统计；未做。
7. 转向/距离实验的逐次日志未归档（阶段二的证据缺口）。
8. 未做可视化/录屏验证（一直 `--no-rendering --batch`）。

## 0.10 已归档但异常的记录 / 杂物（本轮盘点发现）

**a) 截断的 Supervisor 日志**：`webots\logs\random_avoid\` 里 3 份 supervisor 日志没有 `RESULT: true_end`，属 GUI 中途关窗的截断运行，**不能当验收证据**：
`beginner_stage2_random_obstacles_20261103_200121`、`beginner_stage2_random_obstacles_20261108_175812`、`beginner_stage2_scenario_front_20261108_180507`。
（`20261108_174237` 有真值 `error=0.02946`，可用。`20261108_175812` 的控制器侧结果是干净的 `reached`，只是 Supervisor 被切断。）

**b) ~~根目录 `nul`~~（已于 2026-11-09 经主人确认删除）**：曾有 2708 字节，内容是 2026-11-01 抓 `learn.microsoft.com` 时的 HTTP 响应头（302 → /en-us/），是早期用 `>nul` 想丢弃输出却因 shell 差异真写了一个文件。**纯垃圾，不含项目信息**。已清理。

> 备注：在 MSYS bash 里 `>nul` 会真的创建名为 `nul` 的文件。要丢弃输出请用 `> /dev/null`。

## 0.11 交接规则

- **改动顺序**：先改 WSL 权威 `src/*.py` → 同步到 `webots/controllers/robot_controller/logic/`（字节一致）→ 再跑。`kinematics.py` 当前两侧 SHA256 均为 `dd540fdc…`。
- **改完必跑**：WSL 43 个测试 + `START_RANDOM_AVOID.bat --validate` + 至少一个场景的无头运行；引用数据前核对 `error=`。
- **不要动**：`STAGE*_REPORT.md`、`docs/*.md`、已归档日志、`stage2_obstacle.wbt` 的旧位姿（除主人确认）。
- **新增实验**：一律用 `-RunName` 带场景名+时间，禁止覆盖 `avoid_controller.log` 以外的归档文件。
- **报告口径**：只写实跑到的数；失败样本必须保留；不降低标准来「通过」。
</content>
