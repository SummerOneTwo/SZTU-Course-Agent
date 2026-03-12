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

    def analyze_adjustment_impact(
        self,
        courses_to_remove: List[str],
        current_courses: List[Course]
    ) -> Dict[str, List[str]]:
        """分析移除/替换一门课后对整体课表的影响

        Args:
            courses_to_remove: 要移除/替换的教学班ID列表
            current_courses: 当前课表中的课程

        Returns:
            影响分析字典，包含:
            - 'removed': 被移除的课程信息
            - 'remaining': 保留的课程信息
            - 'conflicts_resolved': 解决的冲突
            - 'new_conflicts': 可能产生的新冲突（如果有）
        """
        remove_set = set(courses_to_remove)
        remaining_courses = [c for c in current_courses if c.jx0404id not in remove_set]
        removed_courses = [c for c in current_courses if c.jx0404id in remove_set]

        # 检查当前所有冲突
        original_conflicts = self.find_conflicts(current_courses)
        original_conflict_pairs = {(c1.jx0404id, c2.jx0404id) for c1, c2 in [(conf.course1, conf.course2) for conf in original_conflicts]}

        # 检查移除后的冲突
        remaining_conflicts = self.find_conflicts(remaining_courses)
        remaining_conflict_pairs = {frozenset([conf.course1.jx0404id, conf.course2.jx0404id]) for conf in remaining_conflicts}

        # 找出解决的冲突
        conflicts_resolved = []
        for c1_id, c2_id in original_conflict_pairs:
            if c1_id in remove_set or c2_id in remove_set:
                if frozenset([c1_id, c2_id]) not in remaining_conflict_pairs:
                    c1 = next((c for c in removed_courses if c.jx0404id == c1_id), None)
                    c2 = next((c for c in current_courses if c.jx0404id == c2_id), None)
                    if c1 and c2:
                        conflicts_resolved.append(f"{c1.kcmc} 与 {c2.kcmc}")

        return {
            'removed': [f"{c.kcmc} ({c.jx0404id})" for c in removed_courses],
            'remaining': [f"{c.kcmc} ({c.jx0404id})" for c in remaining_courses],
            'conflicts_resolved': conflicts_resolved,
            'remaining_conflicts': [str(conf) for conf in remaining_conflicts]
        }

    def find_alternatives_for_course(
        self,
        course: Course,
        other_courses: List[Course],
        all_courses_by_name: Dict[str, List[Course]],
        cross_course_search: bool = False
    ) -> List[Course]:
        """为冲突课程找到不冲突的替代方案

        Args:
            course: 冲突的课程
            other_courses: 已选的其他课程
            all_courses_by_name: 所有课程的按名称索引
            cross_course_search: 是否进行跨课程名搜索（寻找同类型/同学分的替代）

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

        # 如果需要跨课程搜索且同名课程替代不够
        if cross_course_search and len(alternatives) < 5:
            all_courses = []
            for courses_list in all_courses_by_name.values():
                all_courses.extend(courses_list)

            # 查找同学分或相似名称的课程
            for alt_course in all_courses:
                if alt_course.jx0404id == course.jx0404id:
                    continue
                if alt_course.kcmc == course.kcmc:
                    continue  # 已经查找过

                # 同学分匹配
                if abs(alt_course.xf - course.xf) < 0.1:
                    # 检查是否与已选课程冲突
                    has_conflict = False
                    for other in other_courses:
                        if self.courses_conflict(alt_course, other):
                            has_conflict = True
                            break
                    if not has_conflict:
                        # 标记为跨课程替代
                        if not hasattr(alt_course, '_metadata'):
                            alt_course._metadata = {}
                        alt_course._metadata.update({'cross_course': True, 'original_name': course.kcmc})
                        alternatives.append(alt_course)

        # 按容量排序
        alternatives.sort(key=lambda c: c.remaining_capacity, reverse=True)

        return alternatives
