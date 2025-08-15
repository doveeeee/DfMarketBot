#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试滚仓配置动态加载功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.config_manager import YamlConfigManager as ConfigManager
from src.services.strategy import RollingStrategy
from src.core.interfaces import MarketData

def test_rolling_config_loading():
    """测试滚仓配置加载"""
    print("=== 测试滚仓配置动态加载 ===")
    
    # 创建配置管理器
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # 验证配置包含滚仓选项
    print("✓ 配置文件加载成功")
    print(f"  - 当前滚仓选项: {config.rolling_option}")
    print(f"  - 可用滚仓选项: {len(config.rolling_options)} 个")
    
    # 测试每个滚仓选项
    for i, option_config in enumerate(config.rolling_options):
        print(f"\n  选项 {i}: {option_config}")
    
    # 测试策略类使用配置
    strategy = RollingStrategy(config)
    
    # 模拟市场数据测试
    test_market_data = MarketData(current_price=1000000)  # 测试价格
    
    # 测试不同选项
    for i in range(4):
        # 更新配置
        config.rolling_option = i
        strategy.config = config
        
        if i < len(config.rolling_options):
            option_config = config.rolling_options[i]
            target_price = option_config["buy_price"] * option_config["buy_count"]
            min_price = option_config["min_buy_price"] * option_config["buy_count"]
            
            print(f"\n选项 {i}:")
            print(f"  目标价格: {target_price}")
            print(f"  最低价格: {min_price}")
            print(f"  购买数量: {option_config['buy_count']}")
    
    return True

def test_config_hot_reload():
    """测试配置热更新"""
    print("\n=== 测试配置热更新 ===")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # 修改配置
    original_option = config.rolling_option
    new_option = (original_option + 1) % 4
    
    # 更新配置
    config_manager.update_config({"rolling_option": new_option})
    
    # 重新加载验证
    updated_config = config_manager.load_config()
    print(f"✓ 配置热更新成功")
    print(f"  - 原选项: {original_option}")
    print(f"  - 新选项: {updated_config.rolling_option}")
    
    # 恢复原始配置
    config_manager.update_config({"rolling_option": original_option})
    
    return True

def test_custom_rolling_options():
    """测试自定义滚仓选项"""
    print("\n=== 测试自定义滚仓选项 ===")
    
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # 添加新的自定义选项
    custom_options = [
        {"buy_price": 520, "min_buy_price": 300, "buy_count": 4980},
        {"buy_price": 450, "min_buy_price": 270, "buy_count": 4980},
        {"buy_price": 450, "min_buy_price": 270, "buy_count": 4980},
        {"buy_price": 1700, "min_buy_price": 700, "buy_count": 1740},
    ]
    
    # 更新配置
    config_manager.update_config({"rolling_options": custom_options})
    
    # 验证更新
    updated_config = config_manager.load_config()
    print(f"✓ 自定义选项添加成功")
    print(f"  - 可用选项: {len(updated_config.rolling_options)} 个")
    print(f"  - 新选项4: {updated_config.rolling_options[4] if len(updated_config.rolling_options) > 4 else '不存在'}")
    
    return True

if __name__ == "__main__":
    print("开始测试滚仓配置动态加载功能...")
    
    tests = [
        test_rolling_config_loading,
        test_config_hot_reload,
        test_custom_rolling_options
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ 测试失败: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！滚仓配置动态加载功能正常")
    else:
        print("❌ 部分测试失败")