# SZTU Course Agent

智能课程冲突检测与选课方案生成系统，基于 Google OR-Tools 实现约束满足问题求解。

## 功能特性

- ⚡ **快速冲突检测**: 检测多门课程的时间冲突
- 📊 **可视化课表**: ASCII 表格和 Markdown 格式输出
- 🧮 **智能方案生成**: 基于 Google OR-Tools 的约束求解
- 📤 **配置导出**: 导出标准 TOML 配置文件
- 💡 **偏好支持**: 支持时间、教师、容量等偏好设置
- 🤖 **AI 智能助手**: 支持自然语言查询课程与生成排课方案 (Beta)
- 🔄 **冲突调整**: 当课程取消或满员时，自动寻找最小改动的替代方案
- 🎯 **优化选课**: 从多个候选课程中选择最优组合，最大化优先级总和

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/SZTU-Course-Agent.git
cd SZTU-Course-Agent

# 使用 pip 安装
pip install -e .

# 或使用 uv
pip install uv
uv sync
```

### 配置环境变量

如需使用 AI 聊天模式，请在项目根目录配置 `.env` 文件：

```bash
cp .env.example .env
# 编辑 .env 文件，设置 LLM_PROVIDER 和相应的 API Key
```

支持的 LLM 提供商：
- **OpenAI**: `LLM_PROVIDER=openai`, 需要 `OPENAI_API_KEY`
- **Anthropic Claude**: `LLM_PROVIDER=claude`, 需要 `ANTHROPIC_API_KEY`
- **Google Gemini**: `LLM_PROVIDER=gemini`, 需要 `GOOGLE_API_KEY`
- **DeepSeek**: `LLM_PROVIDER=deepseek`, 需要 `DEEPSEEK_API_KEY`
- **Local (Ollama)**: `LLM_PROVIDER=local`, 无需 API Key，需要运行 Ollama 服务

## 依赖

- `pydantic>=2.0.0` - 数据模型
- `ortools>=9.11.0` - Google 约束求解工具
- `rich>=13.0.0` - 美化 CLI 输出
- `tomli-w>=1.0.0` - TOML 写入
- `openai-agents>=0.11.1` - OpenAI Agent SDK
- `litellm>=1.0.0` - 统一 LLM 接口，支持 100+ 提供商
- `python-dotenv>=1.2.2` - 环境变量加载
- `pytest>=8.0.0` - 测试框架

## 快速开始

### 交互式 CLI

```bash
python -m sztu_course_agent.cli
# 或
sztu-agent
```

功能菜单:
1. **搜索课程** - 按课程名、教师、教室搜索
2. **检测课程冲突** - 检测多门课程是否有时间冲突
3. **生成选课方案** - 使用 CSP 求解器生成无冲突方案
4. **显示课表** - 可视化显示课程安排
5. **AI 聊天模式** (Beta) - 支持自然语言查询课程与生成排课方案
   - 搜索课程: "帮我搜索高等数学的课程"
   - 生成方案: "我想选高等数学、大学英语和程序设计基础，帮我生成方案"
   - 冲突调整: "我当前的课程表是 [JSON]，数学课取消了，帮我找替代方案"
   - 优化选课: "我想在以下课程中选最优组合：[课程列表]"
6. **退出**

### 作为库使用

```python
from sztu_course_agent import CourseLoader, CSPSolver, Preference, SolutionExporter

# 加载课程数据
loader = CourseLoader.auto("data/courses.json")

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
│   │   ├── course.py        # Course, TimeSlot, TeacherInfo
│   │   ├── schedule.py      # Schedule, ConflictInfo
│   │   ├── user_preference.py
│   │   └── solution.py       # SelectionSolution
│   ├── core/                # 核心算法
│   │   ├── time_slot_parser.py  # 时间槽解析与冲突检测
│   │   ├── conflict_detector.py  # 冲突检测器
│   │   └── csp_solver.py        # 约束满足问题求解器
│   ├── tools/               # 工具集
│   │   ├── course_loader.py     # 课程数据加载
│   │   ├── schedule_builder.py  # 课表可视化
│   │   └── solution_exporter.py # 方案导出
│   ├── agent.py             # AI Agent (OpenAI)
│   └── cli.py               # CLI 入口
├── tests/                   # 单元测试
│   ├── test_time_slot_parser.py
│   ├── test_conflict_detector.py
│   ├── test_csp_solver.py
│   ├── test_conflict_adjustment.py
│   └── test_optimized_selection.py
├── examples/                # 使用示例
│   ├── basic_usage.py
│   └── example_courses.json
├── pyproject.toml           # 项目配置
├── .env.example             # 环境变量示例
├── .gitignore
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
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_csp_solver.py -v

# 运行测试带覆盖率报告
pytest tests/ --cov --cov-report=html
```

## 核心算法

### CSP 求解器 (CSPSolver)

基于 Google OR-Tools 的约束满足问题求解器，支持以下求解模式：

1. **基础选课方案生成** (`solve_with_requirements`)
   - 根据课程名称列表生成无冲突的选课方案
   - 支持多方案生成

2. **冲突调整** (`solve_conflict_adjustment`)
   - 当某些课程不可用时，寻找最小改动的替代方案
   - 支持锁定课程（必须保留的课程）
   - 自动级联解决引入的新冲突

3. **优化选课** (`solve_optimized_selection`)
   - 从多个候选课程中选择最优组合
   - 支持必选课程约束
   - 最大化课程优先级总和
   - 提供被舍弃课程的详细原因

### 冲突检测器 (ConflictDetector)

- 检测单个时间槽冲突
- 检测课程列表中的所有冲突
- 查找不冲突的替代课程
- 支持跨课程搜索替代方案

## AI Agent 功能

AI Agent 使用 LiteLLM 作为统一接口，支持多种 LLM 提供商：

- **OpenAI** - GPT-4, GPT-3.5 等
- **Anthropic Claude** - Claude 3.5 Sonnet, Opus 等
- **Google Gemini** - Gemini 2.0 Flash, Pro 等
- **DeepSeek** - DeepSeek Chat/V3
- **Local Models** - Ollama, vLLM 等本地部署

通过设置 `LLM_PROVIDER` 环境变量即可切换不同的 AI 提供商。

AI Agent 提供以下工具函数：

- `search_courses(query)` - 搜索课程
- `generate_selection_plan(course_names)` - 生成选课方案
- `resolve_conflict(current_courses_str, locked_course_ids, replace_course_ids)` - 冲突调整
- `optimize_selection(candidate_course_names, must_have_course_names, priorities)` - 优化选课

## 许可证

MIT License

## 作者

Sisyphus
