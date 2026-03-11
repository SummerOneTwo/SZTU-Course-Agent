from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import time


class TimeSlot(BaseModel):
    """时间槽模型"""
    weeks: List[int] = Field(description="周次列表，如 [1,2,3,4,5,6,7,8]")
    day: int = Field(ge=1, le=7, description="星期几 (1-7)")
    start_hour: int = Field(ge=1, le=12, description="开始节次")
    end_hour: int = Field(ge=1, le=12, description="结束节次")
    week_type: str = Field(default="all", description="周类型: all/单周/双周")

    def __str__(self) -> str:
        day_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        week_str = f"{self.weeks[0]}-{self.weeks[-1]}周"
        return f"{week_str} {day_names[self.day]} {self.start_hour}-{self.end_hour}节"


class TeacherInfo(BaseModel):
    """教师信息模型"""
    jgxm: str = Field(description="教师姓名")
    jssj: str = Field(description="结束时间，如 17:55")
    kssj: str = Field(description="开始时间，如 15:45")
    jsmc: str = Field(description="教室名称，如 C-5-366")
    jzwmc: str = Field(description="教学楼名称")


class Course(BaseModel):
    """课程模型"""
    kcid: str = Field(description="课程ID")
    jx0404id: str = Field(description="教学班ID")
    kcmc: str = Field(description="课程名称")
    kch: str = Field(default="", description="课程号")
    kcxzmc: str = Field(default="", description="课程性质名称")
    kcsxmc: str = Field(default="", description="课程属性名称")
    xf: float = Field(default=0.0, description="学分")
    xkrs: int = Field(default=0, description="已选人数")
    pkrs: int = Field(default=0, description="容量上限")
    dwmc: str = Field(default="", description="开课单位")
    sksj: str = Field(default="", description="上课时间字符串")
    skls: str = Field(default="", description="教师姓名")
    time_slots: List[TimeSlot] = Field(default_factory=list, description="解析后的时间槽列表")
    teachers: List[TeacherInfo] = Field(default_factory=list, description="教师信息列表")
    csm: Optional[str] = Field(default=None, description="冲突说明")
    ktmc: str = Field(default="", description="上课班级范围")

    @property
    def remaining_capacity(self) -> int:
        """剩余容量"""
        return self.pkrs - self.xkrs

    @property
    def is_full(self) -> bool:
        """是否已满"""
        return self.remaining_capacity <= 0

    @property
    def capacity_ratio(self) -> float:
        """已选比例 (0-1)"""
        if self.pkrs == 0:
            return 0.0
        return self.xkrs / self.pkrs

    def __str__(self) -> str:
        return f"{self.kcmc} [{self.jx0404id}] ({self.xkrs}/{self.pkrs})"


def course_from_dict(data: dict) -> Course:
    """从字典创建Course对象"""
    return Course(
        kcid=data.get("kcid", ""),
        jx0404id=data.get("jx0404id", ""),
        kcmc=data.get("kcmc", ""),
        kch=data.get("kch", ""),
        kcxzmc=data.get("kcxzmc", ""),
        kcsxmc=data.get("kcsxmc", ""),
        xf=float(data.get("xf", 0)),
        xkrs=int(data.get("xkrs", 0)),
        pkrs=int(data.get("pkrs", 0)),
        dwmc=data.get("dwmc", ""),
        sksj=data.get("sksj", ""),
        skls=data.get("skls", data.get("jsmc", "")),
        csm=data.get("csm", data.get("ctsm", None)),
        ktmc=data.get("ktmc", ""),
    )
