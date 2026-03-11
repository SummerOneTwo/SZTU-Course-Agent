"""课表构建与可视化"""
from typing import List, Optional
from ..models.course import Course
from ..models.schedule import Schedule
from ..core.conflict_detector import ConflictDetector


class ScheduleBuilder:
    """课表构建器"""

    def __init__(self):
        self.detector = ConflictDetector()

    def build_schedule(self, courses: List[Course]) -> Schedule:
        """构建课表

        Args:
            courses: 课程列表

        Returns:
            Schedule 对象
        """
        schedule = Schedule()
        for course in courses:
            schedule.add_course(course)
        return schedule

    def render_schedule(self, courses: List[Course], title: str = "课表") -> str:
        """渲染课表为 ASCII 表格

        Args:
            courses: 课程列表
            title: 课表标题

        Returns:
            ASCII 表格字符串
        """
        schedule = Schedule(title)
        for course in courses:
            schedule.add_course(course)
        return schedule.render_ascii()

    def render_markdown(self, courses: List[Course], title: str = "课表") -> str:
        """渲染课表为 Markdown 表格

        Args:
            courses: 课程列表
            title: 课表标题

        Returns:
            Markdown 表格字符串
        """
        day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        lines = [f"# {title}\n"]
        lines.append("| 节次 | " + " | ".join(day_names[1:]) + " |")
        lines.append("|------|" + "|".join(["--------"] * 7) + "|")

        schedule = Schedule()
        for course in courses:
            schedule.add_course(course)

        for slot in range(1, 13):
            time_str = f"{Schedule.TIME_SLOTS[slot][0]}-{Schedule.TIME_SLOTS[slot][1]}"
            row = [f"{slot}节 ({time_str})"]

            for day in range(1, 8):
                courses_at = schedule.get_courses_at(day, slot)
                if not courses_at:
                    row.append("")
                elif len(courses_at) > 1:
                    row.append("⚠️ " + ", ".join(c.kcmc[:4] for c in courses_at))
                else:
                    course = courses_at[0]
                    row.append(course.kcmc)

            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def render_conflict_report(self, courses: List[Course]) -> str:
        """渲染冲突报告

        Args:
            courses: 课程列表

        Returns:
            冲突报告字符串
        """
        conflicts = self.detector.find_conflicts(courses)

        if not conflicts:
            return "✅ 无冲突!"

        lines = [f"⚠️ 发现 {len(conflicts)} 个冲突:\n"]

        for i, conflict in enumerate(conflicts, 1):
            lines.append(f"{i}. {conflict.course1.kcmc} 与 {conflict.course2.kcmc}")
            lines.append(f"   时间: {conflict.course1.sksj} vs {conflict.course2.sksj}")

            # 查找替代方案
            alternatives = []
            # (这里可以扩展查找替代逻辑)

            lines.append("")

        return "\n".join(lines)

    def render_course_list(self, courses: List[Course], show_details: bool = False) -> str:
        """渲染课程列表

        Args:
            courses: 课程列表
            show_details: 是否显示详细信息

        Returns:
            格式化字符串
        """
        lines = []

        for i, course in enumerate(courses, 1):
            basic = f"{i}. {course.kcmc} ({course.skls}) - {course.xkrs}/{course.pkrs}"
            lines.append(basic)

            if show_details:
                lines.append(f"   教学班ID: {course.jx0404id}")
                lines.append(f"   时间: {course.sksj}")
                lines.append(f"   性质: {course.kcxzmc} {course.kcsxmc}")
                lines.append("")

        return "\n".join(lines)
