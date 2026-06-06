# Demo 录制说明

建议录制 3-5 分钟，文件名用 `Demo.mp4`。

## 推荐方式一：PowerPoint 自带录制

1. 打开 `答辩 PPT.pptx`。
2. 进入“幻灯片放映” -> “录制”。
3. 前 1 分钟讲项目背景和目标。
4. 切到终端或 Git Bash，演示命令：

```bash
cd /d/linux开发
export LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONIOENCODING=utf-8
./ops-assist help
./ops-assist all
ls reports
head -80 reports/report_*.md
bash tests/test_workflow.sh
git log --oneline -8
```

5. 回到 PPT 第 7-8 页讲 Git 迭代、分工和总结。
6. 录制结束后导出为 MP4。

## 推荐方式二：OBS 录屏

1. 打开 OBS，新建“显示器采集”或“窗口采集”。
2. 分辨率建议 1920x1080，帧率 30 FPS。
3. 音频只保留麦克风，录制格式选 MP4 或 MKV 后转 MP4。
4. 按下面时间轴录：
   - 0:00-0:40 项目简介与目标
   - 0:40-1:30 系统设计和 Linux 技术
   - 1:30-3:20 终端演示完整流程和报告
   - 3:20-4:10 测试与 Git 记录
   - 4:10-4:40 总结和后续改进

## 录制前检查

- 终端字体调大到 16-18。
- 桌面不要露出无关窗口。
- 先运行一次 `./ops-assist all`，确认报告能生成。
- 如果现场在 Windows Git Bash 演示，先执行：

```bash
export LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONIOENCODING=utf-8
```

- 如果老师要求 Linux 环境，优先用 WSL/Ubuntu 或实验机演示。
