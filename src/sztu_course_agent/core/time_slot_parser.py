"""时间槽解析器

解析 sksj 格式的时间字符串，如:
- "1-16周 星期一 8-10"
- "1-8,10-16周 星期三 2-4"
- "单周 1-16周 星期五 6-8"
"""
import re
from typing import List, Tuple, Optional
from ..models.course import TimeSlot


# 星期映射
DAY_MAP = {
    "星期一": 1, "星期二": 2, "星期三": 3, "星期四": 4, "星期五": 5,
    "星期六": 6, "星期日": 7,
    "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5,
    "周六": 6, "周日": 7,
    "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7,
    "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
}


def parse_weeks(week_str: str) -> List[int]:
    """解析周次字符串

    Args:
        week_str: 周次字符串，如 "1-16", "1-8,10-16", "1,3,5-8"

    Returns:
        周次列表
    """
    weeks = []

    # 移除"周"字
    week_str = week_str.replace("周", "").strip()

    # 解析逗号分隔的多个区间
    parts = week_str.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            # 区间，如 "1-16"
            start, end = map(int, part.split("-"))
            weeks.extend(range(start, end + 1))
        else:
            # 单周次，如 "3"
            weeks.append(int(part))

    return sorted(list(set(weeks)))


def parse_day(day_str: str) -> Optional[int]:
    """解析星期字符串

    Args:
        day_str: 星期字符串

    Returns:
        1-7，解析失败返回 None
    """
    day_str = day_str.strip()
    return DAY_MAP.get(day_str)


def parse_slots(slot_str: str) -> Tuple[int, int]:
    """解析节次字符串

    Args:
        slot_str: 节次字符串，如 "8-10", "2", "3-5"

    Returns:
        (start, end) 元组
    """
    slot_str = slot_str.strip()

    if "-" in slot_str:
        start, end = map(int, slot_str.split("-"))
        return int(start), int(end)
    else:
        slot = int(slot_str)
        return slot, slot


def detect_week_type(sksj: str) -> str:
    """检测周类型

    Returns:
        "单周", "双周", 或 "all"
    """
    if "单周" in sksj:
        return "单周"
    elif "双周" in sksj:
        return "双周"
    return "all"


def filter_weeks_by_type(weeks: List[int], week_type: str) -> List[int]:
    """根据周类型过滤周次

    Args:
        weeks: 周次列表
        week_type: "单周", "双周", 或 "all"

    Returns:
        过滤后的周次列表
    """
    if week_type == "单周":
        return [w for w in weeks if w % 2 == 1]
    elif week_type == "双周":
        return [w for w in weeks if w % 2 == 0]
    return weeks


def parse_time_slot(sksj: str) -> Optional[TimeSlot]:
    """解析单个时间槽

    Args:
        sksj: 时间字符串，如 "1-16周 星期一 8-10"

    Returns:
        TimeSlot 对象，解析失败返回 None
    """
    if not sksj or not sksj.strip():
        return None

    sksj = sksj.strip()
    week_type = detect_week_type(sksj)

    # 提取周次部分
    week_match = re.search(r'(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*?)\s*周', sksj)
    if not week_match:
        return None

    weeks_str = week_match.group(1)
    weeks = parse_weeks(weeks_str)
    weeks = filter_weeks_by_type(weeks, week_type)

    if not weeks:
        return None

    # 提取星期
    day = None
    for day_key in DAY_MAP.keys():
        if day_key in sksj:
            day = parse_day(day_key)
            break

    if day is None:
        return None

    # 提取节次
    # 匹配最后的数字区间或单个数字
    slot_match = re.search(r'(\d+(?:-\d+)?)\s*$', sksj)
    if not slot_match:
        return None

    start_slot, end_slot = parse_slots(slot_match.group(1))

    return TimeSlot(
        weeks=weeks,
        day=day,
        start_hour=start_slot,
        end_hour=end_slot,
        week_type=week_type
    )


def parse_course_time(sksj: str) -> List[TimeSlot]:
    """解析课程时间字符串，支持多个时间段

    Args:
        sksj: 完整时间字符串，如 "1-16周 星期一 8-10;1-16周 星期三 2-4"

    Returns:
        TimeSlot 列表
    """
    if not sksj or not sksj.strip():
        return []

    time_slots = []

    # 按分号、逗号或换行分割
    parts = re.split(r'[;,;\n]', sksj)

    for part in parts:
        part = part.strip()
        if part:
            time_slot = parse_time_slot(part)
            if time_slot:
                time_slots.append(time_slot)

    return time_slots


def time_slots_conflict(slot1: TimeSlot, slot2: TimeSlot) -> bool:
    """检测两个时间槽是否冲突

    Args:
        slot1: 时间槽1
        slot2: 时间槽2

    Returns:
        是否冲突
    """
    # 星期不同，无冲突
    if slot1.day != slot2.day:
        return False

    # 节次不同，无冲突
    if slot1.end_hour < slot2.start_hour or slot2.end_hour < slot1.start_hour:
        return False

    # 检查周次重叠
    weeks1 = set(slot1.weeks)
    weeks2 = set(slot2.weeks)

    # 无周次重叠
    if not weeks1.intersection(weeks2):
        return False

    return True
