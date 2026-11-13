# 项目进度

> 本文件由 `webots/tools/progress.py` 从 `webots/logs/trials.csv` 自动生成。
> 不要手工编辑——下次生成会覆盖。改数据请改日志，然后重新生成。
> 生成时间：2026-11-13 09:19 UTC

## 谁跑到哪了

| 运行者 | 运行数 | 通过 | 最近一次 |
| --- | --- | --- | --- |
| `airpen` | 68 | 30 | 2026-11-13 04:11 UTC |

## 场景级验收

判据：`reached` + `error ≤ 3cm` + `min_clearance > 0`（无障碍场景跳过间隙项）。**8/17 个场景稳定通过。**

| 场景 | 次数 | 通过 | 判定 | 误差范围 (m) | 间隙范围 (mm) |
| --- | --- | --- | --- | --- | --- |
| `clear` | 3 | 3/3 | STABLE_PASS | 0.0170–0.0170 | 无障 |
| `fixed_seed7` | 3 | 3/3 | STABLE_PASS | 0.0170–0.0170 | +62.00~+62.00 |
| `left_blocked` | 3 | 3/3 | STABLE_PASS | 0.0242–0.0242 | +22.75~+22.75 |
| `random_seed_10` | 3 | 3/3 | STABLE_PASS | 0.0170–0.0170 | +38.00~+38.00 |
| `random_seed_5` | 3 | 3/3 | STABLE_PASS | 0.0170–0.0170 | +14.00~+14.00 |
| `random_seed_6` | 3 | 3/3 | STABLE_PASS | 0.0243–0.0243 | +15.23~+15.23 |
| `random_seed_7` | 3 | 3/3 | STABLE_PASS | 0.0170–0.0170 | +42.00~+42.00 |
| `right_blocked` | 3 | 3/3 | STABLE_PASS | 0.0241–0.0241 | +27.60~+27.60 |
| `both_blocked` | 3 | 0/3 | STABLE_FAIL | 0.7468–0.7468 | -0.56~-0.56 |
| `front` | 3 | 0/3 | STABLE_FAIL | 0.0295–0.0295 | -0.17~-0.17 |
| `no_path` | 3 | 0/3 | STABLE_FAIL | 0.8101–0.8101 | -0.30~-0.30 |
| `random_seed_1` | 3 | 0/3 | STABLE_FAIL | 0.0189–0.0189 | -0.17~-0.17 |
| `random_seed_2` | 3 | 0/3 | STABLE_FAIL | 0.0326–0.0326 | -0.17~-0.17 |
| `random_seed_3` | 3 | 0/3 | STABLE_FAIL | 0.0247–0.0247 | -0.73~-0.73 |
| `random_seed_4` | 3 | 0/3 | STABLE_FAIL | 0.4503–0.4503 | -0.26~-0.26 |
| `random_seed_8` | 3 | 0/3 | STABLE_FAIL | 0.0419–0.0419 | -0.19~-0.19 |
| `random_seed_9` | 3 | 0/3 | STABLE_FAIL | 0.4464–0.4464 | +16.89~+16.89 |

## 贴障（接触点通道看不见的那类）

几何间隙 ≤ 0 的运行 **32** 个，其中接触点通道未报出 **32** 个。

| 运行 | 场景 | 间隙 (mm) | 接触点 |
| --- | --- | --- | --- |
| `random_seed_3` | `random_seed_3` | -0.73 | 0 |
| `random_seed_3_r2` | `random_seed_3` | -0.73 | 0 |
| `random_seed_3_r3` | `random_seed_3` | -0.73 | 0 |
| `both_blocked_r2` | `both_blocked` | -0.56 | 0 |
| `both_blocked_r3` | `both_blocked` | -0.56 | 0 |
| `fixed_both_blocked` | `both_blocked` | -0.56 | 0 |
| `test_both2` | `test_both2` | -0.56 | 0 |
| `fixed_no_path` | `no_path` | -0.30 | 0 |
| `no_path_r2` | `no_path` | -0.30 | 0 |
| `no_path_r3` | `no_path` | -0.30 | 0 |
| `test_both_blocked` | `test_both_blocked` | -0.27 | 0 |
| `random_seed_4` | `random_seed_4` | -0.26 | 0 |
| `random_seed_4_r2` | `random_seed_4` | -0.26 | 0 |
| `random_seed_4_r3` | `random_seed_4` | -0.26 | 0 |
| `stallfix_seed4` | `stallfix_seed4` | -0.26 | 0 |

（只列最差的 15 个，共 32 个）

## 下一步

详见 [Notion 团队主页](https://app.notion.com/p/4173f761570d8156bfb5c2279fa1dfd7)。

已知未解决：

- `random_seed_4` 假到达（真值偏 45 cm）：根因是前向传感器照不到斜前方障碍物
- 侧向传感器 ps1/ps2/ps5/ps6 无标定数据
- 场景仅 17 个，统计意义不足
