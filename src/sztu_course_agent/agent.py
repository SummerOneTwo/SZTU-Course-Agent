import asyncio
import os
import json
from dotenv import load_dotenv

from openai import AsyncOpenAI
from openai_agents import Agent, ContentItem

from .tools.course_loader import CourseLoader
from .core.csp_solver import CSPSolver
from .core.conflict_detector import ConflictDetector
from .models.user_preference import Preference
from .tools.schedule_builder import ScheduleBuilder
from .model_config import get_model_info, get_base_url, validate_config

# 加载环境变量 (主要用于 OPENAI_API_KEY)
load_dotenv()

# 初始化资源
loader = CourseLoader.auto_load()
builder = ScheduleBuilder()
detector = ConflictDetector()

def get_agent() -> Agent:
    """初始化并配置课程选择 Agent

    Uses LiteLLM for multi-provider support via model parameter.
    """
    # Get model configuration
    model_info = get_model_info()

    # Validate configuration
    is_valid, error_msg = validate_config()
    if not is_valid:
        raise ValueError(f"Invalid LLM configuration: {error_msg}")

    # Get base URL if applicable (for local models like Ollama)
    base_url = get_base_url()

    # Create OpenAI client with optional custom base URL
    client = AsyncOpenAI(base_url=base_url) if base_url else AsyncOpenAI()

    agent = Agent(
        model=model_info.model,  # Use LiteLLM model string
        client=client,
        name="CourseSelectorAgent",
        instructions=(
            "你是一个名为 SZTU 选课助手的智能助手。你可以帮助学生查询课程、检测冲突、生成选课方案以及展示课表。\n"
            "当你需要获取课程信息时，使用 search_courses 工具。\n"
            "当用户希望你基于某些课程生成一个没有冲突的排课方案时，使用 generate_selection_plan 工具。\n"
            "当用户需要进行冲突调整（某门课不可用，需要找替代方案）时，使用 resolve_conflict 工具。\n"
            "当用户想从多个候选课程中选择最优组合时，使用 optimize_selection 工具。\n"
            "回答用户问题时，保持专业、热心，并使用清晰的格式(如 Markdown 列表或表格)。"
        ),
    )

    @agent.function
    async def search_courses(query: str) -> str:
        """根据关键词搜索课程信息

        Args:
            query: 搜索关键词（如课程名、教师名、上课时间或教室等）

        Returns:
            一段包含匹配课程详细信息的格式化字符串
        """
        if not loader._courses:
            return "课程数据未加载或加载失败，请检查数据文件。"

        results = loader.search(query)
        if not results:
            return f"未找到与 '{query}' 相关的课程。"

        # 格式化输出前 10 条结果
        output = [f"找到 {len(results)} 门相关课程，以下是前 10 门：\n"]
        for i, c in enumerate(results[:10], 1):
            output.append(
                f"{i}. {c.kcmc} (教师: {c.skls})\n"
                f"   - 时间地点: {c.sksj.strip()}\n"
                f"   - 学分: {c.xf} | 容量: {c.xkrs}/{c.pkrs}\n"
                f"   - 课程 ID: {c.kcid} | 教学班 ID: {c.jx0404id}\n"
            )
        return "\n".join(output)

    @agent.function
    async def generate_selection_plan(course_names: list[str]) -> str:
        """根据用户提供的必须选择的课程名称列表，生成无时间冲突的选课方案

        Args:
            course_names: 包含课程名称的字符串列表，例如 ["高等数学A", "大学英语"]

        Returns:
            生成的无冲突方案详情字符串
        """
        if not loader._courses:
            return "课程数据未加载或加载失败，请检查数据文件。"

        if not course_names:
            return "未提供任何课程名称，无法生成方案。"

        solver = CSPSolver(Preference())
        # 生成最多 3 个方案
        solutions = solver.solve_with_requirements(
            loader.get_all_courses(),
            course_names,
            max_solutions=3
        )

        if not solutions:
            return "抱歉，无法为这些课程生成无冲突的排课方案。可能存在无法避免的时间冲突或课程已满。"

        output = [f"已为您生成 {len(solutions)} 个无冲突选课方案：\n"]
        for i, sol in enumerate(solutions, 1):
            output.append(f"### 方案 {i} (评分: {sol.score:.1f}, 总学分: {sol.total_credits})\n")
            for c in sol.courses:
                output.append(f"- **{c.kcmc}** (教师: {c.skls}) | 时间: {c.sksj.strip()}")
            output.append("\n")

            # 提供一个可视化课表
            schedule_str = builder.render_schedule(sol.courses, f"方案 {i} 课表")
            # 将富文本转为纯文本或直接包含(取决于 UI)
            output.append("```\n" + schedule_str + "\n```\n")

        return "\n".join(output)

    @agent.function
    async def resolve_conflict(
        current_courses_str: str,
        locked_course_ids: list[str],
        replace_course_ids: list[str]
    ) -> str:
        """冲突调整工具：当某些课程不可用（取消/满员）时，找到最小改动的替代方案

        Args:
            current_courses_str: 当前课表的课程信息，格式为JSON字符串，包含课程基本信息
                              格式: [{"name": "课程名", "jx0404id": "教学班ID"}, ...]
            locked_course_ids: 锁定的教学班ID列表（必须保留的课程）
            replace_course_ids: 需要替换的教学班ID列表

        Returns:
            调整后的选课方案详情字符串，包含调整说明
        """
        if not loader._courses:
            return "课程数据未加载或加载失败，请检查数据文件。"

        try:
            current_courses_info = json.loads(current_courses_str)
        except json.JSONDecodeError:
            return "课程信息格式错误，请提供有效的JSON格式。"

        # 收集当前课程
        current_courses = []
        all_courses = loader.get_all_courses()

        # 构建课程ID到课程的映射
        course_by_id = {c.jx0404id: c for c in all_courses}

        # 找到当前课程
        for course_info in current_courses_info:
            jx_id = course_info.get("jx0404id")
            if jx_id in course_by_id:
                current_courses.append(course_by_id[jx_id])

        if not current_courses:
            return "未能找到当前课程，请检查课程ID是否正确。"

        # 收集被替换课程的名称，并查找替代课程
        replace_set = set(replace_course_ids)
        alternatives_by_course_name = {}
        all_courses_by_name = loader._courses_by_name if hasattr(loader, '_courses_by_name') else {}

        # 构建课程名索引
        if not all_courses_by_name:
            for course in all_courses:
                if course.kcmc not in all_courses_by_name:
                    all_courses_by_name[course.kcmc] = []
                all_courses_by_name[course.kcmc].append(course)

        for course in current_courses:
            if course.jx0404id in replace_set:
                # 收集其他课程（不包括被替换的课程）
                other_courses = [c for c in current_courses if c.jx0404id not in replace_set and c.jx0404id != course.jx0404id]
                # 查找替代课程
                alternatives = detector.find_alternatives_for_course(
                    course,
                    other_courses,
                    all_courses_by_name,
                    cross_course_search=True
                )
                alternatives_by_course_name[course.kcmc] = alternatives

        # 使用 CSP 求解器进行冲突调整
        preference = Preference()
        preference.locked_courses = locked_course_ids

        solver = CSPSolver(preference)
        solution = solver.solve_conflict_adjustment(
            current_courses=current_courses,
            locked_course_ids=locked_course_ids,
            replace_course_ids=replace_course_ids,
            alternatives_by_course_name=alternatives_by_course_name
        )

        if not solution:
            return "抱歉，无法找到可行的调整方案。可能是所有替代课程都与现有课表冲突。"

        output = [f"已为您找到调整方案：\n"]
        output.append(f"课程数: {solution.total_courses} | 学分: {solution.total_credits:.1f} | 评分: {solution.score:.1f}/100\n\n")

        if solution.metadata.get('adjustments'):
            output.append("**调整说明：**\n")
            for adj in solution.metadata['adjustments']:
                output.append(f"- {adj}\n")
            output.append("\n")

        output.append("**调整后的课程列表：**\n")
        for i, c in enumerate(solution.courses, 1):
            lock_marker = " [锁定]" if c.jx0404id in locked_course_ids else ""
            output.append(f"{i}. {c.kcmc}{lock_marker} (教师: {c.skls}) | 时间: {c.sksj.strip()}\n")

        return "\n".join(output)

    @agent.function
    async def optimize_selection(
        candidate_course_names: list[str],
        must_have_course_names: list[str],
        priorities: dict = None
    ) -> str:
        """优化选课工具：从多个候选课程中选择最优组合，最大化优先级总和

        Args:
            candidate_course_names: 候选课程名称列表
            must_have_course_names: 必选课程名称列表（必须在结果中出现）
            priorities: 课程优先级字典，格式 {"课程名": 优先级(1-10)}，默认优先级为5

        Returns:
            最优选课方案详情字符串，包含被舍弃的课程及原因
        """
        if not loader._courses:
            return "课程数据未加载或加载失败，请检查数据文件。"

        if priorities is None:
            priorities = {}

        all_courses = loader.get_all_courses()

        # 构建课程名索引
        all_courses_by_name = loader._courses_by_name if hasattr(loader, '_courses_by_name') else {}
        if not all_courses_by_name:
            for course in all_courses:
                if course.kcmc not in all_courses_by_name:
                    all_courses_by_name[course.kcmc] = []
                all_courses_by_name[course.kcmc].append(course)

        # 收集候选课程
        candidate_courses_by_name = {}
        missing_courses = []

        for name in candidate_course_names:
            if name in all_courses_by_name and all_courses_by_name[name]:
                candidate_courses_by_name[name] = all_courses_by_name[name]
            else:
                # 尝试模糊匹配
                matched = False
                for course_name in all_courses_by_name.keys():
                    if name in course_name or course_name in name:
                        candidate_courses_by_name[name] = all_courses_by_name[course_name]
                        matched = True
                        break
                if not matched:
                    missing_courses.append(name)

        if not candidate_courses_by_name:
            return "未找到任何匹配的候选课程。"

        if missing_courses:
            return f"未找到以下课程：{', '.join(missing_courses)}"

        # 检查必选课程是否都在候选列表中
        missing_must_have = []
        for name in must_have_course_names:
            if name not in candidate_courses_by_name:
                missing_must_have.append(name)

        if missing_must_have:
            return f"必选课程不在候选列表中：{', '.join(missing_must_have)}"

        # 使用 CSP 求解器进行优化选课
        preference = Preference()
        preference.course_priorities = priorities

        solver = CSPSolver(preference)
        solutions = solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=priorities,
            must_have_courses=must_have_course_names,
            max_solutions=1
        )

        if not solutions:
            return "抱歉，无法找到可行的选课方案。可能是必选课程之间存在时间冲突。"

        solution = solutions[0]

        output = [f"已为您生成最优选课方案：\n"]
        output.append(f"课程数: {solution.total_courses} | 学分: {solution.total_credits:.1f} | 评分: {solution.score:.1f}/100\n\n")

        output.append("**已选课程：**\n")
        for i, c in enumerate(solution.courses, 1):
            is_must_have = c.kcmc in must_have_course_names
            priority = priorities.get(c.kcmc, 5)
            must_marker = " [必选]" if is_must_have else ""
            output.append(f"{i}. {c.kcmc}{must_marker} (优先级: {priority}) | 教师: {c.skls} | 时间: {c.sksj.strip()}\n")

        # 显示被舍弃的课程
        discarded = solution.metadata.get('discarded_courses', [])
        if discarded:
            output.append("\n**被舍弃的课程及原因：**\n")
            for item in discarded:
                output.append(f"- {item['name']}: {item['reason']}\n")

        return "\n".join(output)
    return agent
