# Webots 初学者启动说明：随机多障碍避障

这份说明只解决一件事：让你自己启动、观察、停止实验。避障原理留给你和 ChatGPT 边看边学。

本次打开的世界：

- 世界：`webots/worlds/stage2_random_obstacles.wbt`
- 固定 `seed=7`，4 个障碍，目标在 `(1.0, 0)`
- 控制器：`avoid_controller`（机器人自己避障）
- Supervisor：`avoid_supervisor`（只记录真值，不参与控制）

## 1. 如何启动实验

1. 打开 `D:\A.me\Simulate robot\webots`。
2. 双击 `START_RANDOM_AVOID.bat`。
3. 会弹出一个黑色控制台，然后 Webots 自动打开。
4. Webots 默认是**暂停**状态。在 Webots 顶部工具栏点击 **Run（绿色三角形）**，机器人才开始动。
5. 黑色控制台不要关，它会等 Webots 结束后显示结果。

不要双击 `tools\run_avoid.ps1`。它是被 BAT 调用的；直接双击会提示 `WorldFile`。

## 2. Webots 里哪个按钮运行、暂停

在 Webots 顶部工具栏：

- **Run**：绿色三角形，开始或继续仿真。
- **Pause**：两条竖线，暂停。暂停时仿真时间也停住，可以慢慢看。
- **Step**：三角形加一条竖线，暂停时点一下走一个时间步（32 ms），适合观察传感器和位姿变化。
- **Reload**：圆形箭头，重新加载世界。一般不用；想重来建议关掉 Webots 再双击 BAT。

启动脚本使用 `--mode=pause`，所以打开时不会自己跑，必须点 Run。如果机器人跑得太快，点工具栏的 **Real-time**（时钟）按钮；正常情况不需要改。

## 3. 如何观察机器人

- 摄像机默认跟随 e-puck。鼠标左键拖动旋转视角，滚轮缩放。
- 小机器人是 e-puck；红/橙/蓝/紫色方块是障碍；绿色圆柱是目标点。
- 观察顺序：先朝目标直行 → 前方传感器变大 → BRAKE → 左右转 → MOVE_AROUND → 重新朝目标。
- 想看传感器数值：在 3D 视图里双击机器人，或右键机器人选择 **Show Robot Window**。e-puck 窗口会显示 8 个 proximity sensor 的读数。
- 机器人自己的日志在 `logs/avoid_controller.log`，每 0.5 秒一行 `TRACE`，状态变化时一行 `DECISION`。

Supervisor 的 `POSE` / `RESULT: true_end` 是仿真真值，只用于事后验证；机器人控制时看不到它。

## 4. 如何正常停止

三种情况都算正常：

1. **自动结束**：控制器 24 秒超时，Supervisor 在约 25 秒仿真时间调用 `simulationQuit(0)`，Webots 自动关闭。
2. **提前观察**：点 **Pause** 暂停，看完后点 **Run** 继续。
3. **提前结束**：点 **Pause**，再关闭 Webots 窗口（右上角 X）。黑色控制台会继续运行，复制日志并显示结果。

不要用任务管理器结束 Python；也不要直接关黑色控制台，否则可能看不到本次结果。先关 Webots，再等控制台提示按任意键。

## 5. 如何查看结果和日志

黑色控制台最后会显示：

- `CONTROLLER_RESULT=RESULT: ...`：机器人自己的估计结果（可能是 reached/timeout/stuck 等）。
- `SUPERVISOR_RESULT=RESULT: true_end ... error=...`：仿真真值终点和真实误差。
- `CONTROLLER_LOG=...` / `SUPERVISOR_LOG=...`：本次归档文件路径。

工作日志（运行时写入）：

- `webots/logs/avoid_controller.log`
- `webots/logs/avoid_supervisor.log`

归档日志（每次运行单独保存，使用时间戳，不覆盖旧样本）：

- `webots/logs/random_avoid/beginner_stage2_random_obstacles_<时间>_controller.log`
- `..._supervisor.log`
- `..._world.json`

在日志里搜索：

- 控制器：`RESULT:`、`SUMMARY`、`DECISION`
- Supervisor：`RESULT: true_end`、`COLLISION`

控制器结果和 Supervisor 真值可能不一致，这是正常的：轮子打滑会让里程计虚增。判断是否真的到达，以 Supervisor 的 `error` 为准。

## 6. 出错时发给 ChatGPT 什么

把下面这些一起发：

1. 黑色控制台窗口的完整文字（从 `Simulate Robot` 到最后一行），或整窗截图。
2. 错误码，例如 `[ERROR] The launcher exited with code 1`。
3. Webots 是否打开、是否点了 Run、机器人有没有动。
4. `webots/logs/random_avoid/` 下最新的一次 `..._controller.log` 和 `..._supervisor.log`（如果存在），至少发最后 30 行。
5. 如果有弹窗，发弹窗截图。

常见情况：

- `Webots is already running`：先关闭已打开的 Webots，再双击 BAT。
- `World file not found` / `Sidecar JSON not found`：项目文件被移动或缺失，发控制台文字。
- Webots 打开但显示 `(No Project)`：把世界窗口标题和截图发给 ChatGPT。
- 机器人不动：确认已经点 Run，而不是停在 Pause；再看控制器日志是否有 `RESULT: error`。
- 第一次打开很慢：Webots 可能在联网加载官方 PROTO，等一会儿；如果一直卡住，发截图。
