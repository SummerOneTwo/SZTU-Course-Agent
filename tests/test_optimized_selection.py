"""测试优化选课功能"""
import pytest
from sztu_course_agent.models.course import Course, TimeSlot
from sztu_course_agent.models.user_preference import Preference
from sztu_course_agent.core.csp_solver import CSPSolver


class TestOptimizedSelection:
    """测试优化选课功能"""

    def setup_method(self):
        """设置测试数据"""
        self.preference = Preference()
        self.solver = CSPSolver(self.preference)

        # 创建测试课程数据
        # 高优先级课程 - 高等数学A
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

        # 中优先级课程 - 大学英语
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

        # 低优先级课程 - 程序设计基础
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

        # 体育课 - 不冲突
        self.pe = Course(
            kcid="KC004",
            jx0404id="JX006",
            kcmc="体育",
            sksj="1-16周 星期四 6-8",
            xkrs=30,
            pkrs=50,
            xf=1.0,
        )
        self.pe.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=4, start_hour=6, end_hour=8)
        ]

    def test_basic_priority_selection(self):
        """测试基本优先级选课（高优先级课被选中）"""
        # 高等数学优先级10，大学英语优先级5，编程优先级3
        candidate_courses_by_name = {
            "高等数学A": [self.math_class1, self.math_class2],
            "大学英语": [self.english_class1, self.english_class2],
            "程序设计基础": [self.programming],
            "体育": [self.pe],
        }

        course_priorities = {
            "高等数学A": 10,
            "大学英语": 5,
            "程序设计基础": 3,
            "体育": 1,
        }

        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=course_priorities,
            must_have_courses=[],
            max_solutions=1
        )

        assert len(solutions) >= 1
        solution = solutions[0]

        # 高等数学应该被选中（高优先级，且有时间不冲突的班级）
        math_selected = any(c.kcmc == "高等数学A" for c in solution.courses)
        assert math_selected

        # 如果数学2被选中，英语1和英语2都不应该与之冲突
        selected_math = next((c for c in solution.courses if c.kcmc == "高等数学A"), None)
        if selected_math and selected_math.jx0404id == self.math_class2.jx0404id:
            # 数学2是周三8-10，不与英语1（周一8-10）冲突
            # 英语1应该可以被选中
            english1_selected = any(c.jx0404id == self.english_class1.jx0404id for c in solution.courses)
            english2_selected = any(c.jx0404id == self.english_class2.jx0404id for c in solution.courses)
            assert english1_selected or english2_selected

    def test_must_have_course_constraint(self):
        """测试必选课约束（必选课一定出现在结果中）"""
        candidate_courses_by_name = {
            "高等数学A": [self.math_class1, self.math_class2],
            "大学英语": [self.english_class1, self.english_class2],
            "体育": [self.pe],
        }

        course_priorities = {
            "高等数学A": 5,
            "大学英语": 3,
            "体育": 1,
        }

        # 必选课程
        must_have_courses = ["高等数学A", "大学英语"]

        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=course_priorities,
            must_have_courses=must_have_courses,
            max_solutions=1
        )

        assert len(solutions) >= 1
        solution = solutions[0]

        # 验证必选课程都被选中
        math_selected = any(c.kcmc == "高等数学A" for c in solution.courses)
        english_selected = any(c.kcmc == "大学英语" for c in solution.courses)

        assert math_selected
        assert english_selected

        # 必选课程不应该出现在舍弃列表中
        discarded = solution.metadata.get('discarded_courses', [])
        discarded_names = [item['name'] for item in discarded]
        assert "高等数学A" not in discarded_names
        assert "大学英语" not in discarded_names

    def test_full_conflict_scenario(self):
        """测试全冲突场景的降级舍弃"""
        # 创建一个与数学1冲突的英语课程
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

        # 创建一个也与数学1冲突的编程课程
        programming_conflict = Course(
            kcid="KC003",
            jx0404id="JX008",
            kcmc="程序设计基础",
            sksj="1-16周 星期一 8-10",  # 与数学1冲突
            xkrs=15,
            pkrs=30,
            xf=3.0,
        )
        programming_conflict.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=1, start_hour=8, end_hour=10)
        ]

        candidate_courses_by_name = {
            "高等数学A": [self.math_class1],
            "大学英语": [english_conflict],
            "程序设计基础": [programming_conflict],
            "体育": [self.pe],  # 不与任何课程冲突
        }

        course_priorities = {
            "高等数学A": 10,
            "大学英语": 8,
            "程序设计基础": 6,
            "体育": 1,
        }

        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=course_priorities,
            must_have_courses=[],
            max_solutions=1
        )

        assert len(solutions) >= 1
        solution = solutions[0]

        # 应该选中体育，因为它不冲突
        pe_selected = any(c.jx0404id == self.pe.jx0404id for c in solution.courses)
        assert pe_selected

        # 验证舍弃的课程
        discarded = solution.metadata.get('discarded_courses', [])
        discarded_names = [item['name'] for item in discarded]

        # 由于冲突，一些课程应该被舍弃
        # 至少应该有3个冲突课程中的2个被舍弃
        assert len(discarded) >= 2

    def test_multi_solution_comparison(self):
        """测试多方案比较"""
        candidate_courses_by_name = {
            "高等数学A": [self.math_class1, self.math_class2],
            "大学英语": [self.english_class2],
            "程序设计基础": [self.programming],
        }

        course_priorities = {
            "高等数学A": 10,
            "大学英语": 8,
            "程序设计基础": 6,
        }

        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=course_priorities,
            must_have_courses=[],
            max_solutions=1
        )

        # 虽然只请求1.个解，但应该返回一个有效的解
        assert len(solutions) >= 1
        solution = solutions[0]

        # 验证方案无冲突
        assert not solution.has_conflicts

        # 验证至少选中了高优先级课程
        high_priority_selected = any(
            c.kcmc in ["高等数学A", "大学英语"]
            for c in solution.courses
        )
        assert high_priority_selected

    def test_empty_candidates(self):
        """测试空候选列表"""
        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name={},
            course_priorities={},
            must_have_courses=[],
            max_solutions=1
        )

        assert len(solutions) == 0

    def test_must_have_not_in_candidates(self):
        """测试必选课程不在候选列表中"""
        # 虽然数学不在候选列表中，但在必选列表中
        candidate_courses_by_name = {
            "大学英语": [self.english_class1, self.english_class2],
            "体育": [self.pe],
        }

        course_priorities = {
            "大学英语": 8,
            "体育": 1,
        }

        # 数学在必选列表但不在候选列表中
        # 这种情况下，求解器会继续处理可用课程
        # 因为必选课程不在候选中，约束相当于空约束
        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=course_priorities,
            must_have_courses=["高等数学A"],  # 不在候选中
            max_solutions=1
        )

        # 应该有解，但不包含必选课程（因为它不在候选中）
        assert len(solutions) >= 1
        solution = solutions[0]

        # 验证必选课程不在解中
        math_in_solution = any(c.kcmc == "高等数学A" for c in solution.courses)
        assert not math_in_solution

    def test_priority_without_conflicts(self):
        """测试无冲突情况下的优先级选择"""
        candidate_courses_by_name = {
            "高等数学A": [self.math_class2],  # 周三
            "大学英语": [self.english_class2],  # 周二
            "程序设计基础": [self.programming],  # 周五
            "体育": [self.pe],  # 周四
        }

        course_priorities = {
            "高等数学A": 10,
            "大学英语": 8,
            "程序设计基础": 6,
            "体育": 1,
        }

        solutions = self.solver.solve_optimized_selection(
            candidate_courses_by_name=candidate_courses_by_name,
            course_priorities=course_priorities,
            must_have_courses=[],
            max_solutions=1
        )

        assert len(solutions) >= 1
        solution = solutions[0]

        # 由于所有课程都不冲突，应该都能选中
        assert len(solution.courses) == 4

        # 验证所有课程都被选中
        course_names = {c.kcmc for c in solution.courses}
        assert course_names == {"高等数学A", "大学英语", "程序设计基础", "体育"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
