# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SZTU Course Agent 是一个智能课程冲突检测与选课方案生成系统，基于 Google OR-Tools 实现约束满足问题求解。

## Common Commands

```bash
# 安装依赖
pip install -e .

# 或使用 uv
uv sync

# 运行示例
python examples/basic_usage.py

# 运行交互式 CLI
python -m sztu_course_agent.cli

# 运行测试
pytest tests/

# 运行测试带覆盖率
pytest tests/ --cov
```

## Project Structure

```
SZTU-Course-Agent/
├── src/sztu_course_agent/    # 源代码包
│   ├── models/               # Pydantic 数据模型
│   │   ├── course.py        # Course, TimeSlot, TeacherInfo
│   │   ├── schedule.py      # Schedule, ConflictInfo
│   │   ├── user_preference.py
│   │   └── solution.py
│   ├── core/                # 核心算法
│   │   ├── time_slot_parser.py
│   │   ├── conflict_detector.py
│   │   └── csp_solver.py
│   ├── tools/               # 工具集
│   │   ├── course_loader.py
│   │   ├── schedule_builder.py
│   │   └── solution_exporter.py
│   └── cli.py               # CLI 入口
├── tests/                   # 单元测试
├── examples/                # 使用示例
│   ├── example_courses.json  # 示例课程数据
│   └── basic_usage.py      # 基本使用示例
├── pyproject.toml           # 项目配置
└── README.md
```

## Architecture

### Models Layer (`src/sztu_course_agent/models/`)
- **Course**: 课程模型，包含 kcid, jx0404id, 时间槽, 实际/最大容量
- **TimeSlot**: 解析后的时间表示 (weeks, day, hours)
- **Preference**: 用户偏好 (时间、教师、容量)
- **SelectionSolution**: 生成的选课方案，含评分

### Core Layer (`src/sztu_course_agent/core/`)
- **time_slots_conflict()**: 检测两个时间槽是否冲突
- **ConflictDetector**: 检测一组课程中的所有冲突
- **CSPSolver**: 使用 Google OR-Tools 的约束求解器
  - 变量: 每门课可选择多个教学班
  - 约束: 无时间冲突、容量限制、学分限制
  - 目标: 最大化课程数和用户偏好分数

### Tools Layer (`src/sztu_course_agent/tools/`)
- **CourseLoader**: 从 JSON 加载课程数据，支持模糊搜索
- **ScheduleBuilder**: 渲染可视化课表 (ASCII/Markdown)
- **SolutionExporter**: 导出 TOML/JSON 格式配置

## Data Format

### 课程数据 (JSON)
```json
{
  "kcmc": "课程名称",
  "kcid": "课程ID",
  "jx0404id": "教学班ID",
  "skls": "教师",
  "sksj": "1-16周 星期一 8-10",
  "xkrs": 30,
  "pkrs": 50,
  "xf": 4.0
}
```

### 导出配置 (TOML)
```toml
[[courses]]
name = "课程名称"
kcid = "KC001"
cno = "0"
jx0404id = ["JX001", "JX002"]
```

## Dependencies

- `ortools>=9.11.0`: Google OR-Tools 约束求解
- `pydantic>=2.0.0`: 数据验证和模型
- `rich>=13.0.0`: CLI 格式化
- `tomli-w>=1.0.0`: TOML 写入

## Chinese Time Slot Parsing

时间字符串格式: `"1-16周 星期一 8-10"` 或 `"1-8,10-16周 星期二 2-4"`
- 周次: 可以是范围或逗号分隔
- 星期: 星期一=1, 星期二=2, ...
- 节次: 整数表示
