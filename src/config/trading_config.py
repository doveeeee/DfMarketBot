from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict


class TradingMode(Enum):
    """交易模式枚举"""

    ROLLING = 0  # 滚仓模式 - 配装页面购买
    HOARDING = 1  # 屯仓模式 - 交易页面购买


class ItemType(Enum):
    """物品类型枚举"""

    CONVERTIBLE = 0
    NON_CONVERTIBLE = 1


@dataclass
class TradingConfig:
    """交易配置数据类"""

    ideal_price: int = 0
    key_mode: bool = False
    max_price: int = 0
    rolling_loop_interval: int = 50
    hoarding_loop_interval: int = 150
    item_type: ItemType = ItemType.CONVERTIBLE
    use_balance_calculation: bool = False
    trading_mode: TradingMode = TradingMode.HOARDING
    rolling_option: int = 0  # 滚仓模式下的配装选项
    rolling_options: list = None  # 滚仓选项配置数组
    screen_width: int = 2560
    screen_height: int = 1440
    auto_sell: bool = True
    fast_sell: bool = True
    log_level: str = "INFO"
    second_detect: bool = False
    switch_to_battlefield: bool = False
    switch_to_battlefield_count: int = 300
    min_sell_price: int = 0

    def __post_init__(self):
        """验证配置参数"""
        if self.ideal_price < 0:
            raise ValueError("理想价格不能为负数")
        if self.max_price < 0:
            raise ValueError("最高价格不能为负数")
        if self.rolling_loop_interval <= 0:
            raise ValueError("循环间隔必须大于0")
        if self.hoarding_loop_interval <= 0:
            raise ValueError("循环间隔必须大于0")
        if self.screen_width <= 0 or self.screen_height <= 0:
            raise ValueError("屏幕分辨率必须大于0")

        # 处理整数到枚举的转换
        if isinstance(self.trading_mode, int):
            self.trading_mode = TradingMode(self.trading_mode)
        if isinstance(self.item_type, int):
            self.item_type = ItemType(self.item_type)

        # 设置默认滚仓选项配置
        if self.rolling_options is None:
            self.rolling_options = [
                {
                    "buy_price": 520,
                    "min_buy_price": 300,
                    "buy_count": 4980,
                    "fast_sell_threshold": 0,
                    "min_sell_price": 0,
                },
                {
                    "buy_price": 450,
                    "min_buy_price": 270,
                    "buy_count": 4980,
                    "fast_sell_threshold": 0,
                    "min_sell_price": 0,
                },
                {
                    "buy_price": 450,
                    "min_buy_price": 270,
                    "buy_count": 4980,
                    "fast_sell_threshold": 0,
                    "min_sell_price": 0,
                },
                {
                    "buy_price": 1700,
                    "min_buy_price": 700,
                    "buy_count": 1740,
                    "fast_sell_threshold": 0,
                    "min_sell_price": 0,
                },
            ]

        # 确保所有滚仓选项都包含必要字段（向后兼容性）
        self._ensure_rolling_options_compatibility()

        # 验证所有滚仓选项的配置
        self._validate_rolling_options()

    def to_dict(self):
        """序列化为 dict，枚举转 value"""
        config_dict = asdict(self)
        config_dict["trading_mode"] = config_dict["trading_mode"].value
        config_dict["item_type"] = config_dict["item_type"].value
        return config_dict

    def _ensure_rolling_options_compatibility(self):
        """确保所有滚仓选项都包含必要字段，提供向后兼容性"""
        if self.rolling_options:
            for option in self.rolling_options:
                # 确保包含 fast_sell_threshold 字段
                if "fast_sell_threshold" not in option:
                    option["fast_sell_threshold"] = 0  # 默认值为0，表示总是启用快速售卖
                elif option["fast_sell_threshold"] < 0:
                    option["fast_sell_threshold"] = 0  # 负数重置为0

                # 确保包含 min_sell_price 字段
                if "min_sell_price" not in option:
                    # 如果没有设置，使用全局的 min_sell_price 作为默认值
                    option["min_sell_price"] = 0
                elif option["min_sell_price"] < 0:
                    option["min_sell_price"] = 0  # 负数重置为0

    def _validate_rolling_options(self):
        """验证所有滚仓选项的配置有效性"""
        if not self.rolling_options:
            return

        for i, option in enumerate(self.rolling_options):
            # 验证必需字段
            required_fields = ["buy_price", "min_buy_price", "buy_count", "fast_sell_threshold", "min_sell_price"]
            for field in required_fields:
                if field not in option:
                    raise ValueError(f"滚仓选项 {i} 缺少必需字段: {field}")

            # 验证数值有效性
            if option["buy_price"] < 0:
                raise ValueError(f"滚仓选项 {i} 的购买价格不能为负数")
            if option["min_buy_price"] < 0:
                raise ValueError(f"滚仓选项 {i} 的最低购买价格不能为负数")
            if option["buy_count"] <= 0:
                raise ValueError(f"滚仓选项 {i} 的购买数量必须大于0")
            if option["fast_sell_threshold"] < 0:
                raise ValueError(f"滚仓选项 {i} 的快速售卖阈值不能为负数")
            if option["min_sell_price"] < 0:
                raise ValueError(f"滚仓选项 {i} 的最低售卖价格不能为负数")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TradingConfig":
        """从 dict 反序列化，支持枚举"""
        # 处理枚举类型
        if "trading_mode" in config_dict and not isinstance(config_dict["trading_mode"], TradingMode):
            config_dict["trading_mode"] = TradingMode(config_dict["trading_mode"])
        if "item_type" in config_dict and not isinstance(config_dict["item_type"], ItemType):
            config_dict["item_type"] = ItemType(config_dict["item_type"])
        return cls(**config_dict)
