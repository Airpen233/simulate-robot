# 归档运行索引（自动生成，勿手改）

> 生成时间：2026-11-09 23:26　生成方式：解析 `logs/random_avoid/*_controller.log` + `*_supervisor.log`。
> 本文件**只新增索引**，不修改、不移动、不删除任何原日志。
> 验收口径：**只认 Supervisor 的 `RESULT: true_end ... error=`**；控制器自报 `reached` 不算证据。

目录内共 **33** 组运行。每组含 `_controller.log` + `_supervisor.log`（部分含 `_world.json`）。

## 一、全部运行

| 运行名 | 场景/seed | 参数代 | 控制器结果 | 真值误差 | ≤3cm | 碰撞 | 尝试/转向/后退/恢复 | 证据可用性 |
|---|---|---|---|---|---|---|---|---|
| `beginner_stage2_random_obstacles_20261103_200121` | fixed_seed7 | A | `error` | — | — | — | — | ⚠️ 截断，无真值 → **不可作验收** |
| `beginner_stage2_random_obstacles_20261103_200349` | fixed_seed7 | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `beginner_stage2_random_obstacles_20261108_175812` | fixed_seed7 | A | `reached` | — | — | — | 0/0/0/0 | ⚠️ 截断，无真值 → **不可作验收** |
| `beginner_stage2_scenario_front_20261108_174237` | front | A | `reached` | 2.95 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用 |
| `beginner_stage2_scenario_front_20261108_180507` | front | A | `reached` | — | — | — | 1/1/0/1 | ⚠️ 截断，无真值 → **不可作验收** |
| `fixed_both_blocked` | both_blocked | A | `timeout` | 74.67 cm | ❌ | 0 | 5/4/1/3 | 📕 失败样本（必须保留） |
| `fixed_clear` | clear | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `fixed_fixed_seed7` | fixed_seed7 | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `fixed_front` | front | A | `reached` | 2.95 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用 |
| `fixed_left_blocked` | left_blocked | A | `reached` | 2.42 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用 |
| `fixed_no_path` | no_path | A | `timeout` | 81.01 cm | ❌ | 0 | 5/4/1/3 | 📕 失败样本（必须保留） |
| `fixed_right_blocked` | right_blocked | A | `reached` | 2.41 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用 |
| `random_seed_10` | 10 | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `random_seed_1` | 1 | A | `reached` | 1.89 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `random_seed_2` | 2 | A | `reached` | 3.26 cm | ❌ | 0 | 1/1/0/1 | 📕 超差 / 假 reached（必须保留） |
| `random_seed_3` | 3 | A | `reached` | 2.47 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `random_seed_4` | 4 | A | `reached` | 45.03 cm | ❌ | 0 | 0/0/0/0 | 📕 超差 / 假 reached（必须保留） |
| `random_seed_5` | 5 | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `random_seed_6` | 6 | A | `reached` | 2.43 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用 |
| `random_seed_7` | 7 | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用 |
| `random_seed_8` | 8 | A | `reached` | 4.19 cm | ❌ | 0 | 1/1/0/1 | 📕 超差 / 假 reached（必须保留） |
| `random_seed_9` | 9 | A | `timeout` | 44.64 cm | ❌ | 0 | 4/4/0/3 | 📕 失败样本（必须保留） |
| `stage2_random_obstacles` | fixed | A | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用｜复核/旧名 |
| `takeover_check` | fixed | A | `reached` | 2.95 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用｜复核/旧名 |
| `test_both2` | test_both2 | A | `timeout` | 74.67 cm | ❌ | 0 | 5/4/1/3 | 📕 失败样本（必须保留）｜开发期 |
| `test_both_blocked` | test_both_blocked | B | `timeout` | 75.37 cm | ❌ | 0 | 5/5/0/2 | 📕 失败样本（必须保留）｜开发期 |
| `test_clear2` | test_clear2 | C | `reached` | 1.70 cm | ✅ | 782 | 0/0/0/0 | ✅ 可引用｜开发期 |
| `test_clear3` | test_clear3 | C | `reached` | 1.70 cm | ✅ | 0 | 0/0/0/0 | ✅ 可引用｜开发期 |
| `test_front2` | test_front2 | B | `reached` | 2.95 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用｜开发期 |
| `test_front` | test_front | C | `timeout` | 69.08 cm | ❌ | 0 | 8/8/0/8 | 📕 失败样本（必须保留）｜开发期 |
| `test_left_blocked` | test_left_blocked | B | `reached` | 2.42 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用｜开发期 |
| `test_no_path` | test_no_path | B | `timeout` | 78.00 cm | ❌ | 0 | 5/5/0/2 | 📕 失败样本（必须保留）｜开发期 |
| `test_right_blocked` | test_right_blocked | B | `reached` | 2.41 cm | ✅ | 0 | 1/1/0/1 | ✅ 可引用｜开发期 |

## 二、参数代（同一目录里混了三代参数，引用时必须分开看）

- **A 代**（turn 0.90 / move 2.50 / backup 0.80）：25 组
  `beginner_stage2_random_obstacles_20261103_200121`、`beginner_stage2_random_obstacles_20261103_200349`、`beginner_stage2_random_obstacles_20261108_175812`、`beginner_stage2_scenario_front_20261108_174237`、`beginner_stage2_scenario_front_20261108_180507`、`fixed_both_blocked`、`fixed_clear`、`fixed_fixed_seed7`、`fixed_front`、`fixed_left_blocked`、`fixed_no_path`、`fixed_right_blocked`、`random_seed_10`、`random_seed_1`、`random_seed_2`、`random_seed_3`、`random_seed_4`、`random_seed_5`、`random_seed_6`、`random_seed_7`、`random_seed_8`、`random_seed_9`、`stage2_random_obstacles`、`takeover_check`、`test_both2`
- **B 代**（turn 0.90 / move 2.50 / backup 0.40）：5 组
  `test_both_blocked`、`test_front2`、`test_left_blocked`、`test_no_path`、`test_right_blocked`
- **C 代**（turn 0.80 / move 0.50 / backup 0.40）：3 组
  `test_clear2`、`test_clear3`、`test_front`

**结论**：验收数据（`fixed_*`、`random_seed_*`、`beginner_*2026110*`）全部属于 **A 代**，与当前 `AvoidConfig` 默认值一致。
`test_*` 系列属 B/C 代早期调参，**不能与 A 代数字直接对比**——例如 `test_front` 的 `timeout`（8 次尝试/8 次转向）
是在 C 代 `move_duration_s=0.5`（绕行距离只有 A 代的 1/5）下发生的，不是「当前参数下也失败」。

## 三、异常记录（3 组，需人工知情）

以下运行没有 `RESULT: true_end`，属 GUI 中途关窗的截断记录：

- `beginner_stage2_random_obstacles_20261103_200121`：控制器 `error`，Supervisor 日志在 POSE 中途结束
- `beginner_stage2_random_obstacles_20261108_175812`：控制器 `reached`，Supervisor 日志在 POSE 中途结束
- `beginner_stage2_scenario_front_20261108_180507`：控制器 `reached`，Supervisor 日志在 POSE 中途结束

## 四、确定性复现证据（可作链路可信度依据）

同一 seed + 同一路径多次运行，真值误差**逐位相同**：

- `0.01696`（1.70 cm）：`fixed_clear`、`fixed_fixed_seed7`、`random_seed_5/7/10`、`test_clear2`、`test_clear3`、`beginner_*_200349`、`stage2_random_obstacles`
- `0.02946`（2.95 cm）：`fixed_front`、`test_front2`、`takeover_check`、`beginner_*_174237`

说明仿真在固定 seed 下可复现，不是人工复制的数字。

补充：`test_clear2` / `test_clear3` 虽属 C 代参数，但因该布局 0 次避障（`attempts=0`），
参数不参与动作选择，所以真值与 A 代逐位相同——这是**预期**结果，不是参数代分错。

## 五、与 `summary.csv` 的关系

`summary.csv`（`tools/summarize_runs.py` 生成）只覆盖报告采信的 **17 次**（7 固定 + 10 随机）；
本索引覆盖目录里**全部**运行，含开发期调试与复核运行。
两者不冲突：`summary.csv` = 验收数据；本索引 = **存放清单**。
