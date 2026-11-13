---
name: Bug 报告
about: 仿真行为不对、控制器逻辑错、工具算错
title: "[bug] "
labels: bug
---

## 现象

<!-- 实际发生了什么。贴日志关键行。 -->

```
SUPERVISOR_RESULT=RESULT: true_end ... error=0.45031
控制器却说 reached
```

## 期望

<!-- 应该是什么样。 -->

## 怎么复现

```bash
# 具体命令
powershell -ExecutionPolicy Bypass -File .\tools\run_avoid.ps1 `
  -WorldFile stage2_random_seed_4.wbt -RunName repro_bug -Seed 4 -Timeout 24 -WaitSeconds 34
```

场景文件：
代码 commit（`git rev-parse --short HEAD`）：

## 已知的排查方向

<!-- 如果你已经查过，写在这里，省得别人重复。 -->
