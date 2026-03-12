#!/usr/bin/env python3
"""
AI Agent 选课冲突解决系统 - 命令行交互入口

使用方式:
    uv run -m agent.cli
"""
import sys
import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import asyncio

try:
    from .agent import get_agent
    from .model_config import get_model_info, validate_config, get_supported_providers
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

from .tools.course_loader import CourseLoader
from .core.csp_solver import CSPSolver
from .models.user_preference import Preference
from .tools.schedule_builder import ScheduleBuilder
from .tools.solution_exporter import SolutionExporter
from .core.conflict_detector import ConflictDetector


class AgentCLI:
    """Agent CLI 主类"""

    def __init__(self):
        self.console = Console()
        self.loader = None
        self.builder = ScheduleBuilder()
        self.exporter = SolutionExporter()
        self.preference = Preference()

    def welcome(self):
        """欢迎信息"""
        self.console.print(Panel(
            "[bold cyan]AI Agent 选课冲突解决系统[/bold cyan]\n\n"
            "帮助您:\n"
            "• 检测课程时间冲突\n"
            "• 生成无冲突的选课方案\n"
            "• 导出配置文件用于抢课脚本",
            title="[bold]SZTU Course Selector Agent[/bold]",
            border_style="cyan"
        ))

    def load_courses(self):
        """加载课程数据"""
        self.console.print("\n[bold]加载课程数据...[/bold]")

        self.loader = CourseLoader.auto_load()

        if not self.loader._courses:
            self.console.print("[red]❌ 未能加载课程数据![/red]")
            self.console.print("请确保在项目根目录运行，且有课程数据 JSON 文件")
            return False

        self.console.print(f"[green]✓[/green] 已加载 {len(self.loader._courses)} 门课程")
        return True

    def search_courses(self):
        """搜索课程"""
        if not self.loader:
            if not self.load_courses():
                return

        self.console.print("\n[bold]搜索课程[/bold]")
        query = Prompt.ask("请输入搜索关键词 (课程名/教师/教室)", default="")

        if not query:
            return

        results = self.loader.search(query)

        if not results:
            self.console.print(f"[yellow]未找到匹配的课程: {query}[/yellow]")
            return

        self.console.print(f"\n找到 {len(results)} 门课程:\n")
        self._display_course_list(results[:20])  # 显示前20条

    def detect_conflicts(self):
        """检测冲突"""
        if not self.loader:
            if not self.load_courses():
                return

        self.console.print("\n[bold]检测课程冲突[/bold]")
        self.console.print("请输入要检测的课程 (每行一个课程名，输入空行结束):")

        course_names = []
        while True:
            name = Prompt.ask(f"课程 {len(course_names) + 1}", default="")
            if not name:
                break
            course_names.append(name)

        if not course_names:
            self.console.print("[yellow]未输入任何课程[/yellow]")
            return

        # 收集所有教学班
        all_courses = []
        for name in course_names:
            matches = self.loader.get_by_name(name, fuzzy=True)
            if matches:
                all_courses.extend(matches[:5])  # 每门课取前5个教学班
            else:
                self.console.print(f"[yellow]未找到: {name}[/yellow]")

        if not all_courses:
            self.console.print("[yellow]未找到任何课程[/yellow]")
            return

        # 检测冲突
        conflicts = self.builder.detector.find_conflicts(all_courses)

        if not conflicts:
            self.console.print("[green]✓ 未检测到冲突![/green]")
        else:
            self.console.print(f"\n[red]⚠️ 发现 {len(conflicts)} 个冲突:[/red]\n")
            for i, conflict in enumerate(conflicts, 1):
                self.console.print(f"  {i}. [bold cyan]{conflict.course1.kcmc}[/boldcyan] 与 [bold cyan]{conflict.course2.kcmc}[/boldcyan]")
                self.console.print(f"     时间: {conflict.course1.sksj.strip()} vs {conflict.course2.sksj.strip()}")
                self.console.print("")

    def generate_solutions(self):
        """生成选课方案"""
        if not self.loader:
            if not self.load_courses():
                return

        self.console.print("\n[bold]生成选课方案[/bold]")
        self.console.print("请输入想要选的课程名称 (每行一个，输入空行结束):")

        course_names = []
        while True:
            name = Prompt.ask(f"课程 {len(course_names) + 1}", default="")
            if not name:
                break
            course_names.append(name)

        if not course_names:
            self.console.print("[yellow]未输入任何课程[/yellow]")
            return

        # 输入方案数量
        max_solutions = Prompt.ask("生成方案数量", default="3")

        try:
            max_solutions = int(max_solutions)
        except ValueError:
            max_solutions = 3

        self.console.print(f"\n[bold]正在生成 {max_solutions} 个方案...[/bold]")

        # 使用 CSP 求解器
        solver = CSPSolver(self.preference)
        solutions = solver.solve_with_requirements(
            self.loader.get_all_courses(),
            course_names,
            max_solutions=max_solutions
        )

        if not solutions:
            self.console.print("[red]❌ 无法生成无冲突方案![/red]")
            self.console.print("可能原因:\n"
                              "• 课程之间全部冲突\n"
                              "• 找不到匹配的课程\n"
                              "• 容量已满")
            return

        # 显示方案
        self._display_solutions(solutions)

        # 询问是否导出
        if Confirm.ask("\n是否导出方案到配置文件?", default=True):
            self._export_solutions(solutions)

    def _display_course_list(self, courses):
        """显示课程列表"""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", width=4)
        table.add_column("课程名称", width=25)
        table.add_column("教师", width=10)
        table.add_column("容量", width=10)
        table.add_column("时间", width=30)

        for i, course in enumerate(courses, 1):
            capacity = f"{course.xkrs}/{course.pkrs}"
            if course.is_full:
                capacity = f"[red]{capacity} (满)[/red]"

            table.add_row(
                str(i),
                course.kcmc[:24],
                course.skls[:9],
                capacity,
                course.sksj.strip()[:29]
            )

        self.console.print(table)

    def _display_solutions(self, solutions):
        """显示方案列表"""
        for i, solution in enumerate(solutions, 1):
            self.console.print(f"\n{'=' * 60}")
            self.console.print(f"[bold cyan]方案 {i}[/bold cyan] - 评分: {solution.score:.1f}/100")
            self.console.print(f"课程数: {solution.total_courses} | 学分: {solution.total_credits:.1f}")

            if solution.has_conflicts:
                self.console.print(f"[red]⚠️ {len(solution.conflicts)} 个冲突[/red]")
            else:
                self.console.print("[green]✓ 无冲突[/green]")

            self.console.print("\n[bold]课程列表:[/bold]")
            for j, course in enumerate(solution.courses, 1):
                self.console.print(f"  {j}. {course.kcmc} ({course.skls})")
                self.console.print(f"     时间: {course.sksj.strip()}")

    def _export_solutions(self, solutions):
        """导出方案"""
        # 选择方案
        choice = Prompt.ask(
            "选择要导出的方案 (输入方案编号，0=全部)",
            default="1"
        )

        if choice == "0":
            output_dir = Prompt.ask("输出目录", default="solutions")
            self.exporter.export_multiple_solutions(solutions, output_dir)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(solutions):
                    solution = solutions[idx]
                    filename = Prompt.ask("输出文件名", default=f"solution_{idx + 1}.toml")
                    self.exporter.export_to_toml(solution, filename)
                    self.console.print("\n[bold]配置预览:[/bold]")
                    self.console.print(Panel(
                        self.exporter.generate_config_template(solution),
                        title="config.toml"
                    ))
                else:
                    self.console.print(f"[red]无效的方案编号[/red]")
            except ValueError:
                self.console.print(f"[red]无效输入[/red]")

    def show_schedule(self):
        """显示课表"""
        if not self.loader:
            if not self.load_courses():
                return

        self.console.print("\n[bold]显示课表[/bold]")
        self.console.print("请输入要显示的课程 (每行一个，输入空行结束):")

        course_names = []
        while True:
            name = Prompt.ask(f"课程 {len(course_names) + 1}", default="")
            if not name:
                break
            course_names.append(name)

        if not course_names:
            self.console.print("[yellow]未输入任何课程[/yellow]")
            return

        # 收集课程
        courses = []
        for name in course_names:
            matches = self.loader.get_by_name(name, fuzzy=True)
            if matches:
                courses.append(matches[0])  # 取第一个

        if courses:
            self.console.print(self.builder.render_schedule(courses, "我的课表"))
        else:
            self.console.print("[yellow]未找到任何课程[/yellow]")

    def conflict_adjustment(self):
        """冲突调整功能"""
        if not self.loader:
            if not self.load_courses():
                return

        self.console.print("\n[bold]冲突调整[/bold]")
        self.console.print("当某门课不可用（取消/满员）时，找到最小改动的替代方案\n")

        # 输入当前课表
        self.console.print("请输入当前课表的课程 (每行一个，输入空行结束):")
        current_course_names = []
        while True:
            name = Prompt.ask(f"课程 {len(current_course_names) + 1}", default="")
            if not name:
                break
            current_course_names.append(name)

        if not current_course_names:
            self.console.print("[yellow]未输入任何课程[/yellow]")
            return

        # 收集当前课程
        current_courses = []
        for name in current_course_names:
            matches = self.loader.get_by_name(name, fuzzy=True)
            if matches:
                current_courses.append(matches[0])  # 取第一个

        if not current_courses:
            self.console.print("[yellow]未找到任何课程[/yellow]")
            return

        # 显示当前课程
        self.console.print("\n[bold cyan]当前课程列表：[/bold cyan]")
        for i, c in enumerate(current_courses, 1):
            self.console.print(f"  {i}. {c.kcmc} ({c.jx0404id}) - {c.skls}")

        # 输入锁定课程
        self.console.print("\n[bold yellow]锁定课程[/bold yellow] (必须保留的课程)")
        self.console.print("请输入要锁定的课程编号 (多个用逗号分隔，直接回车跳过):")
        locked_input = Prompt.ask("锁定课程", default="")
        locked_course_ids = []
        if locked_input:
            try:
                indices = [int(x.strip()) for x in locked_input.split(',')]
                for idx in indices:
                    if 1 <= idx <= len(current_courses):
                        locked_course_ids.append(current_courses[idx - 1].jx0404id)
            except ValueError:
                pass

        # 输入需要替换的课程
        self.console.print("\n[bold yellow]需要替换的课程[/bold yellow]")
        self.console.print("请输入要替换的课程编号 (多个用逗号分隔):")
        replace_input = Prompt.ask("替换课程", default="")

        if not replace_input:
            self.console.print("[yellow]未选择需要替换的课程[/yellow]")
            return

        try:
            indices = [int(x.strip()) for x in replace_input.split(',')]
            replace_course_ids = []
            for idx in indices:
                if 1 <= idx <= len(current_courses):
                    replace_course_ids.append(current_courses[idx - 1].jx0404id)
        except ValueError:
            self.console.print("[red]输入格式错误[/red]")
            return

        if not replace_course_ids:
            self.console.print("[yellow]无效的课程编号[/yellow]")
            return

        self.console.print(f"\n[bold]正在查找替代方案...[/bold]")

        # 构建课程名索引
        all_courses_by_name = self.loader._courses_by_name if hasattr(self.loader, '_courses_by_name') else {}
        if not all_courses_by_name:
            all_courses = self.loader.get_all_courses()
            for course in all_courses:
                if course.kcmc not in all_courses_by_name:
                    all_courses_by_name[course.kcmc] = []
                all_courses_by_name[course.kcmc].append(course)

        # 收集替代课程
        alternatives_by_course_name = {}
        for course in current_courses:
            if course.jx0404id in replace_course_ids:
                other_courses = [c for c in current_courses if c.jx0404id not in replace_course_ids and c.jx0404id != course.jx0404id]
                alternatives = self.builder.detector.find_alternatives_for_course(
                    course,
                    other_courses,
                    all_courses_by_name,
                    cross_course_search=True
                )
                alternatives_by_course_name[course.kcmc] = alternatives

        # 使用 CSP 求解器
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
            self.console.print("[red]❌ 无法找到可行的调整方案[/red]")
            self.console.print("可能原因:\n"
                              "• 所有替代课程都与现有课表冲突\n"
                              "• 没有可用的替代课程")
            return

        self.console.print(f"\n[bold cyan]调整完成![/bold cyan]")
        self.console.print(f"课程数: {solution.total_courses} | 学分: {solution.total_credits:.1f} | 评分: {solution.score:.1f}/100\n")

        if solution.metadata.get('adjustments'):
            self.console.print("[bold yellow]调整说明：[/bold yellow]")
            for adj in solution.metadata['adjustments']:
                self.console.print(f"  • {adj}")
            self.console.print("")

        self.console.print("[bold]调整后的课程列表：[/bold]")
        for i, c in enumerate(solution.courses, 1):
            lock_marker = " [锁定]" if c.jx0404id in locked_course_ids else ""
            self.console.print(f"  {i}. {c.kcmc}{lock_marker} ({c.skls})")
            self.console.print(f"     时间: {c.sksj.strip()}")

    def optimized_selection(self):
        """优化选课功能"""
        if not self.loader:
            if not self.load_courses():
                return

        self.console.print("\n[bold]优化选课[/bold]")
        self.console.print("在约束下最大化选到高优先级的课程\n")

        # 输入候选课程
        self.console.print("请输入候选课程 (每行一个，输入空行结束):")
        candidate_course_names = []
        while True:
            name = Prompt.ask(f"课程 {len(candidate_course_names) + 1}", default="")
            if not name:
                break
            candidate_course_names.append(name)

        if not candidate_course_names:
            self.console.print("[yellow]未输入任何课程[/yellow]")
            return

        # 输入必选课程
        self.console.print("\n[bold yellow]必选课程[/bold yellow] (必须在结果中出现)")
        self.console.print("请输入必选课程编号 (多个用逗号分隔，直接回车跳过):")
        must_have_input = Prompt.ask("必选课程", default="")
        must_have_course_names = []
        if must_have_input:
            try:
                indices = [int(x.strip()) for x in must_have_input.split(',')]
                for idx in indices:
                    if 1 <= idx <= len(candidate_course_names):
                        must_have_course_names.append(candidate_course_names[idx - 1])
            except ValueError:
                pass

        # 输入优先级
        self.console.print("\n[bold yellow]设置优先级[/bold yellow] (1-10，默认为5)")
        self.console.print("格式: 课程编号:优先级 (多个用逗号分隔，直接回车跳过)")
        self.console.print("示例: 1:8,2:6,3:10")
        priority_input = Prompt.ask("优先级设置", default="")
        priorities = {}
        if priority_input:
            try:
                for item in priority_input.split(','):
                    parts = item.strip().split(':')
                    if len(parts) == 2:
                        idx = int(parts[0])
                        priority = int(parts[1])
                        if 1 <= idx <= len(candidate_course_names) and 1 <= priority <= 10:
                            priorities[candidate_course_names[idx - 1]] = priority
            except ValueError:
                pass

        self.console.print(f"\n[bold]正在生成最优方案...[/bold]")

        # 构建课程名索引
        all_courses = self.loader.get_all_courses()
        all_courses_by_name = self.loader._courses_by_name if hasattr(self.loader, '_courses_by_name') else {}
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

        if missing_courses:
            self.console.print(f"[yellow]未找到以下课程: {', '.join(missing_courses)}[/yellow]")

        if not candidate_courses_by_name:
            self.console.print("[yellow]未找到任何候选课程[/yellow]")
            return

        # 检查必选课程
        missing_must_have = []
        for name in must_have_course_names:
            if name not in candidate_courses_by_name:
                missing_must_have.append(name)

        if missing_must_have:
            self.console.print(f"[red]必选课程不在候选列表中: {', '.join(missing_must_have)}[/red]")
            return

        # 使用 CSP 求解器
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
            self.console.print("[red]❌ 无法找到可行的选课方案[/red]")
            self.console.print("可能原因:\n"
                              "• 必选课程之间存在时间冲突\n"
                              "• 没有可用的课程")
            return

        solution = solutions[0]
        self.console.print(f"\n[bold cyan]最优方案生成完成![/bold cyan]")
        self.console.print(f"课程数: {solution.total_courses} | 学分: {solution.total_credits:.1f} | 评分: {solution.score:.1f}/100\n")

        self.console.print("[bold]已选课程：[/bold]")
        for i, c in enumerate(solution.courses, 1):
            is_must_have = c.kcmc in must_have_course_names
            priority = priorities.get(c.kcmc, 5)
            must_marker = " [必选]" if is_must_have else ""
            self.console.print(f"  {i}. {c.kcmc}{must_marker} (优先级: {priority})")
            self.console.print(f"     教师: {c.skls} | 时间: {c.sksj.strip()}")

        # 显示被舍弃的课程
        discarded = solution.metadata.get('discarded_courses', [])
        if discarded:
            self.console.print("\n[bold yellow]被舍弃的课程及原因：[/bold yellow]")
            for item in discarded:
                self.console.print(f"  • {item['name']}: {item['reason']}")

    def chat_mode(self):
        """AI Chat 模式"""
        if not AGENT_AVAILABLE:
            self.console.print("[red]❌ AI 助手模块不可用。请确保已配置好 openai-agents 和 .env 文件。[/red]")
            return

        # Get and display model configuration
        model_info = get_model_info()
        is_valid, error_msg = validate_config()

        if not is_valid:
            self.console.print(f"[red]❌ 配置错误: {error_msg}[/red]")
            self.console.print("\n[bold]支持的提供商:[/bold]")
            for provider in get_supported_providers():
                self.console.print(f"  • {provider}")
            self.console.print("\n[bold]使用方法:[/bold]")
            self.console.print("  设置 LLM_PROVIDER 环境变量并配置相应的 API Key")
            return

        self.console.print("\n[bold cyan]=== AI 选课助手聊天模式 ===[/bold cyan]")
        self.console.print(f"[bold]使用模型:[/bold] {model_info.display_name}\n")
        if model_info.api_key_env:
            self.console.print(f"[dim]配置文件: {model_info.api_key_env}[/dim]\n")
        else:
            self.console.print("[dim]本地模型 (无需 API Key)[/dim]\n")
        self.console.print("提示: 输入 'exit' 或 'quit' 退出聊天模式\n")

        agent = get_agent()

        async def run_chat():
            while True:
                user_msg = Prompt.ask("[bold green]用户[/bold green]")
                if user_msg.lower() in ('exit', 'quit'):
                    break
                if not user_msg.strip():
                    continue

                self.console.print("[bold cyan]助手思考中...[/bold cyan]")
                try:
                    # 调用 agent 运行
                    response = await agent.run(user_msg)
                    # 输出内容
                    self.console.print(f"\n[bold blue]助手:[/bold blue] {response.content}\n")
                except Exception as e:
                    self.console.print(f"[red]❌ 发生错误: {e}[/red]\n")
                    
        # 运行异步事件循环
        try:
            asyncio.run(run_chat())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]已退出聊天模式[/yellow]")

    def run(self):
        """运行 CLI"""
        self.welcome()

        while True:
            self.console.print("\n[bold]主菜单:[/bold]")
            self.console.print("  1. 搜索课程")
            self.console.print("  2. 检测课程冲突")
            self.console.print("  3. 生成选课方案")
            self.console.print("  4. 显示课表")
            self.console.print("  5. 冲突调整")
            self.console.print("  6. 优化选课")
            self.console.print("  7. AI 聊天模式 (Beta)")
            self.console.print("  8. 退出")

            choice = Prompt.ask("\n请选择", choices=["1", "2", "3", "4", "5", "6", "7", "8"], default="1")

            if choice == "1":
                self.search_courses()
            elif choice == "2":
                self.detect_conflicts()
            elif choice == "3":
                self.generate_solutions()
            elif choice == "4":
                self.show_schedule()
            elif choice == "5":
                self.conflict_adjustment()
            elif choice == "6":
                self.optimized_selection()
            elif choice == "7":
                self.chat_mode()
            elif choice == "8":
                self.console.print("\n[green]再见![/green]")
                break


def main():
    """入口函数"""
    cli = AgentCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n\n再见!")
        sys.exit(0)


if __name__ == "__main__":
    main()
