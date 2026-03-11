"""数据模型模块"""

from .course import Course, TimeSlot, TeacherInfo
from .schedule import Schedule, ConflictInfo
from .user_preference import Preference, TimePreference
from .solution import SelectionSolution

__all__ = [
    "Course",
    "TimeSlot",
    "TeacherInfo",
    "Schedule",
    "ConflictInfo",
    "Preference",
    "TimePreference",
    "SelectionSolution",
]
