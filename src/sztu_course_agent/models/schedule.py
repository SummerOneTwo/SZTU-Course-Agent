from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set
from .course import Course, TimeSlot


class Schedule:
    """课表模型 - 表示一周的排课情况"""

    # 节次到小时段的映射
    TIME_SLOTS = {
        1: ("08:00", "08:45"),
        2: ("08:55", "09:40"),
        3: ("09:50", "10:35"),
        4: ("10:45", "11:30"),
        5: ("11:40", "12:25"),
        6: ("14:00", "14:45"),
        7: ("14:55", "15:40"),
        8: ("15:50", "16:35"),
        9: ("16:45", "17:30"),
        10: ("17:40", "18:25"),
        11: ("18:30", "19:15"),
        12: ("19:25", "20:10"),
        13: ("20:20", "21:05"),
    }

    def __init__(self, name: str = ""):
        self.name = name
        # 7天 x 12节次的二维表
        self._schedule: Dict[int, Dict[int, List[Course]]] = {
            day: {slot: [] for slot in range(1, 13)} for day in range(1, 8)
        }

    def add_course(self, course: Course) -> None:
        """添加课程到课表"""
        for time_slot in course.time_slots:
            for slot in range(time_slot.start_hour, time_slot.end_hour + 1):
                self._schedule[time_slot.day][slot].append(course)

    def get_courses_at(self, day: int, slot: int) -> List[Course]:
        """获取指定时间的课程"""
        if day < 1 or day > 7 or slot < 1 or slot > 12:
            return []
        return self._schedule[day][slot]

    def is_conflict_at(self, day: int, slot: int) -> bool:
        """检查指定时间是否有冲突"""
        return len(self._schedule[day][slot]) > 1

    def get_conflict_times(self) -> List[tuple]:
        """获取所有冲突的时间点"""
        conflicts = []
        for day in range(1, 8):
            for slot in range(1, 13):
                if self.is_conflict_at(day, slot):
                    conflicts.append((day, slot))
        return conflicts

    def render_ascii(self) -> str:
        """渲染ASCII课表"""
        day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        lines = []
        lines.append(f"\n{'=' * 80}")
        lines.append(f"课表: {self.name}".center(80))
        lines.append(f"{'=' * 80}\n")

        # 表头
        header = "节次  | " + " | ".join(f"{day:^16}" for day in day_names[1:])
        lines.append(header)
        lines.append("-" * len(header))

        # 表体
        for slot in range(1, 13):
            time_str = f"{self.TIME_SLOTS[slot][0]}-{self.TIME_SLOTS[slot][1]}"
            row = f"{slot:2d}节   | {time_str:^16} |"

            for day in range(1, 8):
                courses = self.get_courses_at(day, slot)
                if not courses:
                    cell = " " * 16
                elif len(courses) > 1:
                    # 冲突
                    conflict_names = ", ".join(c.kcmc[:4] for c in courses)
                    cell = f"⚠️{conflict_names[:13]}"
                else:
                    course = courses[0]
                    cell = course.kcmc[:14].ljust(14)
                row += f" {cell} |"
            lines.append(row)

        lines.append("-" * len(header))
        return "\n".join(lines)


class ConflictInfo(BaseModel):
    """冲突信息模型"""
    course1: Course = Field(description="冲突课程1")
    course2: Course = Field(description="冲突课程2")
    conflict_type: str = Field(description="冲突类型: time/teacher")
    day: int = Field(description="冲突星期")
    slot: int = Field(description="冲突节次")
    description: str = Field(description="冲突描述")

    def __str__(self) -> str:
        day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return (
            f"[{self.conflict_type}] {self.course1.kcmc} 与 {self.course2.kcmc} "
            f"冲突于 {day_names[self.day]} {self.slot}节: {self.description}"
        )
