# -*- coding: utf-8 -*-
"""
价格检测服务
"""
import re
import time
from abc import abstractmethod
from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    from src.config.coordinates import CoordinateConfig
    from src.core.exceptions import BalanceDetectionException, PriceDetectionException
    from src.core.interfaces import IOCREngine, IPriceDetector
    from src.infrastructure.screen_capture import ScreenCapture
except ImportError:
    from ..config.coordinates import CoordinateConfig
    from ..core.exceptions import BalanceDetectionException, PriceDetectionException
    from ..core.interfaces import IOCREngine, IPriceDetector
    from ..infrastructure.screen_capture import ScreenCapture


class PriceDetector(IPriceDetector):
    """价格检测器基类"""

    def __init__(self, screen_capture: ScreenCapture, ocr_engine: IOCREngine):
        self.screen_capture = screen_capture
        self.ocr_engine = ocr_engine
        self.coordinates = CoordinateConfig.restore_coordinates(screen_capture.width, screen_capture.height)

    @abstractmethod
    def get_detection_coordinates(self) -> List[float]:
        """获取价格检测坐标 - 由子类实现"""
        raise NotImplementedError("not implemented")

    def _detect_value(
            self, coords: List[float], value_name: str = "价格", max_attempts: int = 30, abnormal_value=100,
            binarize=True, font="", thresh=127
    ) -> int:
        """通用的数值检测逻辑"""
        for _ in range(max_attempts):
            screenshot = self.screen_capture.capture_region(coords)
            value = self._extract_number(screenshot, binarize, font, thresh)
            if value is not None:
                if value_name == "价格" and value < abnormal_value:  # 仅对价格进行异常过滤
                    print(f"检测{value_name}({value})异常，跳过检测")
                    continue
                print(f"detected {value_name}:", value)
                return value

            time.sleep(0.005)

        raise PriceDetectionException(f"{value_name}检测失败")

    def detect_price(self) -> int:
        """检测当前物品价格 - 使用模板方法模式"""
        try:
            coords = self.get_detection_coordinates()
            return self._detect_value(coords)
        except Exception as e:
            raise PriceDetectionException(f"价格检测异常: {e}") from e

    def detect_balance(self) -> Optional[int]:
        """检测当前哈夫币余额"""
        try:
            coords = self.coordinates["balance_detection"]
            return self._detect_value(coords, "余额")
        except Exception as e:
            raise BalanceDetectionException(f"余额检测异常: {e}") from e

    def _extract_number(self, image: np.ndarray, binarize=True, font="", thresh=127) -> Optional[int]:
        """从图像中提取数字"""
        try:
            text = self.ocr_engine.image_to_string(image, binarize, font, thresh)
            # 只保留数字
            numbers = re.sub(r"[^0-9]", "", text)
            return int(numbers) if numbers else None
        except Exception as e:
            print(f"提取数字失败: {e}")
            return None


class HoardingModeDetector(PriceDetector):
    """屯仓模式检测器"""

    def __init__(self, screen_capture: ScreenCapture, ocr_engine: IOCREngine, item_convertible: bool = False):
        super().__init__(screen_capture, ocr_engine)
        self.item_convertible = item_convertible

    def get_detection_coordinates(self) -> List[float]:
        """获取价格检测坐标"""
        if self.item_convertible:
            return self.coordinates["price_detection"]["convertible"]
        return self.coordinates["price_detection"]["non_convertible"]


class RollingModeDetector(PriceDetector):
    """滚仓模式检测器"""

    def get_detection_coordinates(self) -> List[float]:
        """获取价格检测坐标"""
        return self.coordinates["rolling_mode"]["price_area"]

    def check_purchase_failure(self) -> bool:
        """检查购买是否失败"""
        return self._match_template("failure_check", "option_failed")

    def check_stuck(self) -> bool:
        """检查循环是否卡死"""
        return self._match_template("stuck_check", "equipment")

    def check_stuck2(self) -> bool:
        """检查循环是否卡死"""
        return self._match_template("stuck_check2_teqingchu", "enter_teqingchu") and not self._match_template(
            "stuck_check2_equipment_scheme", "equipment_scheme"
        )

    def is_in_game_lobby(self) -> bool:
        """检查循环是否卡死"""
        return self._match_template("xing_qian_bei_zhan_area", "xing_qian_bei_zhan") or self.pei_zhuang_enabled()

    def pei_zhuang_enabled(self):
        return self._match_template("pei_zhuang_area", "pei_zhuang")

    def is_clicked_map(self) -> bool:
        """检查循环是否卡死"""
        return self._match_template("start_action_area", "start_action")

    def check_sell_window(self) -> bool:
        """检查仓库出售页面是不是无法售卖（三角洲bug）"""
        return self._match_template("failure_check", "sell")

    def _match_template(self, coords: str, template_name: str):
        try:
            coords = self.coordinates["rolling_mode"][coords]
            screenshot = self.screen_capture.capture_region(coords)
            return self.ocr_engine.detect_template(screenshot, template_name)
        except Exception as e:
            print("检测失败:", e)
            return False

    def detect_sellable_item(self):
        width = 9
        length = 10
        color_toleration = 20
        coords = self.coordinates["rolling_mode"]["wait_sell_item_area"]
        item_range = self.coordinates["rolling_mode"]["item_range"]
        item_center = [int(item_range[0] / 2), int(item_range[1] / 2)]
        screenshot = self.screen_capture.capture_region(coords)
        valid_color = [26, 31, 34]
        current_pos = [item_center[0], item_center[1]]
        for i in range(length):
            for j in range(width):
                color = self.ocr_engine.get_pixel_color(screenshot, current_pos[0], current_pos[1])
                if not (
                        valid_color[0] - color_toleration < color[0] < valid_color[0] + color_toleration
                        and valid_color[1] - color_toleration < color[1] < valid_color[1] + color_toleration
                        and valid_color[2] - color_toleration < color[2] < valid_color[2] + color_toleration
                ):
                    print(f"检测到可售卖物品: 第{j}行第{i}个, 颜色: ({color[0]}, {color[1]}, {color[2]})")
                    return [coords[0] + current_pos[0], coords[1] + current_pos[1]]
                current_pos[0] += item_range[0] + 1
            current_pos[0] = item_center[0]
            current_pos[1] += item_range[1] + 1
        return [0, 0]

    def detect_sell_num(self) -> Tuple[int, int]:
        coords = self.coordinates["rolling_mode"]["sell_full"]
        screenshot = self.screen_capture.capture_region(coords)
        res = self.ocr_engine.image_to_string(screenshot)
        if res == "":
            return 0, 0
        if "/" in res:
            res = res.split("/")
            return int(res[0]), int(res[1])
        return int(res[0]), int(res[1:])

    def detect_sell_full(self) -> int:
        cur_num, max_num = self.detect_sell_num()
        # 识别失败时为了防止检测失误，就当拍卖行上架已满，等待下次检测
        return cur_num == 0 and max_num == 0

    def detect_min_sell_price(self) -> int:
        """检测当前售卖的最小价格"""
        return self._detect_area("min_sell_price_area", font="w", thresh=50)

    def detect_second_min_sell_price(self) -> int:
        """检测当前售卖的最小价格"""
        return self._detect_area("second_min_sell_price_area", font="w", thresh=50)

    def detect_min_sell_price_count(self) -> int:
        """检测当前售卖的最小价格"""
        return self._detect_area("min_sell_price_count_area", 0, font="w", thresh=50)

    def detect_expected_revenue(self) -> int:
        """检测当前售卖的期望收益"""
        res = self._detect_area("expected_revenue_area", binarize=False, font="w")
        # 检测器会把售价边上的问号当成7，所以这里特殊处理一下... TODO: 以后再修
        return int((res - 7) / 10) if res % 10 == 7 else res

    def detect_total_sell_price_area(self) -> int:
        """检测当前售卖总价"""
        return self._detect_area("total_sell_price_area", font="w", thresh=60)

    def _detect_area(self, template, abnormal_value=100, binarize=True, font="", thresh=127) -> int:
        """检测模板的区域, 并返回数值"""
        try:
            coords = self.coordinates["rolling_mode"][template]
            return self._detect_value(coords, abnormal_value=abnormal_value, binarize=binarize, font=font, thresh=thresh)
        except Exception as e:
            raise PriceDetectionException(f"价格检测异常: {e}") from e


if __name__ == "__main__":
    from src.infrastructure.ocr_engine import TemplateOCREngine

    sc = ScreenCapture()
    print(sc.width, sc.height)
    ocr = TemplateOCREngine()
    detector = RollingModeDetector(sc, ocr)
    result = detector.is_in_game_lobby()
    print(result)
    # test_res = detector._match_template("stuck_check2_equipment_scheme", "equipment_scheme")
    # print(test_res)
    # test_res = detector._match_template("stuck_check2_teqingchu", "enter_teqingchu")
    # print(test_res)
