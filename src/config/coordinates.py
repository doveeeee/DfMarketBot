# -*- coding: utf-8 -*-
"""
坐标配置
"""
from typing import Dict


class CoordinateConfig:
    """坐标配置"""

    BASE_WIDTH = 2560
    BASE_HEIGHT = 1440

    # 坐标配置
    COORDINATES = {
        "price_detection": {
            "convertible": [2179 / 2560, 1078 / 1440, 2308 / 2560, 1102 / 1440],
            "non_convertible": [2179 / 2560, 1156 / 1440, 2308 / 2560, 1178 / 1440],
        },
        "balance_active": [2200 / 2560, 70 / 1440],
        "balance_detection": [1912 / 2560, 360 / 1440, 2324 / 2560, 390 / 1440],
        "buy_buttons": {
            "convertible_max": [0.9085, 0.7222],
            "convertible_min": [0.8095, 0.7222],
            "non_convertible_max": [2329 / 2560, 1112 / 1440],
            "non_convertible_min": [2059 / 2560, 1112 / 1440],
            "convertible_buy": [2189 / 2560, 0.7979],
            "non_convertible_buy": [2186 / 2560, 1225 / 1440],
        },
        "rolling_mode": {
            "options": [
                [244 / 2560, 404 / 1440],
                [117 / 2560, 500 / 1440],
                [117 / 2560, 591 / 1440],
                [117 / 2560, 690 / 1440],
            ],
            "price_area": [2128 / 2560, 1133 / 1440, 2413 / 2560, 1191 / 1440],
            "buy_button": [2245 / 2560, 1165 / 1440],
            "failure_check": [418 / 2560, 280 / 1440, 867 / 2560, 387 / 1440],
            # 检测是否点入装备页面导致卡死
            "stuck_check": [2180 / 2560, 1120 / 1440, 2291 / 2560, 1165 / 1440],
            # 检测是否没有L按下配装按钮导致卡死
            "stuck_check2_teqingchu": [128 / 2560, 1380 / 1440, 405 / 2560, 1420 / 1440],
            "stuck_check2_equipment_scheme": [347 / 2560, 1379 / 1440, 570 / 2560, 1430 / 1440],
            "xing_qian_bei_zhan_area": [2110 / 2560, 1264 / 1440, 2310 / 2560, 1314 / 1440],
            "start_action_area": [2120 / 2560, 889 / 1440, 2296 / 2560, 935 / 1440],
            "pei_zhuang_area": [2017 / 2560, 1266 / 1440, 2126 / 2560, 1309 / 1440],
            "item_range": [84 / 2560, 84 / 1440],
            # 仓库前10行为等待售卖区域
            "wait_sell_item_area": [1651 / 2560, 177 / 1440, 2416 / 2560, 1028 / 1440],
            "enter_storage": [427 / 2560, 76 / 1440],
            "transfer_all": [390 / 2560, 1403 / 1440],
            # 物品右键点击后鼠标位置到出售按钮位置的偏移量
            "item_sell_offset": [77 / 2560, 147 / 1440],
            "sell_button": [1965 / 2560, 939 / 1440],
            # 快速售卖指定点击位置坐标
            "btn_quickSell_area": [1965 / 2560, 939 / 1440],
            "sell_return_button": [1280 / 2560, 1258 / 1440],
            # 当前最小价格的柱子所在位置
            "min_sell_price_button": [655 / 2560, 904 / 1440],
            # 用于检测当前最小价格的区域
            "min_sell_price_area": [615 / 2560, 986 / 1440, 710 / 2560, 1016 / 1440],
            # 用于检测当前第二小价格的区域(第二根柱子)
            "second_min_sell_price_area": [777 / 2560, 986 / 1440, 886 / 2560, 1013 / 1440],
            # 倒数第二根柱子指定点击位置
            "fast_sell_price_button": [1165 / 2560, 700 / 1440],
            # 检测最小价格数量的区域
            "min_sell_price_count_area": [575 / 2560, 500 / 1440, 720 / 2560, 985 / 1440],
            "sell_count_area": [1570 / 2560, 680 / 1440, 1760 / 2560, 710 / 1440],
            "sell_num_left": [1563 / 2560, 749 / 1440],
            "sell_num_right": [1937 / 2560, 749 / 1440],
            "sell_price_text": [1748 / 2560, 860 / 1440],
            "sell_full": [1948 / 2560, 678 / 1440, 2027 / 2560, 711 / 1440],
            "expected_revenue_area": [1642 / 2560, 910 / 1440, 1920 / 2560, 950 / 1440],
            "sell_detail_button": [1867 / 2560, 929 / 1440],
            "total_sell_price_area": [1844 / 2560, 707 / 1440, 2010 / 2560, 740 / 1440],
            # 上架按钮
            "final_sell_button": [1757 / 2560, 994 / 1440],
            # 邮件按钮
            "mail_button": [2313 / 2560, 73 / 1440],
            "mail_trade_button": [598 / 2560, 100 / 1440],
            "mail_get_button": [256 / 2560, 1270 / 1440],
            # 切换大战场相关
            # 切换大战场模式按钮
            "battlefield_mode_button": [336 / 2560, 637 / 1440],
            # 切换烽火行动模式按钮
            "tarkov_mode_button": [336 / 2560, 384 / 1440],
            # 行前备战按钮
            "prepare_equipment_button": [2100 / 2560, 1291 / 1440],
            # 选择零号大坝地图按钮
            "zero_dam_button": [1091 / 2560, 351 / 1440],
            # 开始行动按钮
            "start_action_button": [2198 / 2560, 911 / 1440],
        },
        "app_ver_area": [1663 / 2560, 85 / 1440, 1766 / 2560, 135 / 1440],
        # 进入游戏
        "enter_game": [744 / 2560, 584 / 1440],
    }

    @classmethod
    def restore_coordinates(cls, target_width: int = 2560, target_height: int = 1440) -> Dict:
        """将比例坐标还原为目标分辨率下的绝对像素坐标

        Args:
            target_width: 目标宽度（像素）
            target_height: 目标高度（像素）

        Returns:
            包含绝对像素坐标的配置字典
        """

        def restore_coord(coord):
            # 大于1的认为是绝对坐标，不处理
            if coord[0] > 1 or coord[1] > 1:
                return coord
            if isinstance(coord, list):
                return [int(coord[i] * (target_width if i % 2 == 0 else target_height)) for i in range(len(coord))]
            if isinstance(coord, tuple):
                return tuple(int(coord[i] * (target_width if i % 2 == 0 else target_height)) for i in range(len(coord)))
            return coord

        # 递归处理所有坐标
        def restore_dict(d):
            result = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    result[k] = restore_dict(v)
                elif isinstance(v, list):
                    if all(isinstance(item, (int, float)) for item in v):
                        result[k] = restore_coord(v)
                    else:
                        result[k] = [restore_coord(item) if isinstance(item, (list, tuple)) else item for item in v]
                else:
                    result[k] = v
            return result

        return restore_dict(cls.COORDINATES)


if __name__ == "__main__":
    res = CoordinateConfig.restore_coordinates(2560, 1440)
    print(CoordinateConfig.COORDINATES)
    print(res)
