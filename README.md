# SZTU Course Agent

智能课程冲突检测与选课方案生成系统，基于 Google OR-Tools 实现约束满足问题求解。

## 功能特性

- ⚡ **快速冲突检测**: 检测多门课程的时间冲突
- 📊 **可视化课表**: ASCII 表格和 Markdown 格式输出
- 🧮 **智能方案生成**: 基于 Google OR-Tools 的约束求解
- 📤 **配置导出**: 导出标准 TOML 配置文件
- 💡 **偏好支持**: 支持时间、教师、容量等偏好设置

## 安装

```bash
# 使用 uv
pip install uv
uv sync

# 或使用 pip
pip install -e .
```

## 依赖

- `pydantic>=2.0.0` - 数据模型
- `ortools>=9.11.0` - Google 约束求解工具
- `rich>=13.0.0` - 美化 CLI 输出
- `tomli-w>=1.0.0` - TOML 写入

## 快速开始

### 交互式 CLI

```bash
python -m sztu_course_agent.cli
# 或
sztu-agent
```

功能菜单:
1. 搜索课程 - 按课程名、教师、教室搜索
2. 检测课程冲突 - 检测多门课程是否有时间冲突
3. 生成选课方案 - 使用 CSP 求解器生成无冲突方案
4. 显示课表 - 可视化显示课程安排
5. 退出

### 作为库使用

```python
from sztu_course_agent import CourseLoader, CSPSolver, Preference, SolutionExporter

# 加载课程数据
loader = CourseLoader.auto_load("data/courses.json")

# 创建求解器
solver = CSPSolver(Preference())

# 生成方案
solutions = solver.solve_with_requirements(
    loader.get_all_courses(),
    ["高等数学A", "大学英语", "程序设计基础"],
    max_solutions=3
)

# 导出配置
exporter = SolutionExporter()
exporter.export_to_toml(solutions[0], "config.toml")
```

## 项目结构

```
SZTU-Course-Agent/
├── src/sztu_course_agent/    # 源代码
│   ├── models/               # Pydantic 数据模型
│   │   ├── course.py        # Course, TimeSlot
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
├── tests/                   # 测试
├── examples/                # 使用示例
├── pyproject.toml           # 项目配置
└── README.md
```

## 数据格式

### 课程数据 (JSON)

```json
[
  {
    "kcmc": "高等数学A",
    "kcid": "KC001",
    "jx0404id": "JX001",
    "skls": "张老师",
    "sksj": "1-16周 星期一 8-10",
    "xkrs": 30,
    "pkrs": 50,
    "xf": 4.0
  }
]
```

### 导出配置 (TOML)

```toml
[[courses]]
name = "高等数学A"
kcid = "KC001"
cno = "0"
jx0404id = ["JX001", "JX002"]

[[courses]]
name = "大学英语"
kcid = "KC002"
cno = "0"
jx0404id = ["JX003"]
```

## 运行测试

```bash
pytest tests/ -v
```

## 许可证

MIT License
