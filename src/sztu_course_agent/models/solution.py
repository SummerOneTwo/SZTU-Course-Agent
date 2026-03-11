from pydantic import BaseModel, Field
from typing import List
from .course import Course


class SelectionSolution(BaseModel):
    """选课方案模型"""
    courses: List[Course] = Field(default_factory=list, description="方案中的课程列表")
    total_credits: float = Field(default=0.0, description="总学分")
    total_courses: int = Field(default=0, description="总课程数")
    score: float = Field(default=0.0, description="方案评分 (0-100)")
    conflicts: List[str] = Field(default_factory=list, description="冲突信息")
    metadata: dict = Field(default_factory=dict, description="额外元数据")

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def __str__(self) -> str:
        status = "✅ 无冲突" if not self.has_conflicts else f"⚠️ {len(self.conflicts)} 个冲突"
        return (
            f"方案: {self.total_courses} 门课, {self.total_credits} 学分 | "
            f"评分: {self.score:.1f}/100 | {status}"
        )

    def summary(self) -> str:
        """生成方案摘要"""
        lines = [
            "=" * 60,
            f"方案评分: {self.score:.1f}/100",
            f"课程数量: {self.total_courses}",
            f"总学分: {self.total_credits:.1f}",
            f"状态: {'无冲突' if not self.has_conflicts else f'{len(self.conflicts)} 个冲突'}",
            "=" * 60,
            "\n课程列表:"
        ]
        for i, course in enumerate(self.courses, 1):
            lines.append(
                f"  {i}. {course.kcmc} ({course.skls}) - "
                f"{course.xkrs}/{course.pkrs} - {course.sksj}"
.strip()
            )

        if self.conflicts:
            lines.append("\n冲突:")
            for conflict in self.conflicts:
                lines.append(f"  - {conflict}")

        return "\n".join(lines)
