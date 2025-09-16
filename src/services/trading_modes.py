# -*- coding: utf-8 -*-
"""
交易模式实现
"""
import datetime
import os
import time
from typing import Dict, Optional, Tuple

import pyautogui

from src.utils.window_helper import bring_window_to_front

try:
    from src.config.trading_config import ItemType, TradingConfig, TradingMode
    from src.core.event_bus import event_bus
    from src.core.exceptions import TradingException
    from src.core.interfaces import IOCREngine, ITradingMode, MarketData
    from src.infrastructure.action_executor import PyAutoGUIActionExecutor as ActionExecutor
    from src.infrastructure.screen_capture import ScreenCapture
    from src.services.detector import HoardingModeDetector, RollingModeDetector
    from src.services.strategy import StrategyFactory
    from src.utils.delay_helper import delay_helper
except ImportError:
    from ..config.trading_config import ItemType, TradingConfig, TradingMode
    from ..core.event_bus import event_bus
    from ..core.exceptions import TradingException
    from ..core.interfaces import IOCREngine, ITradingMode, MarketData
    from ..infrastructure.action_executor import PyAutoGUIActionExecutor as ActionExecutor
    from ..infrastructure.screen_capture import ScreenCapture
    from ..services.detector import HoardingModeDetector, RollingModeDetector
    from ..services.strategy import StrategyFactory
    from ..utils.delay_helper import delay_helper


class HoardingTradingMode(ITradingMode):
    """屯仓模式交易实现"""

    def __init__(self, price_detector: HoardingModeDetector, action_executor: ActionExecutor):
        self.detector = price_detector
        self.action_executor = action_executor
        self.last_balance = None
        self.current_balance = None
        self.last_buy_quantity = 0
        self.current_market_data = None
        self.config = None
        self.strategy = None
        self.refresh_strategy = None
        self.mouse_position = None
        # 统计购买失败信息，超过10次认为仓库已满，退出脚本，目前只支持使用哈夫币计算价格时使用
        self.buy_failed_count = 0
        # 停止标志
        self._should_stop = False

    def initialize(self, config: TradingConfig, **kwargs) -> None:
        """初始化屯仓模式"""
        self.config = config
        factory = StrategyFactory()
        self.strategy = factory.create_strategy(config)
        self.refresh_strategy = factory.create_refresh_strategy(config)
        self._should_stop = False
        delay_helper.reload_config()
        delay_helper.set_mode(TradingMode.HOARDING)

    def stop(self) -> None:
        """停止交易模式"""
        self._should_stop = True
        print("屯仓模式收到停止信号")

    def prepare(self) -> None:
        self.mouse_position = self.action_executor.get_mouse_position()
        self.current_balance = self._detect_balance()
        self._execute_enter()
        delay_helper.sleep("enter_action")

    def execute_cycle(self) -> bool:
        """执行一个屯仓交易周期"""
        try:
            # 检查停止信号
            if self._should_stop:
                print("检测到停止信号，退出交易周期")
                return False

            # 获取当前价格
            current_price = self.detector.detect_price()

            # 获取当前余额（如果需要）
            if self.config.use_balance_calculation and self.last_buy_quantity != 0:
                self.current_balance = self._detect_balance()

            self.current_market_data = MarketData(
                current_price=current_price,
                balance=self.current_balance,
                last_balance=self.last_balance,
                last_buy_quantity=self.last_buy_quantity,
                timestamp=time.time(),
            )

            if (
                self.config.use_balance_calculation
                and self.last_buy_quantity != 0
                and self.last_balance == self.current_balance
            ):
                self.buy_failed_count += 1
            else:
                self.buy_failed_count = 0

            if self.buy_failed_count >= 10:
                print("连续10次购买失败，仓库可能满了，退出购买")
                event_bus.emit_overlay_text_updated("连续10次购买失败，仓库可能满了，退出购买")
                return False

            # 执行交易逻辑
            if self.strategy.should_buy(self.current_market_data):
                print("直接购买")
                # 购买逻辑
                quantity = self.strategy.get_buy_quantity(self.current_market_data)
                self._execute_buy(quantity)
                self.last_buy_quantity = quantity

                if self.config.key_mode:
                    return False  # 钥匙卡模式购买后停止
            elif self.refresh_strategy.should_refresh(self.current_market_data):
                print("刷新购买")
                quantity = self.strategy.get_buy_quantity(self.current_market_data)
                self._execute_buy(quantity)
                self.last_buy_quantity = self.refresh_strategy.get_buy_quantity(self.config)
            elif self.strategy.should_refresh(self.current_market_data):
                print("直接刷新")
                self._execute_refresh()
                self.last_buy_quantity = 0

            # 更新余额
            if self.config.use_balance_calculation:
                self.last_balance = self.current_balance

            return not self._should_stop  # 如果收到停止信号则返回False

        except Exception as e:
            raise TradingException(f"屯仓模式交易失败: {e}") from e

    def _detect_balance(self):
        self.action_executor.move_mouse(self.detector.coordinates["balance_active"])
        return self.detector.detect_balance()

    def _execute_enter(self) -> None:
        self.action_executor.click_position((self.mouse_position.x, self.mouse_position.y))

    def _execute_buy(self, quantity: int) -> None:
        """执行购买操作"""
        if quantity == 0:
            return
        convertible = "" if ItemType(self.config.item_type) == ItemType.CONVERTIBLE else "non_"
        if not self.config.key_mode:
            quantity_pos = "min" if quantity == 31 else "max"
            self.action_executor.click_position(
                self.detector.coordinates["buy_buttons"][f"{convertible}convertible_{quantity_pos}"]
            )
        self.action_executor.click_position(self.detector.coordinates["buy_buttons"][f"{convertible}convertible_buy"])
        print(f"执行购买: 数量={quantity}")

    def _execute_refresh(self) -> None:
        """执行刷新操作"""
        self.action_executor.press_key("esc")
        self._execute_enter()
        delay_helper.sleep("refresh_operation")
        print("执行价格刷新")

    def get_market_data(self) -> Optional[MarketData]:
        """获取当前市场数据"""
        return self.current_market_data


class RollingTradingMode(ITradingMode):
    """滚仓模式交易实现"""
    detector: RollingModeDetector

    current_market_data: MarketData
    config: TradingConfig

    def __init__(self, rolling_detector: RollingModeDetector, action_executor: ActionExecutor):
        self.detector = rolling_detector
        self.action_executor = action_executor
        self.strategy_factory = StrategyFactory()
        self.option_configs = None
        self.last_balance = None
        self.profit = 0
        # 已出售总数
        self.count = 0
        # 停止标志
        self._should_stop = False
        self.loop_count = 0
        self.buy_failed_count = 0
        self.buy_success_count = 0
        self.fail_count = 0

    def initialize(self, config: TradingConfig, **kwargs) -> None:
        """初始化滚仓模式"""
        self.config = config
        self.option_configs = config.rolling_options
        self.last_balance = None
        self._should_stop = False
        self.fail_count = 0
        delay_helper.reload_config()
        delay_helper.set_mode(TradingMode.ROLLING)
        if kwargs.get("profit", None):
            self.profit = kwargs.get("profit")
        if kwargs.get("count", None):
            self.count = kwargs.get("count")

    def stop(self) -> None:
        """停止交易模式"""
        self._should_stop = True
        print("滚仓模式收到停止信号")

    def prepare(self) -> None:
        self.last_balance = self._detect_balance()
        print("===" * 30)
        print("初始化成功，当前余额:", self.last_balance)
        self.append_to_sell_log("===" * 30)
        self.append_to_sell_log(f"初始化成功，当前余额: {self.last_balance}")
        event_bus.emit_overlay_text_updated(f"初始化成功，当前余额: {self.last_balance}")
        delay_helper.sleep("initialization")

    def execute_cycle(self) -> bool:
        """执行一个滚仓交易周期"""
        try:
            # 检查停止信号
            if self._should_stop:
                print("检测到停止信号，退出交易周期")
                return False

            # 获取配装配置
            if self.config.rolling_option >= len(self.option_configs):
                return False
            option_config = self.option_configs[self.config.rolling_option]
            if not option_config:
                return False

            if (
                self.config.switch_to_battlefield
                and self.loop_count > 0
                and self.loop_count % self.config.switch_to_battlefield_count == 0
            ):
                time.sleep(1)
                self._switch_to_battlefield_and_return()
                time.sleep(0.5)
            self.loop_count += 1

            target_price = option_config["buy_price"] * option_config["buy_count"]
            min_price = option_config["min_buy_price"] * option_config["buy_count"]

            self._execute_enter()
            delay_helper.sleep("before_option_switch")
            # 切换到指定配装选项
            self._switch_to_option(self.config.rolling_option)
            delay_helper.sleep("after_option_switch")
            current_price = 0
            for i in range(5):
                # 检测价格
                current_price = self.detector.detect_price()
                if current_price > min_price:
                    break
                print(f"价格小于异常价格，重新检测({i}/5)")
                delay_helper.sleep("price_detection_retry")
            # 存储市场数据
            self.current_market_data = MarketData(
                current_price=current_price, balance=None, timestamp=time.time()  # 滚仓模式不检测余额
            )

            print(
                f"滚仓模式: 单价={option_config['buy_price']}, "
                f"数量={option_config['buy_count']}, "
                f"总价={target_price}, 最低价={min_price}, "
                f"当前价={current_price}, 循环次数: {self.loop_count}"
            )
            event_bus.emit_overlay_text_updated(
                f"当前价格[{current_price}, {current_price / option_config['buy_count']}] 目标价格[{target_price}] "
                f"总盈利[{self.profit}] 总购买数[{self.count}] 循环次数[{self.loop_count}] "
                f"购买成功[{self.buy_success_count}] 购买失败[{self.buy_failed_count}]"
            )

            # 执行交易决策
            if min_price < current_price <= target_price:
                delay_helper.sleep("before_buy")
                if self.config.second_detect:
                    delay_helper.sleep("second_price_detection_retry")
                    second_detect_price = self.detector.detect_price()
                    if min_price < second_detect_price <= target_price:
                        event_bus.emit_overlay_text_updated(
                            f"二次检测成功({current_price}, {second_detect_price})，执行购买"
                        )
                        # 购买
                        self._execute_buy()
                    else:
                        event_bus.emit_overlay_text_updated(
                            f"二次检测失败({current_price}, {second_detect_price})，跳过购买"
                        )
                        self._execute_refresh()
                        self.fail_count = 0
                        return not self._should_stop
                else:
                    self._execute_buy()

                # 检查购买是否成功
                delay_helper.sleep("after_buy")
                print("执行检测购买失败")
                if self.detector.check_purchase_failure():
                    print("购买失败！")
                    self._execute_refresh()
                    delay_helper.sleep("after_check_purchase_failure")
                    cur_balance = self._detect_balance()
                    if cur_balance == self.last_balance:
                        print("购买失败！")
                        self.buy_failed_count += 1
                        self._update_statistics()
                        delay_helper.sleep("after_buy_failed")
                        self.fail_count = 0
                        return True
                    print("部分购买成功，执行售卖")
                else:
                    print("购买成功！")
                self.buy_success_count += 1
                delay_helper.sleep("after_buy_success")
                cur_balance = self._detect_balance()
                cost = self.last_balance - cur_balance
                self.profit -= cost
                self.append_to_sell_log(f"购买成功, 总花费: {cost}, 当前盈利: {self.profit}")
                event_bus.emit_overlay_text_updated(f"购买成功, 总花费[{cost}], 当前盈利: {self.profit}")

                # current = time.localtime()
                # if current.tm_hour == 1 and current.tm_min >= 55:
                #     return False

                # 检查停止信号再执行售卖
                if self._should_stop or not self.config.auto_sell:
                    return False

                self._execute_auto_sell(cost)

                # 检查停止信号
                if self._should_stop:
                    return False

                # 自动售卖结束时已经有1s间隔了，这里延迟可以不用太高
                delay_helper.sleep("before_get_mail")
                self._execute_get_mail_half_coin()
                delay_helper.sleep("after_get_mail")
                self._execute_refresh()
                delay_helper.sleep("buy_success_refresh_final")
                self.last_balance = self._detect_balance()
                event_bus.emit_overlay_text_updated(
                    f"当前价格[{current_price}, {current_price / option_config['buy_count']}] 总购买数[{self.count}]"
                )
                delay_helper.sleep("after_get_mail_and_detect_balance")
            else:
                # 刷新
                self._execute_refresh()

            self._update_statistics()
            self.fail_count = 0
            return not self._should_stop  # 如果收到停止信号则返回False

        except Exception as e:
            if self.detector.check_stuck():
                print("检测到点入装备界面，尝试脱离卡死")
                self._execute_refresh()
            elif self.detector.is_in_game_lobby():
                print("检测到进入游戏大厅，尝试脱离卡死")
                self._enter_action_window(self.detector.pei_zhuang_enabled())
            elif self.detector.check_stuck2():
                print("检测到没有L按钮进入配装界面，尝试修复")
                # 没有L按钮进入配装界面
                self._execute_refresh()
                time.sleep(1)
                self._enter_action_window()
            self.fail_count += 1
            if self.fail_count > 10 and not self.detector.detect_window_exist()[0]:
                print("检测到游戏闪退，尝试重启")
                self.append_to_sell_log("游戏闪退，尝试重启")
                if not self._restart_game():
                    return False
                self.append_to_sell_log("游戏重启成功！")
                raise TradingException("游戏闪退！") from e
            raise TradingException(f"滚仓模式交易失败({self.fail_count + 1}): {e}") from e

    def _update_statistics(self):
        self.current_market_data.profit = self.profit
        self.current_market_data.count = self.count

    def _execute_enter(self):
        self.action_executor.press_key("l")

    def _switch_to_option(self, option_index: int) -> None:
        """切换到指定配装选项"""
        coordinates = self.detector.coordinates["rolling_mode"]["options"]
        if 0 <= option_index < len(coordinates):
            self.action_executor.click_position(coordinates[option_index])

    def _execute_buy(self) -> None:
        """执行购买操作"""
        coordinates = self.detector.coordinates["rolling_mode"]["buy_button"]
        self.action_executor.click_position(coordinates)

    def _execute_refresh(self) -> None:
        """执行刷新操作"""
        print("execute refresh")
        self.action_executor.press_key("esc")
        delay_helper.sleep("after_refresh")

    def _execute_auto_sell(self, cost=0):
        """执行自动售卖流程"""
        self._enter_storage_and_transfer()
        sell_results = self._execute_sell_cycles(cost)
        self._log_final_sell_results(sell_results, cost)

    def _enter_storage_and_transfer(self):
        """进入仓库并转移物品"""
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["enter_storage"])
        delay_helper.sleep("after_enter_storage")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["transfer_all"])
        delay_helper.sleep("after_transfer_all")

    def _execute_sell_cycles(self, cost: float) -> Dict[str, any]:
        """执行售卖循环"""
        sell_time = 0
        sell_ratios = [0.33, 0.5, 1.0]
        total_profit = 0
        total_count = 0
        cycle_results = []

        while sell_time < len(sell_ratios):
            # 检查停止信号
            if self._should_stop:
                print(f"在第{sell_time + 1}轮售卖前收到停止信号，退出售卖循环")
                event_bus.emit_overlay_text_updated(f"在第{sell_time + 1}轮售卖前收到停止信号，退出售卖循环")
                break

            result = self._execute_single_sell_cycle(sell_time, sell_ratios[sell_time])
            if not result["success"]:
                time.sleep(1)
                if result["message"] == "无可售卖物品":
                    break
                continue

            total_profit += result["revenue"]
            total_count += result["count"]
            cycle_results.append(result)
            sell_time += 1

        return {"total_profit": total_profit, "total_count": total_count, "cycles": cycle_results}

    def _execute_single_sell_cycle(self, cycle_index: int, sell_ratio: float) -> Dict[str, any]:
        """执行单个售卖循环"""
        if self._should_stop:
            return {"success": False, "message": "收到停止信号"}
        try:
            # 检测可售卖物品
            item_pos = self.detector.detect_sellable_item()
            if item_pos[0] == 0 and item_pos[1] == 0:
                return {"success": False, "message": "无可售卖物品"}

            # 执行售卖操作
            sell_info = self._perform_sell_operation(item_pos, sell_ratio, cycle_index)

            # 更新统计数据
            self.profit += sell_info["revenue"]
            self.count += sell_info["count"]

            return {
                "success": True,
                "revenue": sell_info["revenue"],
                "count": sell_info["count"],
                "price": sell_info["price"],
                "message": "",
            }

        except Exception as e:
            print(f"售卖失败111：{str(e)}")
            return {"success": False, "message": str(e)}

    def _perform_sell_operation(self, item_pos: Tuple[int, int], sell_ratio: float, cycle_index: int) -> Dict[str, any]:
        """执行单个售卖操作"""
        if self._should_stop:
            return {}
        sell_pos = (
            item_pos[0] + self.detector.coordinates["rolling_mode"]["item_sell_offset"][0],
            item_pos[1] + self.detector.coordinates["rolling_mode"]["item_sell_offset"][1],
        )

        # 进入售卖界面并处理可能的卡顿
        self._enter_sell_interface_with_retry(item_pos, sell_pos)

        # 设置售卖价格
        min_sell_price = self._set_sell_price(sell_ratio, cycle_index, fast_sell=self.config.fast_sell)

        # 获取售卖信息并确认
        return self._confirm_sell_transaction(cycle_index, min_sell_price)

    def _enter_sell_interface_with_retry(self, item_pos: Tuple[int, int], sell_pos: Tuple[int, int]):
        """进入售卖界面，带重试机制"""
        max_retries = 10
        for attempt in range(max_retries):
            try:
                if self._should_stop:
                    return
                self._click_sell_item(item_pos, sell_pos)
                if self._wait_for_sell_window():
                    self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["sell_button"])
                    delay_helper.sleep("after_sell_button_click")
                    return

                # 处理卡顿
                print(f"出售按钮没有按动，尝试解除卡顿 (尝试 {attempt + 1}/{max_retries})")
                event_bus.emit_overlay_text_updated(
                    f"出售按钮没有按动，尝试解除卡顿 (尝试 {attempt + 1}/{max_retries})"
                )
                self._resolve_sell_stuck()

            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)

    def _click_sell_item(self, item_pos: Tuple[int, int], sell_pos: Tuple[int, int]):
        """点击售卖物品"""
        # self.action_executor.move_mouse(item_pos)
        # delay_helper.sleep("after_move_to_sell_item")
        # self.action_executor.click_position(item_pos, right_click=True)
        # delay_helper.sleep("after_right_click_sell_item")
        # self.action_executor.click_position(sell_pos)
        self.action_executor.move_mouse(item_pos)
        delay_helper.sleep("after_move_to_sell_item")
        self.action_executor.multi_key_press("alt", "d")

    def _wait_for_sell_window(self) -> bool:
        """等待售卖窗口出现"""
        delay_helper.sleep("sell_window_wait")
        return self.detector.check_sell_window()

    def _resolve_sell_stuck(self):
        """解决售卖卡顿"""
        self.action_executor.press_key("esc")
        delay_helper.sleep("resolve_sell_stuck")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["enter_storage"])
        delay_helper.sleep("resolve_sell_stuck")

    def _get_fast_sell_threshold(self) -> int:
        """获取当前配装的快速售卖阈值"""
        # 检查配置和选项的有效性
        if (
            not self.option_configs
            or self.config.rolling_option < 0
            or self.config.rolling_option >= len(self.option_configs)
        ):
            return 0  # 默认总是启用快速售卖

        current_option = self.option_configs[self.config.rolling_option]
        return current_option.get("fast_sell_threshold", 0)

    def _get_min_sell_price(self) -> int:
        """获取当前配装的最低售卖价格"""
        current_option = self.option_configs[self.config.rolling_option]
        return current_option["min_sell_price"]

    def _set_sell_price(self, sell_ratio: float, cycle_index: int, fast_sell=False) -> int:
        """设置售卖价格"""
        if self._should_stop:
            return 0
        min_sell_pos = self.detector.coordinates["rolling_mode"]["sell_num_left"]
        sell_num_slice_length = self.detector.coordinates["rolling_mode"]["sell_num_right"][0] - min_sell_pos[0]

        sell_x = min_sell_pos[0] + sell_num_slice_length * sell_ratio
        sell_y = min_sell_pos[1]

        min_sell_price = self.detector.detect_min_sell_price()
        second_min_sell_price = self.detector.detect_second_min_sell_price()
        min_sell_price_count = self.detector.detect_min_sell_price_count()

        # 使用当前配装的最低售卖价格
        config_min_sell_price = self._get_min_sell_price()
        print(f"detect min_sell_price: {min_sell_price}, config: {config_min_sell_price}")
        if config_min_sell_price > 0 and min_sell_price < config_min_sell_price:
            print(f"{min_sell_price}小于最小卖价{config_min_sell_price}，跳过售卖")
            event_bus.emit_overlay_text_updated(f"{min_sell_price}小于最小卖价{config_min_sell_price}，跳过售卖")
            self._execute_refresh()
            time.sleep(0.1)
            self._execute_refresh()
            raise ValueError(f"{min_sell_price}小于最小卖价{config_min_sell_price}")
        # 使用当前配装的快速售卖阈值
        fast_sell_threshold = self._get_fast_sell_threshold()

        if fast_sell and min_sell_price > 0 and min_sell_price_count > fast_sell_threshold:
            # 点击售价输入框
            self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["sell_price_text"])
            delay_helper.sleep("after_sell_price_text_click")

            # 全选输入框内容
            self.action_executor.multi_key_press("ctrl", "a")
            delay_helper.sleep("after_select_sell_text_price")

            # 将售卖价格设置为1
            self.action_executor.type_text('1')
            delay_helper.sleep("after_select_sell_text_price")

            # 快速售卖指定点击位置
            self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["btn_quickSell_area"])
            delay_helper.sleep("after_sell_price_text_click")

            # 点击倒数第二根价格柱子获得最高卖价
            self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["fast_sell_price_button"])
            delay_helper.sleep("after_sell_price_text_click")

            # 获取当前售卖价格
            price_area_coords = self.detector.coordinates["rolling_mode"]["sell_price_text_area"]
            min_sell_price = self.detector._detect_value(price_area_coords, binarize=True,
                                                         thresh=127, font='w')
            delay_helper.sleep("after_sell_price_text_click")

        else:
            self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["min_sell_price_button"])
        delay_helper.sleep("after_set_sell_price")
        self.action_executor.click_position((sell_x, sell_y))
        delay_helper.sleep("after_sell_finish")
        return min_sell_price

    def _confirm_sell_transaction(self, sell_time: int, min_sell_price=0) -> Dict[str, any]:
        """确认售卖交易"""
        if self._should_stop:
            return {}
        # 检测售卖数量
        cur_num, max_num = self.detector.detect_sell_num()
        if cur_num > max_num:
            self.action_executor.press_key("esc")
            delay_helper.sleep("after_sale_column_full")
            raise ValueError("售卖数量超出限制")

        # 获取售卖信息
        if min_sell_price <= 0:
            min_sell_price = self.detector.detect_min_sell_price()
        expected_revenue = self.detector.detect_expected_revenue()

        self.action_executor.move_mouse(self.detector.coordinates["rolling_mode"]["sell_detail_button"])
        delay_helper.sleep("after_move_to_sell_detail")

        total_sell_price = self.detector.detect_total_sell_price_area()
        count = int(total_sell_price / min_sell_price) if min_sell_price > 0 else 0

        # 确认售卖
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["final_sell_button"])
        delay_helper.sleep("after_sell_finish")

        # 记录售卖日志
        self.append_to_sell_log(
            f"出售成功, 单价: {min_sell_price}, 数量: {count}, 总价: {total_sell_price}, "
            f"预期收入: {expected_revenue}"
        )
        event_bus.emit_overlay_text_updated(
            f"第{sell_time + 1}轮售卖成功, 单价: {min_sell_price}, "
            f"数量: {count}, 总价: {total_sell_price}, 预期收入: {expected_revenue}"
        )

        return {"revenue": expected_revenue, "count": count, "price": min_sell_price}

    def _log_final_sell_results(self, sell_results: Dict[str, any], cost: float):
        """记录最终售卖结果"""
        total_profit = sell_results.get("total_profit", 0)
        total_count = sell_results.get("total_count", 0)
        cur_profit = total_profit

        self.append_to_sell_log(
            f"本轮售卖完成, 本轮盈利: {cur_profit - cost}, 本轮售卖: {total_count}个, 购买均价: {cost / total_count}"
            f"当前总盈利: {self.profit}, 当前售卖总量: {self.count}"
        )
        event_bus.emit_overlay_text_updated(
            f"本轮售卖完成, 本轮盈利: {cur_profit - cost}, 本轮售卖: {total_count}个, 购买均价: {cost / total_count}"
        )

    def _execute_get_mail_half_coin(self):
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["mail_button"])
        delay_helper.sleep("after_mail_button_click")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["mail_trade_button"])
        delay_helper.sleep("after_mail_trade_click")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["mail_get_button"])
        delay_helper.sleep("after_mail_get_click")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["mail_get_button"])
        delay_helper.sleep("after_confirm_mail_click")
        self.action_executor.press_key("esc")

    def _switch_to_battlefield_and_return(self):
        """切换到大战场模式解除卡顿，再切回来"""
        self._execute_refresh()
        delay_helper.sleep("before_open_mode_select_menu_tarkov_mode")
        self._execute_refresh()
        delay_helper.sleep("before_select_mode")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["battlefield_mode_button"])
        delay_helper.sleep("before_open_mode_select_menu_battlefield_mode")
        for _ in range(3):
            self.action_executor.press_key(" ")
            time.sleep(0.5)
        self._execute_refresh()
        delay_helper.sleep("before_select_mode")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["tarkov_mode_button"])
        delay_helper.sleep("before_select_map")
        self._enter_action_window()

    def _enter_action_window(self, fast_enter_button=False):
        """
        从主界面进入到行动界面
        :param fast_enter_button: 是否有快速配装按钮
        :return:
        """
        if not fast_enter_button:
            self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["prepare_equipment_button"])
            delay_helper.sleep("before_select_zero_dam")
            if not self.detector.is_clicked_map():
                self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["zero_dam_button"])
            delay_helper.sleep("before_start_action")
        self.action_executor.click_position(self.detector.coordinates["rolling_mode"]["start_action_button"])

    def get_market_data(self) -> Optional[MarketData]:
        """获取当前市场数据"""
        return self.current_market_data

    def _detect_balance(self):
        self.action_executor.move_mouse(self.detector.coordinates["balance_active"])
        delay_helper.sleep("balance_detection")
        return self.detector.detect_balance()

    def append_to_sell_log(self, content, path="sell.log"):
        """
        追加内容到当前目录下的sell.log文件中

        参数:
            content (str): 要追加写入的内容

        返回:
            bool: 成功返回True，失败返回False
        """
        try:
            with open(path, "a", encoding="utf-8") as f:
                current_time = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
                f.write(f"{current_time} {content}\n")  # 自动添加换行符
            return True
        except Exception as e:
            print(f"写入sell.log文件失败: {e}")
            return False

    def _restart_game(self):
        for _ in range(10):
            exists, hwnd = self.detector.detect_window_exist("WeGame")
            if not exists:
                print("游戏闪退，且wegame不在前台，等待wegame出现...")
                os.system("start wegame://")
                time.sleep(10)
                continue
            bring_window_to_front(hwnd)
            time.sleep(1)
            x, y = self.detector.find_game_start_button()
            if x == 0 and y == 0:
                print("游戏闪退，找到wegame窗口，但启动按钮未找到")
                continue
            time.sleep(0.3)
            self.action_executor.click_position((x, y))
            for _ in range(18):
                if not self.detector.check_game_start():
                    print("等待游戏启动...")
                    time.sleep(10)
                    continue
                print(self.detector.coordinates["enter_game"])
                # 截全屏时鼠标会挪到左上角，进而触发pyautogui的失效保护，所以这里要临时禁用一下
                pyautogui.FAILSAFE = False
                self.action_executor.click_position(self.detector.coordinates["enter_game"])
                pyautogui.FAILSAFE = True
                time.sleep(1)
                for _ in range(3):
                    self.action_executor.press_key(" ")
                    time.sleep(1)
                delay_helper.sleep("after_enter_game_home")
                self.action_executor.press_key("tab")
                time.sleep(1)
                self._enter_action_window()
                return True
            print("游戏3分钟没有启动成功，退出循环")
            self.append_to_sell_log("游戏3分钟没有启动成功，退出循环")
            return False
        self.append_to_sell_log("游戏闪退，且wegame不在前台，退出循环")
        return False


class TradingModeFactory:
    """交易模式工厂"""

    @staticmethod
    def create_mode(
        config: TradingConfig,
        ocr_engine: IOCREngine,
        screen_capture: ScreenCapture,
        action_executor: ActionExecutor,
    ) -> ITradingMode:
        """根据类型创建交易模式"""
        if config.trading_mode == TradingMode.HOARDING:
            price_detector = HoardingModeDetector(
                screen_capture, ocr_engine, ItemType(config.item_type) == ItemType.CONVERTIBLE
            )
            mode = HoardingTradingMode(price_detector, action_executor)
        elif config.trading_mode == TradingMode.ROLLING:
            price_detector = RollingModeDetector(screen_capture, ocr_engine)
            mode = RollingTradingMode(price_detector, action_executor)
        else:
            raise ValueError(f"不支持的交易模式: {config.trading_mode}")
        return mode


if __name__ == "__main__":
    from src.infrastructure.ocr_engine import TemplateOCREngine

    sc = ScreenCapture()
    ocr = TemplateOCREngine()
    detector = RollingModeDetector(sc, ocr)
    executor = ActionExecutor()
    test_mode = RollingTradingMode(detector, executor)
    test_mode.initialize(TradingConfig(), profit=300000, count=123456)
    # res = test_mode.detector.detect_min_sell_price()
    # res = test_mode.detector.detect_second_min_sell_price()
    # res = test_mode.detector.detect_min_sell_price_count()
    # 售卖右侧区域
    # res = test_mode.detector.detect_expected_revenue()
    # res = test_mode.detector.detect_sell_num()
    res = test_mode.detector.detect_price()
    print(res)
