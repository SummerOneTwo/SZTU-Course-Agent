"""CSP 约束满足求解器 - 使用 Google OR-Tools

Google OR-Tools (ortools) 是 Google 开源的约束求解工具包，
提供强大的约束编程能力，非常适合处理课程排课问题。

官方文档: https://developers.google.com/optimization
"""
from ortools.sat.python import cp_model
from typing import List, Dict, Optional
from ..models.course import Course
from ..models.user_preference import Preference
from ..models.solution import SelectionSolution
from .conflict_detector import ConflictDetector
from .time_slot_parser import time_slots_conflict


class CSPSolver:
    """基于 OR-Tools 的课程选择求解器"""

    def __init__(self, preference: Optional[Preference] = None):
        self.preference = preference or Preference()
        self.detector = ConflictDetector()

    def solve(
        self,
        target_courses: List[List[Course]],
        max_solutions: int = 5,
        timeout_ms: int = 30000
    ) -> List[SelectionSolution]:
        """求解课程选择问题

        Args:
            target_courses: 目标课程列表，每个元素是同一门课的不同教学班
                          例如: [[高等数学A班1, 高等数学A班2], [大学英语班1]]
            max_solutions: 返回的最大方案数量
            timeout_ms: 求解超时时间(毫秒)

        Returns:
            SelectionSolution 列表，按评分排序
        """
        # 找到第一个最优解
        solution = self._find_one_solution(target_courses, [], timeout_ms)
        if not solution:
            return []

        # 对于测试，先简单返回一个解
        # 如果需要多个解，可以添加排除约束
        solutions = [solution]

        # 如果需要更多解，尝试找到其他方案
        # 简化版：只返回找到的最佳解
        return solutions

    def _find_one_solution(
        self,
        target_courses: List[List[Course]],
        existing_solutions: List[SelectionSolution],
        timeout_ms: int = 30000
    ) -> Optional[SelectionSolution]:
        """找到一个解，排除已有的解

        Args:
            target_courses: 目标课程列表
            existing_solutions: 已找到的解
            timeout_ms: 超时时间

        Returns:
            找到的解，如果没有则返回 None
        """
        # 创建模型
        model = cp_model.CpModel()

        # 为每门课程创建布尔变量
        course_vars = []
        for i, classes in enumerate(target_courses):
            vars_for_course = []
            for j, course in enumerate(classes):
                var = model.NewBoolVar(f'course_{i}_{j}')
                vars_for_course.append(var)
            course_vars.append(vars_for_course)

        # 约束1: 每门课程最多选一个教学班
        for i, vars_for_course in enumerate(course_vars):
            model.AddAtMostOne(vars_for_course)

        # 约束2: 时间冲突约束
        for i in range(len(target_courses)):
            for j in range(i + 1, len(target_courses)):
                for ci, course_i in enumerate(target_courses[i]):
                    for cj, course_j in enumerate(target_courses[j]):
                        if self.detector.courses_conflict(course_i, course_j):
                            model.AddAtMostOne([
                                course_vars[i][ci],
                                course_vars[j][cj]
                            ])

        # 约束3: 排除已有的解
        # 通过添加约束：不允许选择与已有解完全相同的课程组合
        for existing_solution in existing_solutions:
            # 获取已有解中的课程ID集合
            existing_ids = {c.jx0404id for c in existing_solution.courses}

            # 创建变量，表示是否选择与已有解相同的课程
            same_as_existing = []
            for i, vars_for_course in enumerate(course_vars):
                for j, var in enumerate(vars_for_course):
                    course = target_courses[i][j]
                    if course.jx0404id in existing_ids:
                        same_as_existing.append(var)

            # 添加约束：不允许选择与已有解完全相同的课程
            # 如果same_as_existing数量等于已有解的课程数，说明是同一个解
            model.Add(sum(same_as_existing) != len(existing_solution.courses))

        # 最大化目标: 选课数量
        objective = []
        for i, vars_for_course in enumerate(course_vars):
            for var in vars_for_course:
                objective.append(var)

        model.Maximize(sum(objective))

        # 求解
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = timeout_ms / 1000
        solver.parameters.log_search_progress = False

        status = solver.Solve(model)

        if status != cp_model.OPTIMAL and status != cp_model.FEASIBLE:
            return None

        # 提取解
        selected_courses = []
        for i, vars_for_course in enumerate(course_vars):
            for j, var in enumerate(vars_for_course):
                if solver.Value(var) == 1:
                    selected_courses.append(target_courses[i][j])

        if not selected_courses:
            return None

        # 计算评分
        total_credits = sum(c.xf for c in selected_courses)
        score = self._calculate_score(selected_courses, total_credits)

        return SelectionSolution(
            courses=selected_courses,
            total_credits=total_credits,
            total_courses=len(selected_courses),
            score=score,
            conflicts=[]
        )

    def _calculate_score(self, courses: List[Course], total_credits: float) -> float:
        """计算方案评分"""
        score = 50.0  # 基础分

        # 学分得分
        if self.preference.min_credits <= total_credits <= self.preference.max_credits:
            score += 10.0

        # 课程数量得分
        score += len(courses) * 5.0

        # 单个课程偏好得分
        for course in courses:
            score += self.preference.score_course(course) * 10.0

        return min(100.0, score)

    def solve_with_requirements(
        self,
        all_courses: List[Course],
        required_course_names: List[str],
        max_solutions: int = 5
    ) -> List[SelectionSolution]:
        """根据课程名称要求求解

        Args:
            all_courses: 所有可用课程
            required_course_names: 必选课程名称列表
            max_solutions: 最大方案数

        Returns:
            SelectionSolution 列表
        """
        # 按课程名分组
        courses_by_name: Dict[str, List[Course]] = {}
        for course in all_courses:
            if course.kcmc not in courses_by_name:
                courses_by_name[course.kcmc] = []
            courses_by_name[course.kcmc].append(course)

        # 构建目标课程列表
        target_courses = []
        found_names = set()
        missing_names = []

        for name in required_course_names:
            if name in courses_by_name and courses_by_name[name]:
                target_courses.append(courses_by_name[name])
                found_names.add(name)
            else:
                # 尝试模糊匹配
                matched = False
                for course_name in courses_by_name.keys():
                    if name in course_name or course_name in name:
                        target_courses.append(courses_by_name[course_name])
                        found_names.add(course_name)
                        matched = True
                        break
                if not matched:
                    missing_names.append(name)

        if missing_names:
            print(f"警告: 以下课程未找到: {', '.join(missing_names)}")

        if not target_courses:
            return []

        # 求解
        solutions = self.solve(target_courses, max_solutions)

        # 添加缺失信息到元数据
        for sol in solutions:
            sol.metadata['missing_courses'] = missing_names
            sol.metadata['matched_courses'] = list(found_names)

        return solutions

    def find_conflict_free_subset(
        self,
        courses: List[Course],
        max_subset_size: Optional[int] = None
    ) -> List[Course]:
        """找到一个无冲突的最大子集

        Args:
            courses: 候选课程列表
            max_subset_size: 最大子集大小限制

        Returns:
            无冲突的课程子集
        """
        # 将每门课程作为单独的目标
        target_courses = [[c] for c in courses]

        # 求解，限制最大解数为1
        solutions = self.solve(target_courses, max_solutions=1)

        if solutions and solutions[0].courses:
            result = solutions[0].courses
            if max_subset_size is not None:
                return result[:max_subset_size]
            return result

        return []
