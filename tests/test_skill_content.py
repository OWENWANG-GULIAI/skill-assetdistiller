import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContentTests(unittest.TestCase):
    def test_skill_centers_original_four_modules_and_top_three_assets(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "Top 3", "资产评估", "变现切入点", "潜在用户", "专家访谈",
            "关键决策", "反常识", "可迁移", "经验 + AI + 场景",
            "我有的 × 别人需要的 × 我愿意长期做的", "PDF"
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("完整 10 章", text)

    def test_interview_is_triggered_but_does_not_deadlock_a_declining_user(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("2-3 个", text)
        self.assertIn("资料过薄", text)
        self.assertIn("用户不回答", text)
        self.assertIn("保守版", text)
        self.assertIn("待验证假设", text)

    def test_pdf_visual_rules_are_explicit(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        template = (ROOT / "references" / "output_template.md").read_text(encoding="utf-8")
        combined = text + template
        for phrase in (
            "1.5 倍行距", "一级编号", "二级编号", "GULIAI", "白底",
            "不使用黑色", "10.5", "9.5", "评分", "排序", "矩阵", "图表"
        ):
            self.assertIn(phrase, combined)


if __name__ == "__main__":
    unittest.main()
