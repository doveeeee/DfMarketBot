# -*- coding: utf-8 -*-
"""
OCR引擎基础设施 - 基于模板匹配的图像识别
不使用三方OCR库，仅识别数字
"""
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
import pyautogui

from src.infrastructure.screen_capture import ScreenCapture

try:
    from src.core.exceptions import OCRException
    from src.core.interfaces import IOCREngine
except ImportError:
    from ..core.exceptions import OCRException
    from ..core.interfaces import IOCREngine


class TemplateOCREngine(IOCREngine):
    """基于模板匹配的OCR引擎"""

    _default_resolution = (1920, 1080)

    def __init__(self, templates_dir: str = None, resolution: Tuple[int, int] = None):
        if templates_dir is None:
            if resolution is None:
                resolution = pyautogui.size()
            templates_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                f"templates/{resolution[0]}x{resolution[1]}",
            )
            template_dir = Path(templates_dir)
            if not template_dir.exists():
                print("未找到模板文件，使用默认模板！")
                templates_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    f"templates/{self._default_resolution[0]}x{self._default_resolution[1]}",
                )

        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # 模板缓存
        self._templates = {}
        self._pic_templates = {}
        self._lock = threading.Lock()

        # 加载模板
        self._load_templates()

    def _load_pic(self, pic_name: str, threshold=127):
        sell_template_path = self.templates_dir / pic_name
        if sell_template_path.exists():
            template = cv2.imread(str(sell_template_path), cv2.IMREAD_GRAYSCALE)
            if template is not None:
                _, binary = cv2.threshold(template, threshold, 255, cv2.THRESH_BINARY)
                template_name = pic_name if not pic_name.endswith(".png") else pic_name[:-4]
                self._pic_templates[template_name] = binary

    def _load_templates(self):
        """加载所有数字模板"""

        def preprocess_template(template_path: Path, prefix=""):
            if not template_path.exists():
                return None

            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                return None
            base_thresh = 127
            base_method = cv2.THRESH_BINARY
            if prefix == "g":
                base_thresh = 50
            # elif prefix != "":
            else:
                base_thresh = 0
                base_method += cv2.THRESH_OTSU

            _, processed = cv2.threshold(template, base_thresh, 255, base_method)
            if prefix != "":
                contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    x, y, w, h = cv2.boundingRect(contours[0])
                    processed = processed[y : y + h, x : x + w]
            return processed

        try:
            with self._lock:
                # 加载默认数字模板 (0-9.png)
                default_group = {}
                for i in range(10):
                    binary = preprocess_template(self.templates_dir / f"{i}.png")
                    if binary is not None:
                        default_group[i] = binary

                if default_group:
                    self._templates["default"] = default_group

                # 加载带前缀的模板 (prefix_0.png~prefix_9.png)
                font_prefixes = set()
                for template_file in self.templates_dir.glob("*_*.png"):
                    parts = template_file.stem.split("_")
                    if len(parts) == 2 and parts[1].isdigit():
                        font_prefixes.add(parts[0])

                for prefix in sorted(font_prefixes):
                    group = {}
                    for i in range(10):
                        binary = preprocess_template(self.templates_dir / f"{prefix}_{i}.png", prefix)
                        if binary is not None:
                            group[i] = binary

                    if len(group) == 10:
                        self._templates[prefix] = group

                # 斜杠特殊处理下
                binary = preprocess_template(self.templates_dir / "w_slash.png", "w")
                if binary is not None:
                    self._templates["w"]["/"] = binary

                # 加载失败检测模板
                self._load_pic("option_failed.png")
                # 加载售卖框模板
                self._load_pic("sell.png")
                # 加载装备模板
                self._load_pic("equipment.png")
                self._load_pic("enter_teqingchu.png", 50)
                self._load_pic("equipment_scheme.png", 50)
                self._load_pic("xing_qian_bei_zhan.png")
                self._load_pic("start_action.png")
                self._load_pic("pei_zhuang.png")

                if not self._templates:
                    raise FileNotFoundError("未找到有效的数字模板文件")

        except Exception as e:
            raise OCRException(f"加载模板失败: {e}") from e

    def image_to_string(self, image: np.ndarray, binarize=True, font: str = "", thresh=127) -> str:
        """将图像转换为数字字符串"""
        try:
            # 确保图像是numpy数组
            if not isinstance(image, np.ndarray):
                image = np.array(image)
            processed = self._preprocess_image(image, binarize, thresh)
            # cv2.imshow("debug", processed)
            # cv2.waitKey()
            digits_info = []

            templates = self._templates.items()
            if font != "":
                template = self._templates.get(font)
                if template:
                    templates = {font: template}.items()
                else:
                    print(f"未找到字体({font})，将使用全量匹配")

            # 对每个字体组进行模板匹配
            for font_name, templates in templates:
                for digit, template in templates.items():
                    # 模板匹配
                    result = cv2.matchTemplate(processed, template, cv2.TM_CCOEFF_NORMED)
                    locations = np.where(result >= 0.7)  # 匹配阈值

                    for pt in zip(*locations[::-1]):
                        digits_info.append(
                            {"digit": digit, "x": pt[0], "score": result[pt[1], pt[0]], "font": font_name}
                        )

            # 非极大值抑制，去除重叠检测
            digits_info.sort(key=lambda x: -x["score"])
            filtered = []

            for info in digits_info:
                x = info["x"]
                overlap = False

                # 检查是否与已选区域重叠
                for selected in filtered:
                    template_width = self._templates[info["font"]][info["digit"]].shape[1]
                    selected_width = self._templates[selected["font"]][selected["digit"]].shape[1]
                    max_width = max(template_width, selected_width)

                    if abs(x - selected["x"]) < max_width * 0.6:  # 重叠阈值
                        overlap = True
                        break

                if not overlap:
                    filtered.append(info)

            # 按x坐标排序，拼接成字符串
            filtered.sort(key=lambda x: x["x"])
            return "".join(str(d["digit"]) for d in filtered)

        except Exception as e:
            raise OCRException(f"OCR识别失败: {e}") from e

    @staticmethod
    def _image_to_gray(image: np.ndarray) -> np.ndarray:
        """转换为灰度图"""
        if len(image.shape) == 3:
            if image.shape[2] == 3:  # RGB
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            elif image.shape[2] == 4:  # RGBA
                gray = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
            else:
                gray = image
        else:
            gray = image
        return gray

    def detect_template(self, image: np.ndarray, template_name: str) -> bool:
        """检测模板是否存在于图像中"""
        try:
            if self._pic_templates is None or self._pic_templates[template_name] is None:
                return False
            # 确保图像是numpy数组
            if not isinstance(image, np.ndarray):
                image = np.array(image)

            gray = self._image_to_gray(image)

            # 模板匹配
            result = cv2.matchTemplate(gray, self._pic_templates[template_name], cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            return max_val >= 0.7

        except Exception as e:
            raise OCRException(f"模板检测失败: {e}") from e

    @staticmethod
    def get_pixel_color(image: np.ndarray, x: int, y: int):
        """
        获取NumPy数组图像中指定坐标点的颜色值
        :param image: NumPy数组形式的图像数据 (OpenCV格式)
        :param x: x坐标 (列)
        :param y: y坐标 (行)
        :return:
            BGR颜色值 (如果是彩色图像)
            灰度值 (如果是灰度图像)
            None (如果坐标超出范围)
        """
        # 检查图像是否有效
        if not isinstance(image, np.ndarray):
            print("错误: 输入必须是NumPy数组")
            return None

        # 检查坐标是否在图像范围内
        height, width = image.shape[:2]
        if x < 0 or x >= width or y < 0 or y >= height:
            print(f"坐标({x},{y})超出图片范围(宽{width},高{height})")
            return None

        # 获取颜色值
        if len(image.shape) == 3:  # 彩色图像
            return tuple(image[y, x])
        # 灰度图像
        return int(image[y, x])

    def _preprocess_image(self, image, binarize=True, thresh=127):
        """预处理输入图像"""
        # 转换为灰度图
        processed = self._image_to_gray(image)
        # 二值化处理
        # TODO 灰色字体在这里识别效果不太好，需要特殊处理
        if binarize:
            method = cv2.THRESH_BINARY
            if thresh == 0:
                method += cv2.THRESH_OTSU
            _, processed = cv2.threshold(processed, thresh, 255, method)

        return processed


class TemplateContoursOCREngine(TemplateOCREngine):

    def __init__(self, templates_dir: str = None, resolution: Tuple[int, int] = None):
        super().__init__(templates_dir, resolution)
        self.confidence_threshold = 0.7

    @staticmethod
    def _find_digit_contours(binary_image):
        """找到图像中的数字轮廓"""
        # 寻找轮廓
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        digit_contours = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # 过滤太小或太大的区域
            if 5 < w < 100 and 10 < h < 100:
                # 计算宽高比，过滤非数字形状
                aspect_ratio = w / h
                if 0.3 < aspect_ratio < 1.2:
                    digit_contours.append((x, y, w, h))

        # 按x坐标排序，确保从左到右识别
        digit_contours.sort(key=lambda c: c[0])

        return digit_contours

    def _match_digit(self, roi, font_name, digit):
        """使用特定字体模板匹配数字"""
        template = self._templates[font_name][digit]

        # 调整模板大小以匹配ROI
        if roi.shape != template.shape:
            roi = cv2.resize(roi, (template.shape[1], template.shape[0]), interpolation=cv2.INTER_NEAREST)
        # 模板匹配
        result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        return max_val

    def _determine_best_font_and_digits(self, digit_regions, binary_image):
        """
        确定最佳匹配字体并同时识别数字

        Args:
            digit_regions: 数字区域列表
            binary_image: 二值化后的图像

        Returns:
            best_font: 最佳字体名称
            digit_results: 每个区域的识别结果列表 (digit, confidence)
            avg_confidence: 平均置信度
        """
        font_scores = defaultdict(float)
        font_digit_results = {}  # 存储每种字体下每个区域的识别结果

        for font_name in self._templates:
            total_confidence = 0
            valid_digits = 0
            digit_results = []

            for x, y, w, h in digit_regions:
                roi = binary_image[y : y + h, x : x + w]

                best_digit = -1
                best_confidence = 0

                for digit in range(10):
                    confidence = self._match_digit(roi, font_name, digit)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_digit = digit

                digit_results.append((best_digit, best_confidence))

                if best_confidence > self.confidence_threshold:
                    total_confidence += best_confidence
                    valid_digits += 1

            # 存储该字体的识别结果
            font_digit_results[font_name] = digit_results

            if valid_digits > 0:
                font_scores[font_name] = total_confidence / valid_digits

        if not font_scores:
            return None, [], 0

        # 返回平均置信度最高的字体及其识别结果
        best_font = max(font_scores.items(), key=lambda x: x[1])[0]
        digit_results = font_digit_results[best_font]
        avg_confidence = font_scores[best_font]

        return best_font, digit_results, avg_confidence

    def image_to_string(self, image: np.ndarray, binarize: bool = True, font: str = "", thresh=127) -> str:
        """
        识别图像中的连续数字

        Args:
            :param thresh:
            :param image: 包含连续数字的图像
            :param font:
            :param binarize:

        Returns:
            result: 识别到的数字字符串
        """
        # 预处理图像
        binary_image = self._preprocess_image(image)
        # 找到数字轮廓
        digit_regions = self._find_digit_contours(binary_image)

        if not digit_regions:
            return ""

        best_font, digit_results, avg_confidence = self._determine_best_font_and_digits(digit_regions, binary_image)
        print(best_font, digit_results, avg_confidence)
        # 使用最佳字体识别每个数字
        result = ""
        confidences = []

        for digit, confidence in digit_results:
            if confidence > self.confidence_threshold:
                result += str(digit)
                confidences.append(confidence)
            # else:
            #     result += "?"  # 无法识别的数字用?代替

        return result


class MockOCREngine(IOCREngine):
    """OCR引擎的模拟实现，用于测试"""

    def __init__(self, **kwargs):
        self.recognized_text = "1234"  # 默认返回的文本
        self.template_detected = False

    def image_to_string(self, image: np.ndarray, binarize=True, font: str = "", thresh: str = 127) -> str:
        """模拟OCR识别"""
        return self.recognized_text

    def detect_template(self, image: np.ndarray, template_name: str) -> bool:
        """模拟模板检测"""
        return self.template_detected

    @staticmethod
    def get_pixel_color(image: np.ndarray, x: int, y: int):
        """检测像素点的颜色"""
        return 100, 100, 100

    def recognize_price(self, image: np.ndarray) -> int:
        """模拟价格识别"""
        return int(self.recognized_text) if self.recognized_text.isdigit() else 0

    def set_recognized_text(self, text: str):
        """设置模拟返回的文本"""
        self.recognized_text = text

    def set_template_detected(self, detected: bool):
        """设置模板检测结果"""
        self.template_detected = detected


class OCREngineFactory:
    """OCR引擎工厂"""

    @staticmethod
    def create_engine(engine_type: str = "template", **kwargs) -> IOCREngine:
        """创建OCR引擎"""
        if engine_type == "template_contour":
            return TemplateContoursOCREngine(**kwargs)
        if engine_type == "template":
            return TemplateOCREngine(**kwargs)
        if engine_type == "mock":
            return MockOCREngine(**kwargs)
        raise ValueError(f"不支持的OCR引擎类型: {engine_type}")


if __name__ == "__main__":
    # ocr = TemplateContoursOCREngine(resolution=(2560,1440))
    ocr = TemplateOCREngine(resolution=(2560, 1440))
    # ocr = TemplateContoursOCREngine(resolution=(1920,1080))
    # ocr = TemplateOCREngine(resolution=(1920, 1080))
    sc = ScreenCapture(resolution=(2560, 1440))
    start = time.time()
    # screenshot = sc.capture_region([461, 739, 532, 762])

    # 遍历templates/bad_cases和templates/bad_cases_1440p目录
    bad_cases_dirs = [
        # "../../templates/bad_cases",
        "../../templates/bad_cases_1440p"
    ]

    for dir_path in bad_cases_dirs:
        print(f"Processing directory: {dir_path}")
        for file_name in os.listdir(dir_path):
            if file_name.endswith(".png"):
                file_path = os.path.join(dir_path, file_name)
                img = cv2.imread(file_path)
                if img is not None:
                    res = ocr.image_to_string(img, thresh=80)
                    # print(f"File: {file_name}, Result: {res}")
                    expected = file_name.split(".")[0].split("_")[0]
                    if expected != res:
                        print(f"file {file_name} detect failed: {res}")
                else:
                    print(f"Failed to read image: {file_name}")

    screenshot = cv2.imread("../../templates/bad_cases_1440p/25612140.png")
    # for _ in range(100):
    #     ocr.image_to_string(screenshot)
    # print("fps:", 100 / (time.time() - start))
