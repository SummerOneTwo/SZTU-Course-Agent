"""冲突检测引擎"""
from typing import List, Set, Tuple, Dict
from ..models.course import Course
from ..models.schedule import Schedule, ConflictInfo
from ..models.solution import SelectionSolution
from .time_slot_parser import time_slots_conflict


class ConflictDetector:
    """冲突检测器"""

    def __init__(self):
        self._conflict_cache: Dict[Tuple[str, str], bool] = {}

    def courses_conflict(self, course1: Course, course2: Course) -> bool:
        """检测两门课程是否冲突

        Args:
            course1: 课程1
            course2: 课程2

        Returns:
            是否冲突
        """
        if course1.jx0404id == course2.jx0404id:
            return False  # 同一教学班不算冲突

        # 使用缓存
        cache_key = (
            tuple(sorted([course1.jx0404id, course2.jx0404id]))
        )
        if cache_key in self._conflict_cache:
            return self._conflict_cache[cache_key]

        # 检测时间冲突
        has_conflict = False
        for slot1 in course1.time_slots:
            for slot2 in course2.time_slots:
                if time_slots_conflict(slot1, slot2):
                    has_conflict = True
                    break
            if has_conflict:
                break

        self._conflict_cache[cache_key] = has_conflict
        return has_conflict

    def find_conflicts(self, courses: List[Course]) -> List[ConflictInfo]:
        """找出所有冲突

        Args:
            courses: 课程列表

        Returns:
            冲突信息列表
        """
        conflicts = []
        day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 先解析所有课程的时间槽
        for course in courses:
            if not course.time_slots:
                continue

        n = len(courses)
        for i in range(n):
            for j in range(i + 1, n):
                if self.courses_conflict(courses[i], courses[j]):
                    # 找出具体的冲突时间
                    conflict_details = []
                    for slot1 in courses[i].time_slots:
                        for slot2 in courses[j].time_slots:
                            if time_slots_conflict(slot1, slot2):
                                conflict_details.append(
                                    f"{day_names[slot1.day]} {slot1.start_hour}-{slot1.end_hour}节"
                                )

                    conflicts.append(ConflictInfo(
                        course1=courses[i],
                        course2=courses[j],
                        conflict_type="time",
                        day=0,  # 具体冲突时间可能多个，这里设为0
                        slot=0,
                        description=f"时间冲突: {', '.join(conflict_details)}"
                    ))

        return conflicts

    def check_solution(self, solution: SelectionSolution) -> bool:
        """检查方案是否有冲突

        Args:
            solution: 选课方案

        Returns:
            True 表示无冲突
        """
        conflicts = self.find_conflicts(solution.courses)
        solution.conflicts = [str(c) for c in conflicts]
        return len(conflicts) == 0

    def find_alternatives_for_course(
        self,
        course: Course,
        other_courses: List[Course],
        all_courses_by_name: Dict[str, List[Course]]
    ) -> List[Course]:
        """为冲突课程找到不冲突的替代方案

        Args:
            course: 冲突的课程
            other_courses: 已选的其他课程
            all_courses_by_name: 所有课程的按名称索引

        Returns:
            可用的替代课程列表
        """
        alternatives = []

        # 查找同名课程的其他教学班
        same_name_courses = all_courses_by_name.get(course.kcmc, [])

        for alt_course in same_name_courses:
            if alt_course.jx0404id == course.jx0404id:
                continue  # 跳过自己

            # 检查是否与已选课程冲突
            has_conflict = False
            for other in other_courses:
                if self.courses_conflict(alt_course, other):
                    has_conflict = True
                    break

            if not has_conflict:
                alternatives.append(alt_course)

        # 按容量排序
        alternatives.sort(key=lambda c: c.remaining_capacity, reverse=True)

        return alternatives

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
