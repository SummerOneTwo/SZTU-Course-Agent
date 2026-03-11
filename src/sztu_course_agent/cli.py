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

from .tools.course_loader import CourseLoader
from .core.csp_solver import CSPSolver
from .models.user_preference import Preference
from .tools.schedule_builder import ScheduleBuilder
from .tools.solution_exporter import SolutionExporter


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

    def run(self):
        """运行 CLI"""
        self.welcome()

        while True:
            self.console.print("\n[bold]主菜单:[/bold]")
            self.console.print("  1. 搜索课程")
            self.console.print("  2. 检测课程冲突")
            self.console.print("  3. 生成选课方案")
            self.console.print("  4. 显示课表")
            self.console.print("  5. 退出")

            choice = Prompt.ask("\n请选择", choices=["1", "2", "3", "4", "5"], default="1")

            if choice == "1":
                self.search_courses()
            elif choice == "2":
                self.detect_conflicts()
            elif choice == "3":
                self.generate_solutions()
            elif choice == "4":
                self.show_schedule()
            elif choice == "5":
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
