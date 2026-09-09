import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_pdf_report import (  # noqa: E402
    PALETTE,
    TABLE_HEADER_BACKGROUND,
    asset_score,
    generate_report,
    make_styles,
    product_score,
    requires_interview,
    validate_report_data,
)


def sample_report():
    return json.loads((ROOT / "sample-report.json").read_text(encoding="utf-8"))


class PdfReportTests(unittest.TestCase):
    def test_sparse_experience_requires_expert_interview(self):
        sparse = {"scene": "企业培训", "challenge": "", "personal_role": "", "key_decision": "", "actions": [], "deliverables": [], "result_evidence": "", "transferable_method": ""}
        complete = {"scene": "企业 AI 培训", "challenge": "工具学习后无法落地", "personal_role": "课程设计与主讲", "key_decision": "按岗位任务重构练习", "actions": ["访谈", "设计", "授课"], "deliverables": ["场景任务卡"], "result_evidence": "20+ 期训练营", "transferable_method": "岗位任务-练习-反馈"}
        self.assertTrue(requires_interview(sparse))
        self.assertFalse(requires_interview(complete))

    def test_scores_use_declared_weights(self):
        self.assertEqual(asset_score({"problem_value": 23, "result_evidence": 17, "moat": 18, "portability": 14, "product_readiness": 18}), 90)
        self.assertEqual(product_score({"customer_urgency": 22, "experience_fit": 24, "delivery_control": 18, "buyer_clarity": 13, "low_cost_validation": 14}), 91)

    def test_validation_rejects_wrong_top_asset_count_and_score(self):
        data = sample_report()
        too_few = deepcopy(data)
        too_few["top_assets"] = too_few["top_assets"][:2]
        with self.assertRaisesRegex(ValueError, "top_assets"):
            validate_report_data(too_few)
        mismatch = deepcopy(data)
        mismatch["top_assets"][0]["score_total"] -= 1
        with self.assertRaisesRegex(ValueError, "score_total"):
            validate_report_data(mismatch)

    def test_typography_and_palette_follow_brand_contract(self):
        styles = make_styles()
        for name, style in styles.items():
            self.assertAlmostEqual(style.leading, style.fontSize * 1.5, places=2, msg=name)
        self.assertGreaterEqual(styles["body"].fontSize, 10.5)
        self.assertGreaterEqual(styles["table"].fontSize, 9.5)
        self.assertGreaterEqual(styles["h1"].fontSize, 21)
        self.assertEqual(PALETTE["gold"].hexval().upper(), "0XD89808")
        self.assertEqual(PALETTE["paper"].hexval().upper(), "0XFFFFFF")
        self.assertEqual(TABLE_HEADER_BACKGROUND, PALETTE["pale_gold"])

    def test_generates_nine_chapter_branded_pdf_without_dark_page_fills(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "report.pdf"
            generate_report(sample_report(), output, ROOT / "assets" / "guliai-logo-transparent.png")
            from pypdf import PdfReader
            reader = PdfReader(str(output))
            text = "".join(page.extract_text() or "" for page in reader.pages)
            self.assertGreater(output.stat().st_size, 20000)
            self.assertGreaterEqual(len(reader.pages), 9)
            for heading in (
                "1. 核心诊断结论", "2. Top 3 经验资产评估", "3. 护城河与不可替代性",
                "4. 高价值问题与付费客户", "5. 变现切入点与产品清单", "6. 首选产品设计",
                "7. 专家访谈追问", "8. 商业化行动路径", "9. 证据与使用边界",
            ):
                self.assertIn(heading, text)
            self.assertIn("资产价值指数", text)
            self.assertIn("产品优先级", text)
            self.assertIn("P1", text)
            self.assertNotIn("<br/>", text)
            prefix = Path(directory) / "page"
            render = subprocess.run(["pdftoppm", "-png", "-r", "72", str(output), str(prefix)], capture_output=True, text=True, check=False)
            self.assertEqual(render.returncode, 0, render.stderr)
            for png in sorted(Path(directory).glob("page-*.png")):
                image = Image.open(png).convert("RGB")
                pixels = list(image.get_flattened_data())
                near_dark = sum(1 for r, g, b in pixels if r < 45 and g < 45 and b < 45)
                self.assertLess(near_dark / len(pixels), 0.08, png.name)


if __name__ == "__main__":
    unittest.main()
