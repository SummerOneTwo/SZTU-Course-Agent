"""方案导出 - 导出为抢课脚本可用的配置文件"""
import json
import tomli_w
from typing import List
from pathlib import Path
from ..models.solution import SelectionSolution
from ..models.course import Course


class SolutionExporter:
    """方案导出器"""

    def export_to_toml(self, solution: SelectionSolution, output_path: str) -> None:
        """导出为 TOML 格式 (兼容现有抢课脚本)

        Args:
            solution: 选课方案
            output_path: 输出文件路径
        """
        # 构建配置字典
        config = {
            "courses": []
        }

        # 将课程按 kcid 分组
        courses_by_kcid = {}
        for course in solution.courses:
            if course.kcid not in courses_by_kcid:
                courses_by_kcid[course.kcid] = []
            courses_by_kcid[course.kcid].append(course)

        # 构建课程配置
        for kcid, courses in courses_by_kcid.items():
            first_course = courses[0]
            course_config = {
                "name": first_course.kcmc,
                "kcid": kcid,
                "cno": "1",  # 默认跨年级选课
                "jx0404id": [c.jx0404id for c in courses]
            }
            config["courses"].append(course_config)

        # 写入 TOML 文件
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix('.toml')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tomli_w.dumps(config))

        print(f"已导出方案到: {output_path}")

    def export_to_json(self, solution: SelectionSolution, output_path: str) -> None:
        """导出为 JSON 格式

        Args:
            solution: 选课方案
            output_path: 输出文件路径
        """
        config = {
            "courses": [],
            "metadata": {
                "total_credits": solution.total_credits,
                "total_courses": solution.total_courses,
                "score": solution.score,
                "has_conflicts": solution.has_conflicts,
            }
        }

        courses_by_kcid = {}
        for course in solution.courses:
            if course.kcid not in courses_by_kcid:
                courses_by_kcid[course.kcid] = []
            courses_by_kcid[course.kcid].append(course)

        for kcid, courses in courses_by_kcid.items():
            first_course = courses[0]
            course_config = {
                "name": first_course.kcmc,
                "kcid": kcid,
                "cno": "1",
                "jx0404id": [c.jx0404id for c in courses],
                "teacher": first_course.skls,
                "capacity": f"{first_course.xkrs}/{first_course.pkrs}",
                "time": first_course.sksj.strip(),
            }
            config["courses"].append(course_config)

        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix('.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"已导出方案到: {output_path}")

    def export_multiple_solutions(self, solutions: List[SelectionSolution], output_dir: str) -> None:
        """导出多个方案

        Args:
            solutions: 方案列表
            output_dir: 输出目录
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, solution in enumerate(solutions, 1):
            filename = f"solution_{i}_score_{int(solution.score)}"
            self.export_to_toml(solution, output_dir / f"{filename}.toml")

        print(f"已导出 {len(solutions)} 个方案到: {output_dir}")

    def generate_config_template(self, solution: SelectionSolution) -> str:
        """生成配置模板字符串

        Args:
            solution: 选课方案

        Returns:
            TOML 配置字符串
        """
        lines = [
            "# ============================================================",
            "# SZTU 抢课脚本配置文件 (由 AI Agent 生成)",
            "# ============================================================",
            "",
            "[account]",
            "username = \"YOUR_USERNAME\"",
            "password = \"YOUR_PASSWORD\"",
            "",
            "# ============================================================",
            "# 课程配置",
            "# ============================================================",
            ""
        ]

        courses_by_kcid = {}
        for course in solution.courses:
            if course.kcid not in courses_by_kcid:
                courses_by_kcid[course.kcid] = []
            courses_by_kcid[course.kcid].append(course)

        for kcid, courses in courses_by_kcid.items():
            first_course = courses[0]
            lines.append(f"[[courses]]")
            lines.append(f'name = "{first_course.kcmc}"')
            lines.append(f'kcid = "{kcid}"')
            lines.append('cno = "1"')
            lines.append('jx0404id = [')
            for course in courses:
                lines.append(f'    "{course.jx0404id}",')
            lines.append(']')
            lines.append('')

        lines.extend([
            "# ============================================================",
            "# 运行设置 (请根据实际情况修改)",
            "# ============================================================",
            "",
            "[settings]",
            "mode = \"scavenge\"",
            f"target_count = {solution.total_courses}",
            "max_workers = 8",
            "round_cool_down_min = 280",
            "round_cool_down_max = 320",
            "schedule_start = \"09:00\"",
            "schedule_end = \"22:00\"",
        ])

        return "\n".join(lines)

    def export_config_with_settings(
        self,
        solution: SelectionSolution,
        output_path: str,
        settings: dict = None
    ) -> None:
        """导出完整配置 (包含账户和运行设置)

        Args:
            solution: 选课方案
            output_path: 输出文件路径
            settings: 运行设置字典
        """
        if settings is None:
            settings = {
                "mode": "scavenge",
                "target_count": solution.total_courses,
                "max_workers": 8,
                "round_cool_down_min": 280,
                "round_cool_down_max": 320,
                "schedule_start": "09:00",
                "schedule_end": "22:00",
            }

        config = {
            "account": {
                "username": "YOUR_USERNAME",
                "password": "YOUR_PASSWORD",
            },
            "courses": []
        }

        courses_by_kcid = {}
        for course in solution.courses:
            if course.kcid not in courses_by_kcid:
                courses_by_kcid[course.kcid] = []
            courses_by_kcid[course.kcid].append(course)

        for kcid, courses in courses_by_kcid.items():
            first_course = courses[0]
            course_config = {
                "name": first_course.kcmc,
                "kcid": kcid,
                "cno": "1",
                "jx0404id": [c.jx0404id for c in courses]
            }
            config["courses"].append(course_config)

        config["settings"] = settings

        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix('.toml')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tomli_w.dumps(config))

        print(f"已导出完整配置到: {output_path}")
