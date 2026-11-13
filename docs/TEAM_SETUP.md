# 团队协作搭建状态

> 更新：2026-11-13 ｜ 状态：**地基已完成，等待第二个人到位**

---

## 已完成

### GitHub

| 项 | 状态 | 说明 |
|---|---|---|
| 仓库公开 | ✅ | `github.com/Airpen233/simulate-robot` 已从私有改为公开 |
| 分支保护 | ✅ | 强制 PR、需 1 人批准、禁 force-push、禁删 main、**管理员也受约束** |
| 仓库结构合并 | ✅ | `src/` + `tests/` 已并入，主仓库可独立跑 47 个测试 |
| 路径可移植 | ✅ | `run_avoid.ps1` 支持 `-WebotsExe` / `WEBOTS_HOME` / PATH 自动探测 |
| 协作模板 | ✅ | `CONTRIBUTING.md`、`CODEOWNERS`、PR 模板、3 类 Issue 模板 |
| **CI 流水线** | ❌ **阻塞** | 见下方「待你授权」 |

**分支保护已实测有效**：直接 push main 被拒

```
! [remote rejected] main -> main (protected branch hook declined)
```

### Notion

| 项 | 状态 | 链接 |
|---|---|---|
| Teamspace「Airpen的工作空间 总部」 | ✅ 已存在（你是 owner） | — |
| 团队主页 | ✅ | [Simulate Robot · 团队主页](https://app.notion.com/p/4173f761570d8156bfb5c2279fa1dfd7) |
| 任务看板 | ✅ 含「伙伴」负责人选项 | 团队主页下 |
| 决策记录库 | ✅ | 团队主页下 |
| ADR-001 碰撞双通道 | ✅ 已回填 | 决策记录库 |

---

## 待你授权（3 件，都要你本人操作）

### ① CI 需要 `workflow` 权限

**现象**

```
! [remote rejected] (refusing to allow an OAuth App to create or update
   workflow `.github/workflows/tests.yml` without `workflow` scope)
```

**当前 token 权限**：`gist`、`read:org`、`repo` —— 缺 `workflow`

**操作步骤**

```bash
# 在终端里跑（会打开浏览器）
gh auth refresh -s workflow
```

浏览器弹出后勾选确认即可。完成后告诉我，我把 CI 推送上去。

> CI 文件已备好，暂存在 `/tmp/tests.yml.pending`。内容：在 Python 3.10/3.11/3.12 上跑 47 个测试 + 工具自检。

### ② 伙伴的 Notion 邮箱

需要用来邀请进 Teamspace。**没有它，团队主页只有你一个人能看到。**

### ③ 伙伴的 GitHub 用户名

需要用来：

- 加为仓库协作者
- 替换 `CODEOWNERS` 里的占位符
- 让他能提 PR

---

## 第二个人到位后要做的

```
□ Notion：邀请伙伴进 Teamspace，设定可编辑权限
□ GitHub：Settings → Collaborators → 添加伙伴（Write 权限）
□ CODEOWNERS：把 @伙伴 占位符换成真实用户名
□ 给伙伴发一份「三十秒上手」：clone → 跑测试 → 47 个全过
□ 约定第一次协作任务（建议从 Issue 开始，别直接从代码开始）
```

---

## 已知的协作风险（写下来免得踩）

### 1. `trials.csv` 会被并发写坏

现在脚本假设「只有一个人在跑实验」。两个人同时跑会：

- 同时写 `trials.csv` 冲突
- **抢占 Webots 实例**（已实测：并发启动第二个会 1.6 秒退出、零日志）
- 用同样场景名覆盖

**解法（待实施）**：`trials.csv` 按人分文件，或加「谁在跑」锁。

### 2. 环境必须一致

Webots 版本不同 → 物理行为不同 → 同一个场景跑出不同的 `error=`。

**这不是谁算错了，是环境不一致。** 发现后要排查，不能当作「手抖」。

### 3. 验收标准容易被无意放宽

`EXPERIMENT_WORKFLOW.md` 是我写的，你认可了。但伙伴没参与。

**PR 模板里已加一节强制填「验证了什么」**，就是为了防这个。

---

## 当前项目真实数字（给伙伴的诚实交代）

| 项 | 值 |
|---|---|
| 单元测试 | 47 个，全过 |
| 实验场景 | 17 个 |
| 真实通过率 | **8/17 = 47.1%** |
| 判据 | `reached` + `error ≤ 3cm` + `min_clearance > 0` |
| 证据等级 | T3（可审计） |

**不是「已实现鲁棒自主避障」。** 17 个场景里有 2 个本质无解（受困场景），1 个是已知的传感器盲区 bug（seed 4）。

新加入的人应该先看 `AGENTS.md` 的「0.6 结果现状」和「0.7 校准过的坑」两节，那里没有美化。
