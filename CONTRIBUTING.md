# 贡献指南

> 这是一个双人协作项目。本文件定义「怎么一起干活」。
> 项目事实见 [`AGENTS.md`](AGENTS.md)，实验纪律见 [`EXPERIMENT_WORKFLOW.md`](EXPERIMENT_WORKFLOW.md)。

---

## 0. 三十秒上手

```bash
git clone https://github.com/Airpen233/simulate-robot.git
cd simulate-robot

# 跑单元测试（纯 Python，不需要 Webots）
python -m unittest discover -s tests -v
```

**47 个测试全过** = 你的环境是对的。

跑仿真需要 Webots R2025a：

```powershell
# Windows 上，从仓库根目录
cd webots
cmd /c "START_RANDOM_AVOID.bat --validate"     # 静态检查，不启动仿真
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid.ps1 `
  -WorldFile stage2_scenario_front.wbt -RunName my_test -Timeout 24 -WaitSeconds 34
```

Webots 路径会自动探测（`WEBOTS_HOME` 环境变量 → 默认安装位置 → PATH）。探测失败时用 `-WebotsExe` 显式指定。

---

## 1. 代码分工

| 位置 | 负责人 | 说明 |
|---|---|---|
| `src/avoidance.py` | **Airpen** | 避障状态机，核心逻辑 |
| `src/kinematics.py` | **Airpen** | 差速运动学 |
| `src/robot.py` | **Airpen** | 机器人抽象 |
| `webots/controllers/` | **Airpen** | Webots 适配层 |
| `webots/tools/` | 共同 | 分析工具，改前先说一声 |
| `docs/` | 共同 | 教材与说明 |
| `EXPERIMENT_WORKFLOW.md` | **Airpen** | 实验纪律，改动需讨论 |

> 分工写在 [`CODEOWNERS`](.github/CODEOWNERS) 里，PR 会自动请求对应评审。

---

## 2. 协作流程

```
1. 开 Issue 说清要做什么（用模板）
2. 从 main 拉分支：git checkout -b feat/你的功能名
3. 改代码 + 加测试
4. 本地跑：python -m unittest discover -s tests
5. 提 PR（用模板，必须填「验证了什么」）
6. 另一人 review
7. 合并到 main
```

### 分支命名

```
feat/xxx    新功能
fix/xxx     修 bug
exp/xxx     实验（不改核心逻辑）
docs/xxx    文档
```

### 三条硬规矩

1. **不许直接 push 到 main。** 一律走 PR。
2. **不许 force-push 到 main 或别人的分支。**
3. **PR 合并前 CI 必须绿。**

---

## 3. 提交信息格式

```
<类型>: <一句话说明>

<可选：为什么这么改，有什么取舍>

<可选：关联 Issue #123>
```

类型：`feat` / `fix` / `docs` / `test` / `refactor` / `exp` / `chore`

**示例**（来自本仓库真实历史）：

```
fix: 无障碍场景的间隙判据应为 N/A 而非失败

clear 场景没有障碍物，min_clearance 无定义（空值）。原逻辑把空值
当作 clearance_ok != yes，导致该场景永远无法通过。

修正：无障场景跳过间隙判据，只按误差判。
```

---

## 4. 实验规矩（这条最重要）

**任何「实验成功」的结论，必须附证据。** 详见 `EXPERIMENT_WORKFLOW.md`。

最低要求：

| 结论类型 | 必须提供 |
|---|---|
| 「修好了」 | 跑之前的日志 + 跑之后的日志 |
| 「通过率提升了」 | 完整 `trials.csv` 行，不许挑样本 |
| 「碰撞 0 次」 | 说清是哪个通道测的（接触点 / 几何间隙） |

**只认 Supervisor 真值：`RESULT: true_end ... error=`。控制器自报 `reached` 不算证据。**

### 两个已知陷阱

1. **`collision_samples=0` 是假阴性。** 接触点通道漏报率实测 32/32。必须同时看几何间隙。
2. **仿真完全确定性。** 同场景跑两次产生逐字节相同的日志。所以「多跑几次」不会带来新信息，要扩大**场景数量**。

---

## 4.1 日志目录：按人隔离

从 2026-11-13 起，实验日志按运行者分目录：

```
webots/logs/random_avoid/
├── *.log              ← 历史（2026-11 之前），保持在原位不动
├── airpen/            ← Airpen 的新实验
│   └── <RunName>_*.log
└── <你的名字>/         ← 你的新实验
    └── <RunName>_*.log
```

**为什么要这样**：`trials.csv` 是从日志派生出来的。两人把日志混在同一目录，会互相覆盖。

### 怎么用

```powershell
# 方式一：显式指定
.\tools\run_avoid.ps1 -WorldFile ... -RunName my_test -Runner 你的名字

# 方式二：设环境变量（推荐，设一次就行）
$env:RUNNER_NAME = "你的名字"
```

**不设的话默认是 `airpen`**，你的实验会混进我的目录里。第一次用请务必设一次。

### 历史文件为什么不动

`logs/random_avoid/*.log` 是已归档的证据，被 commit 引用过。移动它们会让项目历史里每一个路径都失效。

三个分析工具（`measure_clearance.py` / `build_trials.py` / `summarize_runs.py`）会**同时扫描历史目录和所有分人子目录**，所以旧数据照样能读。

### 跑之前先看有没有人在跑

**Webots 同一时间只能跑一个实例。** 两个人同时启动，后来者会在 1.6 秒内退出且**不产生任何日志**——看起来像「跑完了但没结果」。

脚本已经会检测并抛错：

```
Webots is already running (...). Close the existing Webots window before starting this experiment.
```

看到这个提示，等对方跑完再试。

---

## 5. 提交日志前先想清楚

本仓库**把实验日志纳入版本控制**（`webots/logs/`）。这是刻意的：日志就是证据，不放进版本控制就无法追溯。

所以：

- 新增实验日志请一并提交，**不要只提交成功的**
- 失败的样本比成功的更有价值
- 日志文件命名带场景名 + 时间，不要复用文件名

---

## 6. 环境差异须知

| 项 | Airpen 的环境 | 你的环境可能不同 |
|---|---|---|
| Webots | R2025a | 版本必须一致，否则物理行为会变 |
| Python | 3.12.10 | CI 测 3.10/3.11/3.12 |
| WSL | Ubuntu-24.04 | 可选，只影响跑测试的位置 |

**如果你们跑同一个场景得到不同的 `error=` 值，说明环境不一致——这是要排查的问题，不是谁算错了。**

---

## 7. 遇到分歧怎么办

1. **数据说话。** 跑实验，看结果，不靠感觉。
2. **写进 ADR。** 重要决策记录在 `docs/decisions/` 下，写清背景、选项、选择理由。
3. **改不了就记录。** 已知限制写进文档，比假装不存在强。
