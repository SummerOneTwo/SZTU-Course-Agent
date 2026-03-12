"""测试时间槽解析器"""
import pytest
from sztu_course_agent.core.time_slot_parser import (
    parse_weeks,
    parse_day,
    parse_slots,
    parse_time_slot,
    parse_course_time,
    time_slots_conflict,
)
from sztu_course_agent.models.course import TimeSlot


class TestParseWeeks:
    """测试周次解析"""

    def test_single_week(self):
        """单个周次"""
        assert parse_weeks("1周") == [1]
        assert parse_weeks("5周") == [5]

    def test_week_range(self):
        """周次范围"""
        assert parse_weeks("1-16周") == list(range(1, 17))
        assert parse_weeks("3-8周") == [3, 4, 5, 6, 7, 8]

    def test_multiple_ranges(self):
        """多个范围"""
        assert parse_weeks("1-8,10-16周") == list(range(1, 9)) + list(range(10, 17))
        assert parse_weeks("1,3,5-7周") == [1, 3, 5, 6, 7]

    def test_weeks_without_zhou(self):
        """没有'周'字"""
        assert parse_weeks("1-16") == list(range(1, 17))


class TestParseDay:
    """测试星期解析"""

    def test_chinese_days(self):
        """中文星期"""
        assert parse_day("星期一") == 1
        assert parse_day("星期三") == 3
        assert parse_day("星期日") == 7
        assert parse_day("周一") == 1
        assert parse_day("周五") == 5
        assert parse_day("周日") == 7

    def test_english_days(self):
        """英文星期"""
        assert parse_day("Monday") == 1
        assert parse_day("Wed") == 3
        assert parse_day("Sun") == 7

    def test_number_days(self):
        """数字星期"""
        assert parse_day("1") == 1
        assert parse_day("5") == 5

    def test_invalid_day(self):
        """无效星期"""
        assert parse_day("星期八") is None
        assert parse_day("Monx") is None


class TestParseSlots:
    """测试节次解析"""

    def test_single_slot(self):
        """单个节次"""
        assert parse_slots("8") == (8, 8)
        assert parse_slots("3") == (3, 3)

    def test_slot_range(self):
        """节次范围"""
        assert parse_slots("8-10") == (8, 10)
        assert parse_slots("1-3") == (1, 3)
        assert parse_slots("2-4") == (2, 4)


class TestParseTimeSlot:
    """测试完整时间槽解析"""

    def test_basic_format(self):
        """基本格式"""
        slot = parse_time_slot("1-16周 星期一 8-10")
        assert slot is not None
        assert slot.weeks == list(range(1, 17))
        assert slot.day == 1
        assert slot.start_hour == 8
        assert slot.end_hour == 10
        assert slot.week_type == "all"

    def test_odd_weeks(self):
        """单周"""
        slot = parse_time_slot("单周 1-16周 星期三 2-4")
        assert slot is not None
        assert slot.week_type == "单周"
        assert len(slot.weeks) == 8  # 16周中单周有8个
        assert slot.day == 3
        assert slot.start_hour == 2
        assert slot.end_hour == 4

    def test_even_weeks(self):
        """双周"""
        slot = parse_time_slot("双周 1-16周 星期五 6-8")
        assert slot is not None
        assert slot.week_type == "双周"
        assert len(slot.weeks) == 8  # 16周中双周有8个
        assert slot.day == 5
        assert slot.start_hour == 6
        assert slot.end_hour == 8

    def test_multiple_week_ranges(self):
        """多个周范围"""
        slot = parse_time_slot("1-8,10-16周 星期二 1-3")
        assert slot is not None
        assert len(slot.weeks) == 15
        assert slot.day == 2
        assert slot.start_hour == 1
        assert slot.end_hour == 3


class TestParseCourseTime:
    """测试课程时间字符串解析"""

    def test_single_slot(self):
        """单个时间段"""
        slots = parse_course_time("1-16周 星期一 8-10")
        assert len(slots) == 1
        assert slots[0].day == 1
        assert slots[0].start_hour == 8
        assert slots[0].end_hour == 10

    def test_multiple_slots(self):
        """多个时间段"""
        slots = parse_course_time("1-16周 星期一 8-10; 1-16周 星期三 2-4")
        assert len(slots) == 2
        assert slots[0].day == 1
        assert slots[1].day == 3

    def test_empty_string(self):
        """空字符串"""
        slots = parse_course_time("")
        assert len(slots) == 0

        slots = parse_course_time("   ")
        assert len(slots) == 0


class TestTimeSlotsConflict:
    """测试时间槽冲突检测"""

    def test_no_same_day(self):
        """不同星期，无冲突"""
        slot1 = TimeSlot(weeks=[1, 2], day=1, start_hour=8, end_hour=10)
        slot2 = TimeSlot(weeks=[1, 2], day=2, start_hour=8, end_hour=10)
        assert not time_slots_conflict(slot1, slot2)

    def test_no_same_slot_range(self):
        """同一星期但节次不重叠"""
        slot1 = TimeSlot(weeks=[1, 2], day=1, start_hour=1, end_hour=3)
        slot2 = TimeSlot(weeks=[1, 2], day=1, start_hour=4, end_hour=6)
        assert not time_slots_conflict(slot1, slot2)

    def test_overlapping_slots(self):
        """节次重叠"""
        slot1 = TimeSlot(weeks=[1, 2], day=1, start_hour=8, end_hour=10)
        slot2 = TimeSlot(weeks=[1, 2], day=1, start_hour=9, end_hour=11)
        assert time_slots_conflict(slot1, slot2)

    def test_same_slots(self):
        """完全相同的时间"""
        slot1 = TimeSlot(weeks=[1, 2], day=1, start_hour=8, end_hour=10)
        slot2 = TimeSlot(weeks=[1, 2], day=1, start_hour=8, end_hour=10)
        assert time_slots_conflict(slot1, slot2)

    def test_no_week_overlap(self):
        """周次不重叠"""
        slot1 = TimeSlot(weeks=[1, 2, 3], day=1, start_hour=8, end_hour=10)
        slot2 = TimeSlot(weeks=[4, 5, 6], day=1, start_hour=8, end_hour=10)
        assert not time_slots_conflict(slot1, slot2)

    def test_partial_week_overlap(self):
        """部分周次重叠"""
        slot1 = TimeSlot(weeks=[1, 2, 3, 4], day=1, start_hour=8, end_hour=10)
        slot2 = TimeSlot(weeks=[3, 4, 5, 6], day=1, start_hour=8, end_hour=10)
        assert time_slots_conflict(slot1, slot2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
