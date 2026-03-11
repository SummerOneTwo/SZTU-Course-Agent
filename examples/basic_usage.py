"""
基本使用示例

演示如何使用 SZTU Course Agent 进行课程冲突检测和方案生成
"""
import json
from rich.console import Console
from rich.table import Table

# 注意：实际使用时先安装: pip install -e .
from sztu_course_agent import (
    CourseLoader,
    CSPSolver,
    Preference,
    SolutionExporter,
    ScheduleBuilder,
)


def main():
    console = Console()

    # 1. 加载课程数据
    console.print("\n[bold cyan]1. 加载课程数据[/bold cyan]")
    loader = CourseLoader.from_file("examples/example_courses.json")

    if not loader._courses:
        console.print("[red]❌ 未加载到课程数据[/red]")
        return

    console.print(f"[green]✓[/green] 已加载 {len(loader._courses)} 门课程")

    # 2. 显示所有课程
    console.print("\n[bold cyan]2. 可选课程列表[/bold cyan]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("课程名称")
    table.add_column("教师")
    table.add_column("学分")
    table.add_column("时间")

    unique_courses = {}
    for course in loader._courses:
        if course.kcmc not in unique_courses:
            unique_courses[course.kcmc] = course

    for course in unique_courses.values():
        table.add_row(
            course.kcmc,
            course.skls,
            str(course.xf),
            course.sksj.strip()
        )

    console.print(table)

    # 3. 创建用户偏好
    console.print("\n[bold cyan]3. 创建用户偏好[/bold cyan]")
    preference = Preference(
        target_courses=["高等数学A", "大学英语", "程序设计基础", "线性代数"],
        min_credits=10.0,
        max_credits=15.0,
        prefer_not_full=True,
    )
    console.print(f"[green]✓[/green] 目标课程: {preference.target_courses}")
    console.print(f"[green]✓[/green] 学分范围: {preference.min_credits}-{preference.max_credits}")

    # 4. 创建求解器并生成方案
    console.print("\n[bold cyan]4. 生成选课方案[/bold cyan]")
    solver = CSPSolver(preference)

    solutions = solver.solve_with_requirements(
        loader.get_all_courses(),
        preference.target_courses,
        max_solutions=3
    )

    if not solutions:
        console.print("[red]❌ 无法生成无冲突方案[/red]")
        console.print("可能原因: 课程之间全部冲突或找不到匹配的课程")
        return

    # 5. 显示生成的方案
    console.print(f"\n[green]✓[/green] 生成了 {len(solutions)} 个方案:\n")

    for i, solution in enumerate(solutions, 1):
        console.print(f"[bold]方案 {i}[/bold] - 评分: {solution.score:.1f}/100")
        console.print(f"课程数: {solution.total_courses} | 学分: {solution.total_credits:.1f}")

        if solution.has_conflicts:
            console.print(f"[red]⚠️ {len(solution.conflicts)} 个冲突[/red]")
        else:
            console.print("[green]✓ 无冲突[/green]")

        console.print("\n课程列表:")
        for j, course in enumerate(solution.courses, 1):
            console.print(f"  {j}. [cyan]{course.kcmc}[/cyan] ({course.skls})")
            console.print(f"     时间: {course.sksj.strip()} | ID: {course.jx0404id}")
        console.print()

    # 6. 导出配置
    console.print("[bold cyan]5. 导出配置文件[/bold cyan]")
    exporter = SolutionExporter()
    exporter.export_to_toml(solutions[0], "examples/output_config.toml")
    console.print("[green]✓[/green] 已导出到 examples/output_config.toml")

    # 7. 显示课表
    console.print("\n[bold cyan]6. 显示课表[/bold cyan]")
    builder = ScheduleBuilder()
    console.print(builder.render_schedule(solutions[0].courses, "选课方案课表"))


if __name__ == "__main__":
    main()
