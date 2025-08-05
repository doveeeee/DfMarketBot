#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试导入所有模块
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """测试所有模块导入"""
    try:
        # 测试核心接口
        from src.core.interfaces import ITradingService, TradingConfig, MarketData
        print("✅ 核心接口导入成功")
        
        # 测试配置管理
        from src.config.settings import JsonConfigManager, ConfigManager
        print("✅ 配置管理导入成功")
        
        # 测试服务层
        from src.services.trading_service import TradingService
        print("✅ 交易服务导入成功")
        
        # 测试检测器
        from src.services.detector import PriceDetector, RollingModeDetector
        print("✅ 检测器导入成功")
        
        # 测试交易模式
        from src.services.trading_modes import TradingModeFactory
        print("✅ 交易模式导入成功")
        
        # 测试基础设施
        from src.infrastructure.screen_capture import ScreenCapture
        from src.infrastructure.ocr_engine import TesseractOCREngine
        from src.infrastructure.action_executor import ActionExecutorFactory
        print("✅ 基础设施导入成功")
        
        # 测试UI适配器
        from src.ui.adapter import UIAdapter
        print("✅ UI适配器导入成功")
        
        # 测试主程序
        from GUIV2.AppGUI import Ui_MainWindow
        print("✅ UI文件导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试模块导入...")
    success = test_imports()
    if success:
        print("\n🎉 所有模块导入成功！")
    else:
        print("\n💥 存在导入错误，请检查依赖和代码")