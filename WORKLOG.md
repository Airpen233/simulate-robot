# 工作日志

> 由 `webots/tools/worklog.py` 从 git 历史自动生成，**无需手工维护**。
> 每次提交后重跑一次即可：`cd webots && python tools/worklog.py`
> 统计窗口：全部历史｜生成时间：2026-11-14 10:05 UTC

## 谁做了什么

| 人 | 提交数 | 涉及文件 | 改动行数 | 活跃天数 |
| --- | --- | --- | --- | --- |
| `airpen` | 16 | 291 | 4455 | 1 |

## 按天

### 2026-11-13　（airpen，16 个提交）

- **feat: 新增 WORKLOG.md —— 从 git 历史自动生成「做了什么」 (#6)** `0614357`　（4 文件 / +640 行）
  - 触及：`(root)`、`.github/workflows`、`webots/tools`

    ## 背景
    PROGRESS.md 只回答「结果如何」（跑了几次、哪些通过）。对方想看
    「他这两天干了什么、为什么这么改」得逐个点开提交，拼不起来。

    用户选择：纯自动，不手写。

    ## 实现
    tools/worklog.py 从 git 历史生成 WORKLOG.md：
    - 按天分组，每天列出提交标题 + 触及模块 + 正文（「为什么」）
    - 作者身份归一：同一人多个邮箱合并（Airpen 有两个邮箱）
    - 自动过滤 Merge pull request 噪音
    - chore/ci/style 折叠成一行，不淹没真正的工作

    ## 两个统计口径的坑（已修）
    1. 首次提交把 136 个日志一次性导入，显示为 17085 行插入
       -> 证据文件（.log/.wbt/_world.json）单独计数，不混进代码行
    2. 首次导入本身不是「一天写了 6500 行」
       -> 基线提交标为「基线导入，不计入工作量」

    修正后：27166 行 -> 3775 行，符合实际。

    ## 验证
    - 连续生成两次内容一致（除时间戳），幂等
    - CI 已加入 worklog.py --print 检查

- **feat: 台账记录运行者与时间，并生成 PROGRESS.md (#5)** `208af4b`　（6 文件 / +354 行 + 证据 138 行）
  - 触及：`webots/tools`、`(root)`、`.github/workflows`

    ## 背景（需求修正）
    之前理解成两人共用一台机器、Webots 会抢实例。实际是**各用自己的
    设备**，仓库是唯一共享点。所以真正需要的是「让他能看到我做到哪」，
    不是并发控制。

    ## 改动
    - trials.csv 新增两列：
      - runner：从日志所在目录推导（logs/random_avoid/<runner>/），
        历史文件没有子目录则归 airpen
      - recorded_at：日志文件 mtime。日志内只有仿真相对时间，mtime 是
        唯一可用的墙钟时间
    - measure_clearance.py 新增 runner_of()
    - 新增 tools/progress.py：从 trials.csv 生成仓库根 PROGRESS.md

    ## PROGRESS.md 内容
    - 谁跑到哪了：每人运行数、通过数、最近一次时间
    - 场景级验收：17 场景的三条件判定与误差/间隙范围
    - 贴障清单：几何间隙 ≤0 但接触点未报出的那些（最差 15 个）
    - 下一步：已知未解决项

    ## CI 设计
    最初想用 GitHub Actions 自动提交 PROGRESS.md，但实测 main 需要 PR，
    bot push 会被拒。改为「本机生成 + 随 PR 提交」，CI 只验证生成器可用。
    额外好处：CI 不能静默改写证据文件。

- **feat: 实验日志按运行者分目录，避免两人互相覆盖 (#4)** `c7c7c7b`　（5 文件 / +169 行 + 证据 268 行）
  - 触及：`webots/logs`、`webots/tools`、`(root)`

    ## 问题
    trials.csv 是从 logs/random_avoid/*.log 派生的。两人把日志混在同一
    目录时会互相覆盖，且 build_trials 用 open("w") 整文件重写。

    ## 方案 A：历史不动，新的分人目录
    首选方案是全部迁入 airpen/ 子目录，但那会让项目历史里每个路径失效
    （已归档证据被 commit 引用过）。折中：

      logs/random_avoid/*.log            历史，原位不动
      logs/random_avoid/<runner>/*.log   新实验，一人一目录

    ## 实现
    - run_avoid.ps1 新增 -Runner，解析顺序：参数 -> RUNNER_NAME 环境变量
      -> "airpen"。名字做白名单校验（字母数字点下划线连字符），因为它
      要当目录名
    - measure_clearance.py 新增 run_dirs() / find_run() / all_runs()
    - build_trials.py 与 summarize_runs.py 改为调用上述函数
    - 三个工具同时扫描历史目录与所有分人子目录，旧数据照常可读

    ## 验证
    - isolation_test 用 -Runner partner 实跑，日志确实进入
      logs/random_avoid/partner/，未污染历史目录
    - 改动前后 measure_clearance 输出完全一致（diff 为空）
    - build_trials 仍 68 行，17 场景判定不变

- **docs: 同步 CI 已启用并成为必需检查 (#3)** `57a16db`　（1 文件 / +58 行）
  - 触及：`docs/TEAM_SETUP.md`

    - CI 四个作业首次运行全过（5-10s）
    - 4 个 check 已设为分支保护必需项，strict 模式
    - 待办从 3 件减为 2 件（workflow 授权已完成）
    - 明确记录管理员绕过当前允许，伙伴到位后应关闭

- **docs: 记录团队协作搭建状态与待办 (#1)** `c956260`　（1 文件 / +126 行）
  - 触及：`docs/TEAM_SETUP.md`

    - 已完成：仓库公开、分支保护（实测拦截直推 main）、src/tests 并入、
      路径可移植、协作模板、Notion Teamspace 三件套
    - 待授权 3 件：CI 需要 workflow scope、伙伴 Notion 邮箱、伙伴 GitHub 用户名
    - 已知协作风险 3 条：trials.csv 并发写、环境必须一致、验收标准易被放宽
    - 给伙伴的诚实交代：真实通过率 47.1%，不是「已实现鲁棒避障」

- **feat: 补齐 CI 之外的团队协作基础设施** `400970b`　（1 文件 / +56 行）
  - 触及：`.github/workflows`

    上一提交因 token 缺 workflow scope 被拒，本提交暂时不含
    .github/workflows/tests.yml（等授权后单独补）。

    含：
    - src/ 与 tests/ 并入主仓库，可独立跑 47 个测试
    - run_avoid.ps1 路径可移植（-WebotsExe / WEBOTS_HOME / PATH）
    - CONTRIBUTING.md 贡献指南
    - CODEOWNERS、PR 模板、三类 Issue 模板

- **feat: 建立团队协作基础设施（CI + PR/Issue 模板 + 贡献指南）** `8568fd7`　（17 文件 / +1742 行）
  - 触及：`.github/ISSUE_TEMPLATE`、`.github/CODEOWNERS`、`.github/pull_request_template.md`

    ## 背景
    项目要从单人转为双人协作。原状态有两个硬障碍：
    1. GitHub 仓库里没有 src/ 和 tests/ —— 47 个测试只存在于 WSL 环境，
       伙伴克隆仓库后根本没有测试可跑。
    2. Webots 可执行文件路径硬编码为 C:\\Program Files\...，换机器就失败。

    ## 改动

    ### 仓库结构
    - 并入 src/（avoidance/kinematics/robot/main）与 tests/（47 个测试）
    - 现在主仓库可独立运行 `python -m unittest discover -s tests`
    - 验证：主仓库本地跑 47 测试全部 OK
    - 权威逻辑仍在 WSL，并入的是字节一致副本（三份核心文件 SHA256 一致）

    ### 路径可移植
    - run_avoid.ps1 新增 -WebotsExe 参数
    - 解析顺序：显式参数 -> WEBOTS_HOME 环境变量 -> 默认安装位置 -> PATH
    - 验证：改动后 VALIDATE_OK 仍通过

    ### CI
    - .github/workflows/tests.yml
    - 在 Python 3.10/3.11/3.12 上跑单元测试
    - 附加作业：生成器自检、间隙工具、台账构建
    - 明确注记：CI 不跑仿真，绝不声称仿真通过

- **docs: 更正 seed 4 根因诊断 —— 堵转检测无法捕获轮子空转** `96e4255`　（0 文件 / +0 行）

    ## 前一提交的错误结论
    上一提交写「堵转检测是必要兜底」，并暗示它能覆盖 seed 4。

    ## 实测推翻
    重跑日志显示，卡住期间控制器估计位置稳定增长：
      pose: 0.573 -> 0.614 -> 0.655 -> ... -> 0.982（每次约 +0.041m）
    而真值 x 从 t=7.2 起冻结在 0.5497。

    即：轮子在转、编码器在计数、里程计完全不知情。
    「里程计位移 <1mm」这个判据永远抓不到这种空转。

    ## 堵转检测仍然有效，但适用范围要说清楚
    它只能抓「指令发出但轮子不转」（编码器增量≈0），
    例如轮子被外力完全锁死、电机堵转。

    它抓不到「轮子空转」，那是另一类故障：
    物理上在推障碍物，轮子转但车不动，编码器照常计数。

    ## 正确分类
    | 现象 | 编码器 | 里程计 | 能否被 stall guard 抓到 |
    |---|---|---|---|
    | 电机锁死 | 不动 | 不动 | 能 |
    | 轮子空转 | 照常转 | 虚增 | 不能 |
    | 正常行驶 | 转 | 增长 | 不触发 |

- **feat: 加入堵转检测（stall guard），并查明 seed 4 根因不是堵转** `18791dc`　（2 文件 / +80 行 + 证据 145 行）
  - 触及：`webots/logs`、`webots/controllers`

    ## 改动
    - AvoidConfig 新增 stall_window_s=0.5, stall_min_progress_m=0.001
    - AvoidStateMachine._update_stall(): 指令前进但里程计 0.5s 内位移
      小于 1mm 时判定 STUCK
    - tick() 新增 travelled_m / commanded_forward 参数（有默认值，
      旧调用不受影响）
    - 堵转判据在 REACHED 之前执行，避免假到达优先
    - avoid_controller.py 传入 odometry.distance_m 与指令方向
    - 新增 4 个测试：堵转触发、正常前进不触发、原地转不触发、
      堵转优先于假到达

    测试：43 -> 47，全部通过

    ## 关键发现：seed 4 不是堵转问题
    用新代码重跑 seed 4，结果完全没变（仍 45.03cm 假到达，
    控制器仍报 reached）。

    查真值轨迹：机器人在 t=7.2 卡在 x=0.5497，之后 17 秒一动不动，
    而里程计照样累计到 0.982。这确实是堵转。

    但堵转检测没触发，因为：
    - 障碍物 OBSTACLE1 在 (0.663, 0.108)，位于机器人右前方
    - 机器人与它表面距离仅 2.8cm
    - 但 front(ps0/ps7) 读数只有 70-80，远低于阈值 120

- **fix: 无障碍场景的间隙判据应为 N/A 而非失败** `5f54714`　（1 文件 / +18 行 + 证据 134 行）
  - 触及：`webots/logs`、`webots/tools`

    clear 场景没有障碍物，min_clearance 无定义（空值）。原逻辑把空值
    当作 clearance_ok != yes，导致该场景永远无法通过。

    修正：无障场景跳过间隙判据，只按误差判。clear 从 STABLE_FAIL
    变为 STABLE_PASS。

    ## 最终统计（N=3，三条件）
    场景 17，通过 8，失败 9，不稳定 0
    通过率 8/17 = 47.1%

    ## 失败原因分类
    误差超限 5 个：both_blocked 74.7cm / no_path 81.0cm /
      seed4 45.0cm / seed9 44.6cm / seed8 4.2cm / seed2 3.3cm
    贴障     3 个：front -0.17mm / seed1 -0.17mm / seed3 -0.73mm
      （这三个误差都 <=3cm，只因几何间隙<=0 而失败）

    ## 口径对比
    旧（只看误差）: 11/17 = 64.7%
    新（+间隙）  : 8/17  = 47.1%

- **test: 补跑 34 次重复实验，推翻 N=3 假设** `ffd0a02`　（3 文件 / +433 行 + 证据 5621 行）
  - 触及：`webots/logs`、`webots/tools`、`(root)`

    ## 执行
    17 场景 × r2/r3 共 34 次运行。首次因并发启动两个 Webots
    实例导致 11 次作废（WEBOTS_EXIT_CODE=-1，1.6s 退出，零日志），
    串行重跑后全部完成。

    ## 结果：零方差
    17/17 场景三次重复的真值误差完全相同（精确到 0.00001 m），
    间隙也完全相同。random_seed_3 的三份日志去 header 后逐字节相同。
    不稳定场景数：0。

    ## 结论：N=3 在当前项目是无效的
    本项目不训练策略，仿真步进完全确定（固定 32ms、无随机注入、
    无噪声建模）。同场景重复等价于跑一次。
    要统计意义必须扩大场景数（17→50+），不是重复。

    ## 判据统计
    新三条件（reached + 误差<=3cm + 间隙>0）：
      稳定通过 7/17 = 41.2%
    旧口径（只看误差）：11/17 = 64.7%
    差额 4 个全因几何间隙<=0 被判失败，是加严不是退化。

    ## 假设验证
    H1 可复现   ✅（强于预期：逐字节相同）
    H2 seed4    ✅ 3/3 全部 45.03cm

- **feat: 建立实验工作流 + 最小间隙测量工具，推翻「碰撞 0」结论** `7900838`　（2 文件 / +663 行）
  - 触及：`(root)`、`webots/tools`

    ## 新增
    - EXPERIMENT_WORKFLOW.md：实验纪律（双层随机协议、不可变台账、
      复现分级 T1/T2/T3、双通道验收、预登记、统计报告格式）
    - webots/tools/measure_clearance.py：基于 Supervisor 真值位姿算
      机器人与障碍物的最小几何间隙

    ## 关键发现：collision_samples 是系统性假阴性
    30 个有效 run 中，几何重叠 15 个，而接触点通道 15/15 全部漏报。

    15 个擦碰的表面距离集中在 36.27-36.83 mm（半径 37 mm），
    说明是接触约束把穿透压在容差附近，不是数值噪声。
    符号有意义，量级无意义：clearance <= 0 一律判失败。

    ## 因此撤回的旧结论
    旧说法「障碍碰撞 0」不成立。正确表述：
    接触点通道记录 0 次；几何通道测出 15 次持续接触。

    ## 工具验证
    fixed_front 复现手工计算的 -0.17 mm，时间点与坐标一致。

    依据：CoRL-Skills / RSS-Skills 学术评审方法论，本地化后写入工作流文档。

- **docs: AGENTS.md 降级为本地草稿，权威副本迁入 Notion** `4820242`　（1 文件 / +20 行）
  - 触及：`(root)`

    - 文件头标明权威副本位置（Notion PS_Knowledge）
    - 目录地图、Git 状态两处过时描述一并修正
    - 新增 .gitignore（logs 故意入库，作为验收证据）
    - 内容未删减，仅改头部与两行事实

    关联：项目卡 4173f761-570d-81f5-b170-cbf87cceca1a
    知识页 4173f761-570d-81c5-80a8-ebd8b592b914

- 另有 2 个杂项提交（chore/ci/style）：`e665f83`、`ed01193`
- _chore: 首次提交 —— Webots e-puck 仿真工程现状快照_ `0864dcc`　— 基线导入，不计入工作量

## 最近活跃的模块

| 模块 | 涉及提交数 |
| --- | --- |
| `(root)` | 9 |
| `webots/tools` | 7 |
| `webots/logs` | 6 |
| `.github/workflows` | 5 |
| `docs/TEAM_SETUP.md` | 2 |
| `webots/controllers` | 2 |
| `.github/ISSUE_TEMPLATE` | 1 |
| `.github/CODEOWNERS` | 1 |
| `.github/pull_request_template.md` | 1 |
| `webots/worlds` | 1 |
