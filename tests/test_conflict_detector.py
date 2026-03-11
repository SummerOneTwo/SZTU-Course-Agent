"""测试冲突检测引擎"""
import pytest
from agent.models.course import Course, TimeSlot
from agent.core.conflict_detector import ConflictDetector
from agent.models.solution import SelectionSolution


class TestConflictDetector:
    """测试冲突检测器"""

    def setup_method(self):
        """设置测试数据"""
        self.detector = ConflictDetector()

        # 创建测试课程
        self.course1 = Course(
            kcid="KC001",
            jx0404id="JX001",
            kcmc="高等数学A",
            sksj="1-16周 星期一 8-10",
            xkrs=30,
            pkrs=50,
        )
        self.course1.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=1, start_hour=8, end_hour=10)
        ]

        self.course2 = Course(
            kcid="KC002",
            jx0404id="JX002",
            kcmc="大学英语",
            sksj="1-16周 星期一 8-10",
            xkrs=40,
            pkrs=60,
        )
        self.course2.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=1, start_hour=8, end_hour=10)
        ]

        self.course3 = Course(
            kcid="KC003",
            jx0404id="JX003",
            kcmc="程序设计基础",
            sksj="1-16周 星期二 2-4",
            xkrs=20,
            pkrs=40,
        )
        self.course3.time_slots = [
            TimeSlot(weeks=list(range(1, 17)), day=2, start_hour=2, end_hour=4)
        ]

        self.course4 = Course(
            kcid="KC004",
            jx0404id="JX004",
            kcmc="物理实验",
            sksj="1-8周 星期一 8-10",
            xkrs=10,
            pkrs=20,
        )
        self.course4.time_slots = [
            TimeSlot(weeks=list(range(1, 9)), day=1, start_hour=8, end_hour=10)
        ]

    def test_courses_conflict_same_time(self):
        """测试相同时间冲突"""
        assert self.detector.courses_conflict(self.course1, self.course2)
        assert self.detector.courses_conflict(self.course2, self.course1)

    def test_courses_conflict_different_time(self):
        """测试不同时间无冲突"""
        assert not self.detector.courses_conflict(self.course1, self.course3)
        assert not self.detector.courses_conflict(self.course3, self.course1)

    def test_courses_conflict_partial_week_overlap(self):
        """测试部分周次重叠"""
        assert self.detector.courses_conflict(self.course1, self.course4)
        assert self.detector.courses_conflict(self.course4, self.course1)

    def test_courses_conflict_no_week_overlap(self):
        """测试周次不重叠"""
        course_no_overlap = Course(
            kcid="KC005",
            jx0404id="JX005",
            kcmc="化学实验",
            sksj="9-16周 星期一 8-10",
            xkrs=10,
            pkrs=20,
        )
        course_no_overlap.time_slots = [
            TimeSlot(weeks=list(range(9, 17)), day=1, start_hour=8, end_hour=10)
        ]

        assert not self.detector.courses_conflict(self.course4, course_no_overlap)

    def test_courses_conflict_same_course(self):
        """测试同一课程不算冲突"""
        assert not self.detector.courses_conflict(self.course1, self.course1)

    def test_find_conflicts(self):
        """测试找出所有冲突"""
        conflicts = self.detector.find_conflicts([
            self.course1,
            self.course2,
            self.course3,
        ])

        assert len(conflicts) == 1
        assert conflicts[0].course1.kcmc == "高等数学A"
        assert conflicts[0].course2.kcmc == "大学英语"

    def test_find_no_conflicts(self):
        """测试无冲突情况"""
        conflicts = self.detector.find_conflicts([
            self.course1,
            self.course3,
        ])

        assert len(conflicts) == 0

    def test_check_solution_conflict(self):
        """测试检查方案冲突"""
        solution = SelectionSolution(
            courses=[self.course1, self.course2],
            total_credits=8.0,
            total_courses=2
        )

        is_conflict_free = self.detector.check_solution(solution)

        assert not is_conflict_free
        assert len(solution.conflicts) == 1

    def test_check_solution_no_conflict(self):
        """测试检查方案无冲突"""
        solution = SelectionSolution(
            courses=[self.course1, self.course3],
            total_credits=8.0,
            total_courses=2
        )

        is_conflict_free = self.detector.check_solution(solution)

        assert is_conflict_free
        assert len(solution.conflicts) == 0

    def test_find_alternatives_for_course(self):
        """测试查找替代课程"""
        all_courses_by_name = {
            "高等数学A": [
                self.course1,
                self.course2,  # 冲突的时间
            ]
        }

        alternatives = self.detector.find_alternatives_for_course(
            self.course1,
            [self.course3],
            all_courses_by_name
        )

        # 应该返回不冲突的替代
        assert len(alternatives) == 1
        assert alternatives[0].jx0404id == self.course2.jx0404id

    def test_build_schedule(self):
        """测试构建课表"""
        schedule = self.detector.build_schedule([
            self.course1,
            self.course3,
        ])

        # 检查周一8-10节有课程
        monday_courses = schedule.get_courses_at(1, 8)
        assert len(monday_courses) == 1
        assert monday_courses[0].kcmc == "高等数学A"

        # 检查周二2-4节有课程
        tuesday_courses = schedule.get_courses_at(2, 2)
        assert len(tuesday_courses) == 1
        assert tuesday_courses[0].kcmc == "程序设计基础"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
