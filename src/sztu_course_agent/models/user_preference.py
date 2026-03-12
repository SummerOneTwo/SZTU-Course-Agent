from pydantic import BaseModel, Field
from typing import List, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .course import Course


class TimePreference(BaseModel):
    """时间偏好设置"""
    preferred_days: List[int] = Field(default_factory=list, description="偏好星期 (1-7)")
    avoided_days: List[int] = Field(default_factory=list, description="避开星期 (1-7)")
    preferred_slots: List[int] = Field(default_factory=list, description="偏好节次 (1-12)")
    avoided_slots: List[int] = Field(default_factory=list, description="避开节次 (1-12)")
    prefer_morning: bool = True
    prefer_afternoon: bool = True
    prefer_evening: bool = False

    def score_time(self, day: int, slot: int) -> float:
        """对时间打分 (0-1)"""
        score = 1.0

        if day in self.avoided_days:
            score -= 0.5
        if slot in self.avoided_slots:
            score -= 0.5
        if day in self.preferred_days:
            score += 0.2
        if slot in self.preferred_slots:
            score += 0.2

        # 早晚偏好
        if 6 <= slot <= 9:  # 上午
            score += 0.1 if self.prefer_morning else -0.2
        elif 10 <= slot <= 12:  # 下午
            score += 0.1 if self.prefer_afternoon else -0.2
        elif slot >= 11:  # 晚上
            score += 0.1 if self.prefer_evening else -0.2

        return max(0.0, min(1.0, score))


class Preference(BaseModel):
    """用户偏好模型"""
    target_courses: List[str] = Field(default_factory=list, description="目标课程名称列表")
    min_credits: float = 0.0
    max_credits: float = 30.0
    preferred_teachers: List[str] = Field(default_factory=list, description="偏好教师")
    avoided_teachers: List[str] = Field(default_factory=list, description="避开教师")
    time_pref: TimePreference = Field(default_factory=TimePreference)
    prefer_high_capacity: bool = True
    prefer_not_full: bool = True
    locked_courses: List[str] = Field(default_factory=list, description="锁定的教学班ID列表，不可被移除")
    course_priorities: Dict[str, int] = Field(default_factory=dict, description="课程名->优先级(1-10)，用于取舍决策")
    must_have_courses: List[str] = Field(default_factory=list, description="必选课程名称列表（区别于锁定：锁定是已选定教学班，必选是必须有但可换班）")

    def score_course(self, course: "Course") -> float:
        """对课程打分 (0-1)"""
        score = 0.5  # 基础分

        # 教师偏好
        if self.preferred_teachers and course.skls:
            if any(t in course.skls for t in self.preferred_teachers):
                score += 0.3
        if self.avoided_teachers and course.skls:
            if any(t in course.skls for t in self.avoided_teachers):
                score -= 0.5

        # 容量偏好
        if self.prefer_high_capacity:
            score += course.capacity_ratio * 0.2
        if self.prefer_not_full and course.is_full:
            score -= 0.8

        # 时间偏好
        if course.time_slots:
            for time_slot in course.time_slots:
                time_score = self.time_pref.score_time(time_slot.day, time_slot.start_hour)
                score += time_score * 0.2
                break  # 只评估第一个时间段

        return max(0.0, min(1.0, score))
