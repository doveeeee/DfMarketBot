# -*- coding: utf-8 -*-
"""
核心接口定义层
"""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, Generic, Optional, Tuple, Type, TypeVar

import numpy as np

from src.config.trading_config import TradingConfig


@dataclass
class MarketData:
    """市场数据"""

    current_price: int
    balance: Optional[int] = None
    last_balance: Optional[int] = None
    last_buy_quantity: Optional[int] = None
    timestamp: float = 0.0
    profit: Optional[int] = 0
    count: Optional[int] = 0
    total_count: Optional[int] = 0
    cost: Optional[int] = 0
    detail: Optional[dict[float, int]] = None

    def update_statistics(self, market_data):
        if market_data.profit > 0:
            self.profit = market_data.profit
        if market_data.count > 0:
            self.count = market_data.count
        if market_data.total_count > 0:
            self.total_count = market_data.total_count
        if market_data.cost > 0:
            self.cost = market_data.cost
        if market_data.detail is not None:
            self.detail = market_data.detail


class IPriceDetector(ABC):
    """价格检测器接口"""

    @abstractmethod
    def detect_price(self) -> int:
        """检测当前物品价格"""

    @abstractmethod
    def detect_balance(self) -> Optional[int]:
        """检测当前哈夫币余额"""


class IActionExecutor(ABC):
    """动作执行器接口"""

    @abstractmethod
    def click_position(self, position: Tuple[float, float], right_click=False) -> None:
        """点击指定位置"""

    @abstractmethod
    def press_key(self, key: str) -> None:
        """按下键盘按键"""

    @abstractmethod
    def move_mouse(self, position: Tuple[float, float]) -> None:
        """移动鼠标到指定位置"""


class ITradingStrategy(ABC):
    """交易策略接口"""

    @abstractmethod
    def should_buy(self, market_data: MarketData) -> bool:
        """判断是否该购买"""

    @abstractmethod
    def should_refresh(self, market_data: MarketData) -> bool:
        """判断是否该刷新"""

    @abstractmethod
    def get_buy_quantity(self, market_data: MarketData) -> int:
        """获取购买数量"""


# 定义泛型类型
TConfig = TypeVar("TConfig", bound=object)


class ITradingMode(ABC):
    """交易模式接口"""

    @abstractmethod
    def prepare(self) -> None:
        """交易周期啊前准备"""

    @abstractmethod
    def execute_cycle(self) -> bool:
        """执行一个交易周期，返回是否继续"""

    @abstractmethod
    def initialize(self, config: TradingConfig, **kwargs) -> None:
        """初始化模式"""

    @abstractmethod
    def get_market_data(self) -> Optional[MarketData]:
        """获取当前市场数据"""

    @abstractmethod
    def stop(self):
        """停止交易"""


class ILogger(ABC):
    """日志接口"""

    @abstractmethod
    def info(self, message: str) -> None:
        """info日志"""

    @abstractmethod
    def error(self, message: str) -> None:
        """error日志"""

    @abstractmethod
    def debug(self, message: str) -> None:
        """debug日志"""


class IConfigManager(ABC, Generic[TConfig]):
    """配置管理器接口（泛型版本）"""

    def __init__(self, config_path: str = None):
        pass

    @abstractmethod
    def load_config(self) -> TConfig:
        """加载配置"""
        raise NotImplementedError

    @abstractmethod
    def save_config(self, config: TConfig) -> None:
        """保存配置"""
        raise NotImplementedError

    @abstractmethod
    def update_config(self, updates: Dict[str, Any]) -> TConfig:
        """更新配置"""
        raise NotImplementedError

    @abstractmethod
    def reload_config(self) -> TConfig:
        """重新加载配置（支持热更新）"""
        raise NotImplementedError

    @staticmethod
    def _config_to_dict(config: TConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        if hasattr(config, "to_dict"):
            return config.to_dict()
        return asdict(config)

    @staticmethod
    def _dict_to_config(config_dict: Dict[str, Any], config_class: Type[TConfig]) -> TConfig:
        """将字典转换为配置对象"""
        if hasattr(config_class, "from_dict"):
            return config_class.from_dict(config_dict)
        return config_class(**config_dict)


class IOCREngine(ABC):
    """OCR引擎接口"""

    @abstractmethod
    def image_to_string(self, image: np.ndarray, binarize: bool = True, font: str = "", thresh=127) -> str:
        """将图像转换为字符串"""

    @abstractmethod
    def detect_template(self, image: np.ndarray, template_name: str) -> bool:
        """检测模板匹配"""

    @abstractmethod
    def find_template(self, image: np.ndarray, template_name: str) -> tuple:
        """检测模板所在位置"""

    @staticmethod
    @abstractmethod
    def get_pixel_color(image: np.ndarray, x: int, y: int):
        """检测固定点的像素值"""


class ITradingService(ABC):
    """交易服务接口"""

    @abstractmethod
    def initialize(self, config: TradingConfig) -> None:
        """初始化交易服务"""

    @abstractmethod
    def prepare(self) -> None:
        """交易前准备"""

    @abstractmethod
    def execute_cycle(self) -> bool:
        """执行一个交易周期"""

    @abstractmethod
    def get_market_data(self) -> Optional[MarketData]:
        """获取当前市场数据"""

    @abstractmethod
    def stop(self) -> None:
        """停止交易服务"""
