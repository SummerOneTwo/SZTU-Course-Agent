"""课程数据加载器"""
import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from ..models.course import Course, course_from_dict
from ..core.time_slot_parser import parse_course_time


class CourseLoader:
    """课程数据加载器"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: 课程数据目录，默认为当前目录下的 JSON 文件
        """
        self.data_dir = data_dir
        self._courses: List[Course] = []
        self._by_id: Dict[str, Course] = {}
        self._by_name: Dict[str, List[Course]] = {}
        self._by_kcid: Dict[str, List[Course]] = {}

    def load_from_json(self, filepath: str) -> None:
        """从 JSON 文件加载课程数据

        Args:
            filepath: JSON 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON 格式错误: 期望是课程列表")

        for item in data:
            try:
                course = course_from_dict(item)
                # 解析时间槽
                course.time_slots = parse_course_time(course.sksj)
                self._courses.append(course)
            except Exception as e:
                print(f"解析课程失败: {item.get('kcmc', 'Unknown')}: {e}")

        self._build_indexes()

    def load_from_directory(self, directory: str) -> None:
        """从目录加载所有 JSON 课程数据文件

        Args:
            directory: 目录路径
        """
        dir_path = Path(directory)
        for filepath in dir_path.glob("*.json"):
            try:
                self.load_from_json(str(filepath))
            except Exception as e:
                print(f"加载文件失败 {filepath}: {e}")

    def _build_indexes(self) -> None:
        """构建索引"""
        self._by_id.clear()
        self._by_name.clear()
        self._by_kcid.clear()

        for course in self._courses:
            # 按 jx0404id 索引
            if course.jx0404id:
                self._by_id[course.jx0404id] = course

            # 按课程名索引
            if course.kcmc:
                if course.kcmc not in self._by_name:
                    self._by_name[course.kcmc] = []
                self._by_name[course.kcmc].append(course)

            # 按 kcid 索引
            if course.kcid:
                if course.kcid not in self._by_kcid:
                    self._by_kcid[course.kcid] = []
                self._by_kcid[course.kcid].append(course)

    def get_all_courses(self) -> List[Course]:
        """获取所有课程"""
        return self._courses.copy()

    def get_by_id(self, jx0404id: str) -> Optional[Course]:
        """按教学班ID获取课程"""
        return self._by_id.get(jx0404id)

    def get_by_name(self, name: str, fuzzy: bool = False) -> List[Course]:
        """按课程名获取课程

        Args:
            name: 课程名
            fuzzy: 是否模糊匹配

        Returns:
            课程列表
        """
        if fuzzy:
            results = []
            for course_name, courses in self._by_name.items():
                if name.lower() in course_name.lower():
                    results.extend(courses)
            return results
        return self._by_name.get(name, []).copy()

    def get_by_kcid(self, kcid: str) -> List[Course]:
        """按课程ID获取课程列表"""
        return self._by_kcid.get(kcid, []).copy()

    def search(self, query: str) -> List[Course]:
        """搜索课程

        Args:
            query: 搜索关键词 (课程名、教师、教室等)

        Returns:
            匹配的课程列表
        """
        query = query.lower()
        results = []

        for course in self._courses:
            # 检查课程名
            if query in course.kcmc.lower():
                results.append(course)
                continue

            # 检查教师
            if query in course.skls.lower():
                results.append(course)
                continue

            # 检查开课单位
            if query in course.dwmc.lower():
                results.append(course)
                continue

            # 检查时间
            if query in course.sksj.lower():
                results.append(course)
                continue

        return results

    def filter_by_capacity(self, min_remaining: int = 0) -> List[Course]:
        """过滤有剩余容量的课程

        Args:
            min_remaining: 最小剩余容量

        Returns:
            课程列表
        """
        return [c for c in self._courses if c.remaining_capacity >= min_remaining]

    def get_course_groups(self) -> Dict[str, List[Course]]:
        """获取按课程名分组的课程字典"""
        return {k: v.copy() for k, v in self._by_name.items()}

    @classmethod
    def auto_load(cls) -> "CourseLoader":
        """自动加载当前目录的课程数据

        Returns:
            CourseLoader 实例
        """
        loader = cls()

        # 尝试常见的课程数据文件
        possible_files = [
            "选课数据_完整.json",
            "选课数据_完整（读取部分了解结构即可）.json",
            "courses.json",
            "course_data.json",
        ]

        loaded = False
        for filename in possible_files:
            if os.path.exists(filename):
                try:
                    loader.load_from_json(filename)
                    print(f"已加载: {filename} ({len(loader._courses)} 门课程)")
                    loaded = True
                    break
                except Exception as e:
                    print(f"加载失败 {filename}: {e}")

        if not loaded:
            print("未找到课程数据文件")

        return loader
