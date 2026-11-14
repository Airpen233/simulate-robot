# 新人上手：从零开始参加这个项目

> **这份文件是给谁看的**：会用电脑、但没怎么用过 AI 助手、也没接触过 GitHub 的人。
> 不需要任何编程基础。每一步都写清楚「点哪里、打什么、看到什么算成功」。
>
> 如果你已经会用 GitHub 和命令行，直接看 [CONTRIBUTING.md](CONTRIBUTING.md)。
>
> **想知道这个项目最终要做成什么样、现在走到哪了**：看 [ROADMAP.md](../ROADMAP.md)。
> 建议先照着这份文件跑通一次，再读路线——那时候你会更容易理解路线里在说什么。

---

## 0. 这个项目在做什么（30 秒版）

我们在 Webots 仿真软件里，让一个叫 **e-puck** 的小轮式机器人学会自己绕过障碍物、走到目标点。

- 机器人没有摄像头，只有 8 个红外传感器 + 2 个轮子
- 全部在电脑里模拟，不会碰坏任何东西
- 目标是让它「可靠地」完成任务——不是碰巧成功一次

**为什么需要两个人**：一个人写代码调参数，另一个人跑实验记数据、找反例。这两件事必须分开做，否则容易自己骗自己。

---

## 1. 你会用到三个东西

| 工具 | 干什么用 | 类比 |
|---|---|---|
| **GitHub** | 存代码和历史，两个人同步 | 一个共享网盘，但能记住每次改动 |
| **AI 助手**（DSH / ChatGPT / Claude 都行） | 帮你写代码、解释报错、分析数据 | 一个随时在的助教 |
| **Webots** | 跑仿真，看机器人动 | 一个游戏，但物理是真的 |

**你不需要精通任何一个。** 下面每一步都会告诉你怎么做。

---

## 2. 第一步：把项目下载到自己电脑

### 2.1 装 Git

打开 <https://git-scm.com/download/win>，下载 Windows 版，一路点「下一步」装完。

装完验证：按 `Win + R`，输入 `cmd`，回车。在黑窗口里打：

```
git --version
```

看到类似 `git version 2.5x.x` 就是成功了。

### 2.2 装 Python

打开 <https://www.python.org/downloads/>，下载 3.12 版本。

**安装时一定要勾选 `Add Python to PATH`**（在第一个界面最下面）。这一步漏了后面会很麻烦。

验证：同样在 cmd 里打：

```
python --version
```

应该显示 `Python 3.12.x`。

### 2.3 下载项目

在 cmd 里打（一行，回车）：

```
cd %USERPROFILE%\Desktop
git clone https://github.com/Airpen233/simulate-robot.git
```

这会桌面上出现一个叫 `simulate-robot` 的文件夹。

### 2.4 验证下载成功

```
cd %USERPROFILE%\Desktop\simulate-robot
python -m unittest discover -s tests
```

**看到最后一行是 `OK` 就成功了。**

如果显示 `Ran 47 tests ... OK`，说明你的环境和我们的完全一致。

> ⚠️ 如果这里报错，先别往下走。把整个报错复制给 AI，说「我在 Windows 上跑 python -m unittest 报这个错，怎么解决」。

---

## 3. 第二步：装 Webots（跑仿真用）

打开 <https://cyberbotics.com/>，下载 **R2025a** 版本。

**版本必须是 R2025a。** 不同版本的物理引擎不一样，同一个场景会跑出不同结果，到时候你和我的数据对不上。

装完后，项目会自动找到它，不需要配置。

---

## 4. 第三步：跑第一次仿真

### 4.1 先做静态检查（安全，不启动仿真）

在 cmd 里：

```
cd %USERPROFILE%\Desktop\simulate-robot\webots
START_RANDOM_AVOID.bat --validate
```

看到 `VALIDATE_OK` 就对了。

### 4.2 真跑一次

```
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid.ps1 -WorldFile stage2_scenario_clear.wbt -RunName 我的第一次 -Runner 你的名字 -Timeout 24 -WaitSeconds 34
```

**注意 `-Runner 你的名字`** —— 把「你的名字」换成你的英文名或拼音（只能用字母、数字、`.`、`_`、`-`）。

这一步的作用是：你的实验日志会存到 `logs/random_avoid/你的名字/` 下，不会和我的混在一起。

大约 34 秒后，你会看到：

```
STILL_RUNNING=False
SUPERVISOR_RESULT=RESULT: true_end pos=[0.98304,-0.00000] ... error=0.01696 ...
```

**`error=0.01696` 就是机器人离目标点的真实距离（米）。0.01696 = 1.696 厘米。**

这个数字和我的完全一样，说明你跑对了。

---

## 5. 怎么和 AI 配合干活

这是最重要的一节。用得好，效率差好几倍；用不好，AI 会给你一堆跑不了的代码。

### 5.1 提问的四个要素

一个能用的提问长这样：

```
【环境】Windows 11，Webots R2025a，Python 3.12
【我做了什么】运行 tools\run_avoid.ps1 跑 stage2_scenario_front.wbt
【报了什么错】贴完整报错，不要只说「报错了」
【我想要什么】让它跑完并输出 SUPERVISOR_RESULT
```

**反例（AI 只能瞎猜）**：

```
我的代码不工作，怎么办
```

### 5.2 报错要贴全

不要只贴最后一行。要把从 `Traceback` 或者 `Error` 开始的部分整段贴出来，包括文件名和行号。

如果 AI 看了说「信息不够」，就把它要的东西补上再问。

### 5.3 不要让 AI 一次改太多

❌ 坏做法：「帮我优化避障算法」
✅ 好做法：「在 `avoidance.py` 的 `choose_turn_direction` 里，把阈值从 200 改成从配置读取，其他不要动」

**一次只改一件事**，改完自己跑一遍验证。改多了出错就不知道是哪一处的问题。

### 5.4 让 AI 给你「验证方法」

每次让 AI 改东西，最后加一句：

```
改完之后，我怎么验证它确实生效了？给我一条命令和预期输出。
```

如果 AI 说不清楚怎么验证，那这次改动大概率有问题。

### 5.5 AI 说「已完成」时，不要信

**AI 经常声称做了它没做的事。** 特别是：

- 「我已经运行了测试」→ 你自己跑一遍
- 「应该可以了」→ 跑一次看结果
- 「这个 bug 已修复」→ 跑之前失败的那个场景

这个项目有一条铁律：

> **没有实际运行过的，不能说成已经运行过。**

### 5.6 让 AI 读项目里的文件

AI 不知道我们项目的细节，直接问它会得到通用答案。最好开头就说：

```
先读一下 simulate-robot 项目里的 CONTRIBUTING.md 和 AGENTS.md，
然后再回答。
```

---

## 6. 怎么把改动交回项目（GitHub）

你改了代码或者跑完实验，需要让另一个人的电脑也能看到。流程是：**拉取 → 改 → 提交 → 推送**。

### 6.1 每次开工前先拉取

```
cd %USERPROFILE%\Desktop\simulate-robot
git pull
```

这一步是拿别人最新的改动。**不做的话，后面推送会冲突。**

### 6.2 改完之后，看自己改了什么

```
git status
```

会列出你改动的文件（红色的）。确认这些都是你想改的。

### 6.3 提交

```
git add -A
git commit -m "fix: 修了 front 场景的转向时机"
```

`-m` 后面是说明。**格式：`类型: 一句话`**

| 类型 | 什么时候用 |
|---|---|
| `feat` | 新增功能 |
| `fix` | 修 bug |
| `docs` | 只改文档 |
| `exp` | 跑实验、改数据 |
| `test` | 加测试 |

### 6.4 推送

```
git push
```

**如果报错说 `rejected`，通常是因为别人先推了。** 先 `git pull` 再 `git push`。

### 6.5 关于「不能直接推 main」

项目设了保护：**不能直接往主分支推**，必须走「提 PR（Pull Request）」。

简单说：

1. 开一个自己的分支：`git checkout -b feat/我的功能`
2. 改完提交推送：`git push -u origin feat/我的功能`
3. 去 GitHub 网页上点「Compare & pull request」
4. 等对方点「Approve」，然后点「Merge」

**为什么这么麻烦**：这样每一步改动都有人看过，不会有人手滑把整个项目搞坏。

---

## 7. 跑实验的规矩（很重要）

这个项目最容易犯的错，是**用不靠谱的数据下结论**。

### 7.1 只认 Supervisor 的数字

每次运行会输出两行结果：

```
CONTROLLER_RESULT=RESULT: reached ...      ← 机器人自己以为到了
SUPERVISOR_RESULT=RESULT: true_end ... error=0.01696    ← 上帝视角的真实距离
```

**只有第二行算数。** 第一行是机器人自己的估计，它会骗人——历史上出现过机器人以为到了、实际差 45 厘米的情况。

### 7.2 三个数字必须一起看

| 指标 | 从哪看 | 合格线 |
|---|---|---|
| 真实误差 | `SUPERVISOR_RESULT` 的 `error=` | ≤ 0.03（3 厘米） |
| 最小间隙 | 跑 `python tools/measure_clearance.py` | > 0（没碰到障碍） |
| 是否假到达 | 对比上面两行 | 不允许 |

**只看误差会漏掉「撞着过去」的情况。** 实测中有一半的运行撞到了障碍物，但碰撞计数器完全没报出来。

### 7.3 跑完记得更新这两份文件

```
cd webots
python tools/build_trials.py
python tools/progress.py
python tools/worklog.py
```

然后一起提交。这样对方打开 GitHub 就能看到你做了什么、结果如何。

---

## 8. 遇到问题怎么办

按这个顺序：

1. **看报错最后一行**，通常是直接原因
2. **问 AI**，按第 5.1 节的四要素提问
3. **搜索**——把报错原文粘到搜索引擎，很多坑别人踩过
4. **问队友**——但先说清楚你试过什么

### 常见问题速查

| 症状 | 原因 | 怎么办 |
|---|---|---|
| `python: command not found` | 装 Python 时没勾 PATH | 重装，勾上 `Add Python to PATH` |
| `git clone` 卡住 | 网络问题 | 换个网络，或用手机热点试 |
| 仿真跑起来但没有任何日志 | 并发冲突（两个 Webots） | 关掉所有 Webots 再跑 |
| `VALIDATE world_controller_...=MISSING` | 世界文件和控制器不匹配 | 检查 `-WorldFile` 名字拼对了没 |
| `git push` 报 `rejected` | 别人先推了 | 先 `git pull`，解决冲突后再推 |
| 结果和队友不一样 | Webots 版本不同 | 核对版本是否都是 R2025a |

---

## 9. 你的第一个任务

不用等分配，直接做这个：

**跑三次 `stage2_scenario_front.wbt`，然后回答：这三次结果一样吗？**

```powershell
cd webots
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid.ps1 -WorldFile stage2_scenario_front.wbt -RunName front_测试1 -Runner 你的名字 -Timeout 24 -WaitSeconds 34
```

把 `front_测试1` 换成 `front_测试2`、`front_测试3` 再跑两次。

然后打开 `logs/random_avoid/你的名字/` 里的日志，对比三次的 `error=`。

**你会看到一个有意思的结果**——但先不说是什么，自己看了再回来聊。

---

## 10. 一句话总结

> **看不懂就问 AI，但别信它说「已经好了」——自己跑一遍。**

这个项目的所有规矩，核心只有一条：

> **只报实际跑出来的数，失败样本也要留着。**

因为我们要的是「这个算法到底行不行」，不是「看起来行不行」。
