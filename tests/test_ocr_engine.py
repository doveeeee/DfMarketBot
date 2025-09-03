import os
import unittest

import cv2

from src.infrastructure.ocr_engine import TemplateOCREngine


class TestTemplateOCREngine(unittest.TestCase):
    """测试模板匹配"""

    def test_default_font_1080p(self):
        ocr = TemplateOCREngine(resolution=(1920, 1080))
        bad_cases_dir = os.path.join(os.path.dirname(__file__), "ocr_bad_cases", "bad_cases_1080p", "default")
        failed_result = []
        for file_name in os.listdir(bad_cases_dir):
            if not file_name.endswith(".png"):
                self.fail("测试文件格式有误，请检查！")
            file_path = os.path.join(bad_cases_dir, file_name)
            img = cv2.imread(file_path)
            if img is None:
                self.fail(f"Failed to read image: {file_name}")
            actual = ocr.image_to_string(img, thresh=80)
            expected = file_name.split(".")[0].split("_")[0]
            print(f"file {file_name} detected: {actual}")
            if expected != actual:
                print(f"file {file_name} detect failed: {actual}")
                failed_result.append({"expected": expected, "actual": actual})
        if len(failed_result) != 0:
            self.fail(f"ocr detect failed: {failed_result}")
