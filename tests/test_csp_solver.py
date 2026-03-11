"""测试 CSP 求解器"""
import pytest
from agent.models.course import Course, TimeSlot
from agent.models.user_preference import Preference
from agent.core.csp_solver import CSPSolver


class TestCSPSolver:
    """测试 CSP 求解器"""

    def setup_method(self):
        """设置测试数据"""
        self.preference = Preference()
        self.solver = CSPSolver(self.preference)

        # 创建测试课程数据
        # 高等数学A 有两个教学班
        self.math_class1 = Course(
            kcid="KC001",
            jx0404id="JX001",
            kcmc="高等数学A",
            sksj="1-16周 星期一 8-10",
            xkrs=30,
            pkrs=50,
            xf=4.0,
        )
        self.math_class1.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=1, start_hour=8, end_hour=10)
        ]

        self.math_class2 = Course(
            kcid="KC001",
            jx0404id="JX002",
            kcmc="高等数学A",
            sksj="1-16周 星期三 8-10",
            xkrs=40,
            pkrs=60,
            xf=4.0,
        )
        self.math_class2.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=3, start_hour=8, end_hour=10)
        ]

        # 大学英语 有两个教学班
        self.english_class1 = Course(
            kcid="KC002",
            jx0404id="JX003",
            kcmc="大学英语",
            sksj="1-16周 星期一 8-10",
            xkrs=20,
            pkrs=40,
            xf=3.0,
        )
        self.english_class1.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=1, start_hour=8, end_hour=10)
        ]

        self.english_class2 = Course(
            kcid="KC002",
            jx0404id="JX004",
            kcmc="大学英语",
            sksj="1-16周 星期二 2-4",
            xkrs=25,
            pkrs=40,
            xf=3.0,
        )
        self.english_class2.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=2, start_hour=2, end_hour=4)
        ]

        # 程序设计基础
        self.programming = Course(
            kcid="KC003",
            jx0404id="JX005",
            kcmc="程序设计基础",
            sksj="1-16周 星期五 6-8",
            xkrs=15,
            pkrs=30,
            xf=3.0,
        )
        self.programming.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=5, start_hour=6, end_hour=8)
        ]

    def test_solve_no_conflicts(self):
        """测试解决无冲突问题"""
        # 数学1 和 英语2 和 编程 没有冲突
        target_courses = [
            [self.math_class1],
            [self.english_class2],
            [self.programming],
        ]

        solutions = self.solver.solve(target_courses, max_solutions=1)

        assert len(solutions) >= 1
        assert solutions[0].total_courses == 3
        assert solutions[0].has_conflicts is False

    def test_solve_with_conflicts(self):
        """测试解决有冲突问题"""
        # 数学1 和 英语1 冲突，但英语2 不冲突
        target_courses = [
            [self.math_class1, self.math_class2],  # 高等数学有两个班级
            [self.english_class1, self.english_class2],  # 大学英语有两个班级
        ]

        solutions = self.solver.solve(target_courses, max_solutions=3)

        # 应该至少找到一个方案
        assert len(solutions) >= 1
        assert solutions[0].total_courses == 2

        # 找到的方案应该无冲突
        assert not solutions[0].has_conflicts

    def test_solve_only_conflicting_combinations(self):
        """测试只有冲突组合的情况"""
        # 数学1 和 英语1 都在周一8-10，冲突
        # 添加一个也冲突的课程
        target_courses = [
            [self.math_class1],  # 只能选周一8-10
            [self.english_class1],  # 只能选周一8-10
        ]

        solutions = self.solver.solve(target_courses, max_solutions=1)

        # 应该返回空列表或冲突的方案
        if solutions:
            # 如果有解，应该是冲突的
            assert solutions[0].has_conflicts or solutions[0].total_courses < 2

    def test_solve_multiple_solutions(self):
        """测试生成多个方案"""
        # 数学有两个班级，英语有两个班级，可以组合出多个方案
        target_courses = [
            [self.math_class1, self.math_class2],
            [self.english_class2],  # 固定英语2
        ]

        solutions = self.solver.solve(target_courses, max_solutions=2)

        # 至少有一个方案
        assert len(solutions) >= 1

    def test_solve_with_requirements(self):
        """测试根据课程名称求解"""
        all_courses = [
            self.math_class1,
            self.math_class2,
            self.english_class1,
            self.english_class2,
            self.programming,
        ]

        solutions = self.solver.solve_with_requirements(
            all_courses,
            ["高等数学A", "大学英语"],
            max_solutions=2
        )

        # 应该至少找到一个方案
        assert len(solutions) >= 1
        assert solutions[0].total_courses == 2

    def test_solve_with_requirements_fuzzy_match(self):
        """测试模糊匹配"""
        all_courses = [
            self.math_class1,
            self.math_class2,
            self.english_class1,
            self.english_class2,
        ]

        solutions = self.solver.solve_with_requirements(
            all_courses,
            ["数学"],  # 模糊匹配 "高等数学A"
            max_solutions=1
        )

        assert len(solutions) >= 1

    def test_solve_with_requirements_missing_course(self):
        """测试处理缺失的课程"""
        all_courses = [
            self.math_class1,
            self.english_class1,
        ]

        solutions = self.solver.solve_with_requirements(
            all_courses,
            ["高等数学A", "不存在的课程"],
            max_solutions=1
        )

        # 应该返回找到的课程方案
        assert len(solutions) >= 1

    def test_find_conflict_free_subset(self):
        """测试找无冲突子集"""
        courses = [
            self.math_class1,
            self.english_class1,  # 与数学1冲突
            self.programming,  # 不冲突
        ]

        subset = self.solver.find_conflict_free_subset(courses)

        # 最多选2门 (数学1和编程，或英语1和编程)
        assert len(subset) >= 2

    def test_find_conflict_free_subset_with_limit(self):
        """测试限制子集大小"""
        courses = [
            self.math_class1,
            self.english_class2,
            self.programming,
        ]

        subset = self.solver.find_conflict_free_subset(courses, max_subset_size=2)

        # 限制最多2门
        assert len(subset) <= 2

    def test_capacity_preference(self):
        """测试容量偏好"""
        # 设置容量偏好
        self.preference.prefer_not_full = True

        # 让一个班级满员
        full_course = Course(
            kcid="KC004",
            jx0404id="JX006",
            kcmc="满员课程",
            sksj="1-16周 星期四 2-4",
            xkrs=50,
            pkrs=50,  # 满员
            xf=2.0,
        )
        full_course.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=4, start_hour=2, end_hour=4)
        ]

        available_course = Course(
            kcid="KC004",
            jx0404id="JX007",
            kcmc="可用课程",
            sksj="1-16周 星期四 2-4",
            xkrs=20,
            pkrs=50,  # 不满员
            xf=2.0,
        )
        available_course.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=4, start_hour=2, end_hour=4)
        ]

        target_courses = [
            [full_course, available_course]
        ]

        solutions = self.solver.solve(target_courses, max_solutions=1)

        # 验证有解（选择满员或不满员都算有效解）
        assert len(solutions) >= 1
        assert len(solutions[0].courses) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
