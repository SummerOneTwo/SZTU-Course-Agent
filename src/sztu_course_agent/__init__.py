"""
SZTU Course Agent - 智能课程冲突检测与选课方案生成系统
"""

__version__ = "0.1.0"

from .models.course import Course, TimeSlot, TeacherInfo
from .models.schedule import Schedule, ConflictInfo
from .models.user_preference import Preference, TimePreference
from .models.solution import SelectionSolution
from .core.time_slot_parser import parse_course_time, time_slots_conflict
from .core.conflict_detector import ConflictDetector
from .core.csp_solver import CSPSolver
from .tools.course_loader import CourseLoader
from .tools.schedule_builder import ScheduleBuilder
from .tools.solution_exporter import SolutionExporter

__all__ = [
    # Models
    "Course",
    "TimeSlot",
    "TeacherInfo",
    "Schedule",
    "ConflictInfo",
    "Preference",
    "TimePreference",
    "SelectionSolution",
    # Core
    "parse_course_time",
    "time_slots_conflict",
    "ConflictDetector",
    "CSPSolver",
    # Tools
    "CourseLoader",
    "ScheduleBuilder",
    "SolutionExporter",
]
