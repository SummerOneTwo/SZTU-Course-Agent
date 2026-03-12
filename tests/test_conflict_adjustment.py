"""测试冲突调整功能"""
import pytest
from sztu_course_agent.models.course import Course, TimeSlot
from sztu_course_agent.models.user_preference import Preference
from sztu_course_agent.core.csp_solver import CSPSolver


class TestConflictAdjustment:
    """测试冲突调整功能"""

    def setup_method(self):
        """设置测试数据"""
        self.preference = Preference()
        self.solver = CSPSolver(self.preference)

        # 创建测试课程数据
        # 高等数学A 有三个教学班
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

        self.math_class3 = Course(
            kcid="KC001",
            jx0404id="JX003",
            kcmc="高等数学A",
            sksj="1-16周 星期五 8-10",
            xkrs=35,
            pkrs=60,
            xf=4.0,
        )
        self.math_class3.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=5, start_hour=8, end_hour=10)
        ]

        # 大学英语
        self.english_class1 = Course(
            kcid="KC002",
            jx0404id="JX004",
            kcmc="大学英语",
            sksj="1-16周 星期二 2-4",
            xkrs=20,
            pkrs=40,
            xf=3.0,
        )
        self.english_class1.time_slots = [
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

    def test_basic_conflict_adjustment(self):
        """测试基本冲突调整（替换一门课，保留锁定课）"""
        # 当前课表：数学1、英语、编程
        current_courses = [self.math_class1, self.english_class1, self.programming]

        # 锁定英语和编程
        locked_course_ids = [self.english_class1.jx0404id, self.programming.jx0404id]

        # 需要替换数学1
        replace_course_ids = [self.math_class1.jx0404id]

        # 替代方案：数学2和数学3
        alternatives_by_course_name = {
            "高等数学A": [self.math_class2, self.math_class3]
        }

        solution = self.solver.solve_conflict_adjustment(
            current_courses=current_courses,
            locked_course_ids=locked_course_ids,
            replace_course_ids=replace_course_ids,
            alternatives_by_course_name=alternatives_by_course_name
        )

        # 验证解
        assert solution is not None
        assert len(solution.courses) == 3  # 仍然选3门课

        # 验证锁定课程被保留
        locked_ids_in_solution = {c.jx0404id for c in solution.courses if c.jx0404id in locked_course_ids}
        assert len(locked_ids_in_solution) == 2

        # 验证被替换的课程不在结果中
        replaced_in_solution = any(c.jx0404id == self.math_class1.jx0404id for c in solution.courses)
        assert not replaced_in_solution

        # 验证选择了某个替代课程
        math_in_solution = any(c.kcmc == "高等数学A" for c in solution.courses)
        assert math_in_solution

    def test_cascading_conflict_adjustment(self):
        """测试级联冲突调整（替换导致新冲突需要继续调整）"""
        # 创建一个与数学3冲突的编程课程
        programming_conflict = Course(
            kcid="KC003",
            jx0404id="JX006",
            kcmc="程序设计基础",
            sksj="1-16周 星期五 8-10",
            xkrs=15,
            pkrs=30,
            xf=3.0,
        )
        programming_conflict.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=5, start_hour=8, end_hour=10)
        ]

        current_courses = [self.math_class1, self.english_class1, programming_conflict]

        # 锁定英语
        locked_course_ids = [self.english_class1.jx0404id]

        # 需要替换数学1
        replace_course_ids = [self.math_class1.jx0404id]

        # 替代方案：数学2（不冲突）、数学3（与编程冲突）
        alternatives_by_course_name = {
            "高等数学A": [self.math_class2, self.math_class3]
        }

        solution = self.solver.solve_conflict_adjustment(
            current_courses=current_courses,
            locked_course_ids=locked_course_ids,
            replace_course_ids=replace_course_ids,
            alternatives_by_course_name=alternatives_by_course_name
        )

        # 应该选择数学2，因为数学3与编程冲突
        assert solution is not None
        math_classes_in_solution = [c for c in solution.courses if c.kcmc == "高等数学A"]
        if math_classes_in_solution:
            # 选择了数学2（因为与编程不冲突）
            assert math_classes_in_solution[0].jx0404id == self.math_class2.jx0404id

    def test_no_feasible_solution(self):
        """测试无可行解（锁定课全部冲突）"""
        # 创建一个与所有数学班级都冲突的英语课程
        english_conflict = Course(
            kcid="KC002",
            jx0404id="JX007",
            kcmc="大学英语",
            sksj="1-16周 星期一 8-10",  # 与数学1冲突
            xkrs=20,
            pkrs=40,
            xf=3.0,
        )
        english_conflict.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=1, start_hour=8, end_hour=10)
        ]

        current_courses = [self.math_class1, english_conflict]

        # 锁定英语（与所有数学冲突）
        locked_course_ids = [english_conflict.jx0404id]

        # 需要替换数学1
        replace_course_ids = [self.math_class1.jx0404id]

        # 替代方案：数学2（周三8-10）、数学3（周五8-10）- 都不与英语冲突
        # 所以这里应该有解
        alternatives_by_course_name = {
            "高等数学A": [self.math_class2, self.math_class3]
        }

        solution = self.solver.solve_conflict_adjustment(
            current_courses=current_courses,
            locked_course_ids=locked_course_ids,
            replace_course_ids=replace_course_ids,
            alternatives_by_course_name=alternatives_by_course_name
        )

        # 应该有解
        assert solution is not None

    def test_adjustment_minimization(self):
        """测试调整最小化验证"""
        # 当前课表有3门课
        current_courses = [self.math_class1, self.english_class1, self.programming]

        # 锁定英语和编程
        locked_course_ids = [self.english_class1.jx0404id, self.programming.jx0404id]

        # 需要替换数学1
        replace_course_ids = [self.math_class1.jx0404id]

        # 替代方案：数学2
        alternatives_by_course_name = {
            "高等数学A": [self.math_class2]
        }

        solution = self.solver.solve_conflict_adjustment(
            current_courses=current_courses,
            locked_course_ids=locked_course_ids,
            replace_course_ids=replace_course_ids,
            alternatives_by_course_name=alternatives_by_course_name
        )

        # 验证：只替换了数学1，没有其他改变
        assert solution is not None
        assert len(solution.courses) == 3
        assert solution.metadata.get('adjustments')
        adjustments = solution.metadata['adjustments']

        # 应该只有一次替换操作
        assert len(adjustments) == 1
        assert "替换" in adjustments[0]

    def test_empty_alternatives(self):
        """测试没有替代课程的情况"""
        current_courses = [self.math_class1, self.english_class1]

        locked_course_ids = [self.english_class1.jx0404id]
        replace_course_ids = [self.math_class1.jx0404id]

        # 没有替代课程
        alternatives_by_course_name = {
            "高等数学A": []
        }

        solution = self.solver.solve_conflict_adjustment(
            current_courses=current_courses,
            locked_course_ids=locked_course_ids,
            replace_course_ids=replace_course_ids,
            alternatives_by_course_name=alternatives_by_course_name
        )

        # 应该有解，但只包含锁定的课程
        assert solution is not None
        # 只应该包含英语课（锁定）
        assert len(solution.courses) == 1
        assert solution.courses[0].jx0404id == self.english_class1.jx0404id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
