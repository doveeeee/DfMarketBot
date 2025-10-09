# -*- coding: utf-8 -*-
"""
交易服务 - 核心业务逻辑整合
"""
from typing import Optional

from ..core.exceptions import TradingException, WindowDetectionException, WindowNotFoundException, WindowSizeException
from ..core.interfaces import ITradingService, MarketData, TradingConfig
from ..infrastructure.action_executor import ActionExecutorFactory
from ..infrastructure.ocr_engine import OCREngineFactory
from ..infrastructure.screen_capture import ScreenCapture
from ..services.trading_modes import TradingModeFactory
from ..services.window_service import WindowService


class TradingService(ITradingService):
    """交易服务实现"""

    def __init__(self):
        # 初始化窗口服务
        self.window_service = WindowService()
        if not self.window_service.detect_game_window():
            print("请先打开游戏！")
            raise WindowNotFoundException("未检测到游戏窗口")
        resolution = self.window_service.get_window_size()
        # 初始化基础设施
        self.screen_capture = ScreenCapture(resolution)
        self.ocr_engine = OCREngineFactory.create_engine("template", resolution=resolution)
        self.action_executor = ActionExecutorFactory.create_executor("pyautogui")

        # 初始化交易模式
        self.current_mode = None
        self.current_config = None

        self.profit = 0
        self.count = 0
        self.total_count = 0
        self.cost = 0
        self.detail = {}

    def initialize(self, config: TradingConfig) -> None:
        """初始化交易服务"""
        try:
            # 检查基础设施是否可用
            self._check_infrastructure()

            # 自动检测窗口模式
            self._initialize_window_mode()

            # 切换交易模式
            self._switch_mode(config)

            # 更新当前配置
            self.current_config = config
            print("交易服务初始化成功")

        except (WindowDetectionException, WindowNotFoundException, WindowSizeException) as e:
            # 窗口相关异常，提供用户友好的错误信息
            raise TradingException(f"窗口检测失败: {e}") from e
        except Exception as e:
            raise TradingException(f"交易服务初始化失败: {e}") from e

    def prepare(self) -> None:
        try:
            self.current_mode.prepare()
        except Exception as e:
            raise TradingException(f"交易服务准备失败: {e}") from e

    def execute_cycle(self) -> bool:
        """执行一个交易周期"""
        try:
            # 执行交易周期
            res = self.current_mode.execute_cycle()
            market_data = self.get_market_data()
            self.profit = market_data.profit
            self.count = market_data.count
            self.total_count = market_data.total_count
            self.cost = market_data.cost
            self.detail = market_data.detail
            return res

        except Exception as e:
            raise TradingException(f"交易周期执行失败: {e}") from e

    def get_market_data(self) -> Optional[MarketData]:
        """获取当前市场数据"""
        if self.current_mode is not None:
            return self.current_mode.get_market_data()
        return None

    def stop(self) -> None:
        """停止交易服务"""
        if self.current_mode and hasattr(self.current_mode, "stop"):
            self.current_mode.stop()

        # 清理窗口服务
        if self.window_service:
            self.window_service.reset()

        # 清除窗口偏移设置
        self._clear_window_offsets()

        self.current_mode = None
        self.current_config = None

    def get_window_service(self) -> WindowService:
        """获取窗口服务实例"""
        return self.window_service

    def is_window_mode_detected(self) -> bool:
        """检查是否检测到窗口模式"""
        return self.window_service is not None and self.window_service.current_window is not None

    def get_window_info(self):
        """获取当前窗口信息"""
        if self.window_service:
            return self.window_service.get_window_info()
        return None

    def _check_infrastructure(self) -> None:
        """检查基础设施是否可用"""
        # 检查屏幕捕获
        try:
            test_image = self.screen_capture.capture_region([0, 0, 256, 1440])
            if test_image is None or test_image.size == 0:
                raise TradingException("屏幕捕获失败")
        except Exception as e:
            raise TradingException(f"屏幕捕获不可用: {e}") from e

        # 检查OCR引擎
        try:
            test_image = self.screen_capture.capture_region([0, 0, 256, 144])
            self.ocr_engine.image_to_string(test_image)
        except Exception as e:
            raise TradingException(f"OCR引擎不可用: {e}") from e

        # 检查动作执行器
        try:
            self.action_executor.get_mouse_position()
        except Exception as e:
            raise TradingException(f"动作执行器不可用: {e}") from e

    def _initialize_window_mode(self) -> None:
        """自动检测窗口模式"""
        try:
            print("开始自动检测游戏窗口模式...")

            # 尝试检测游戏窗口
            if not self.window_service.detect_game_window():
                print("未检测到游戏窗口，使用全屏模式")
                self._clear_window_offsets()
                return

            # 检查是否为真正的窗口模式（有边框）
            if not self.window_service.is_game_windowed():
                print("检测到游戏运行在全屏或无边框模式，使用全屏坐标")
                self._clear_window_offsets()
                # 重置窗口服务，因为不需要窗口偏移
                self.window_service.reset()
                return

            # 获取窗口偏移和尺寸
            window_offset = self.window_service.get_window_offset()
            window_size = self.window_service.get_window_size()

            print(f"检测到窗口模式 - 偏移: {window_offset}, 尺寸: {window_size}")

            # 配置动作执行器的窗口偏移
            if hasattr(self.action_executor, "set_window_offset"):
                self.action_executor.set_window_offset(window_offset[0], window_offset[1])
                print(f"已设置动作执行器窗口偏移: {window_offset}")

            # 配置屏幕截图的窗口区域
            if hasattr(self.screen_capture, "set_window_region"):
                self.screen_capture.set_window_region(
                    window_offset[0], window_offset[1], window_size[0], window_size[1]
                )
                print(f"已设置屏幕截图窗口区域: {window_offset} + {window_size}")

        except (WindowDetectionException, WindowNotFoundException, WindowSizeException) as e:
            print(f"窗口检测警告: {e}，将使用全屏模式")
            self._clear_window_offsets()
        except Exception as e:
            print(f"窗口模式自动检测出错: {e}，将使用全屏模式")
            self._clear_window_offsets()

    def _clear_window_offsets(self) -> None:
        """清除窗口偏移设置，回退到全屏模式"""
        try:
            # 清除动作执行器的窗口偏移
            if hasattr(self.action_executor, "set_window_offset"):
                self.action_executor.set_window_offset(0, 0)

            # 清除屏幕截图的窗口区域
            if hasattr(self.screen_capture, "clear_window_region"):
                self.screen_capture.clear_window_region()

        except Exception as e:
            print(f"清除窗口偏移设置时出错: {e}")

    def _switch_mode(self, config: TradingConfig) -> None:
        """切换交易模式"""
        try:
            # 创建新的交易模式
            new_mode = TradingModeFactory.create_mode(
                config, self.ocr_engine, self.screen_capture, self.action_executor
            )

            # 初始化新模式
            new_mode.initialize(config, profit=self.profit, count=self.count,
                                total_count=self.total_count, cost=self.cost, detail=self.detail)

            # 更新当前模式
            self.current_mode = new_mode

            print(f"切换到模式: {config.trading_mode}")

        except Exception as e:
            raise TradingException(f"切换交易模式失败: {e}") from e
