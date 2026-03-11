"""核心算法模块"""

from .time_slot_parser import parse_course_time, time_slots_conflict
from .conflict_detector import ConflictDetector
from .csp_solver import CSPSolver

__all__ = [
    "parse_course_time",
    "time_slots_conflict",
    "ConflictDetector",
    "CSPSolver",
]
