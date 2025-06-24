#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证 Windows Theme Switcher v1.6.1 的 Bug 修复

主要测试点：
1. 程序能否正常启动并隐藏在屏幕边缘
2. 鼠标靠近精确区域时能否正常唤出窗口
3. 鼠标离开窗口后能否正常自动隐藏
4. 非精确区域触发后的自动隐藏功能是否正常
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from theme_switcher import WindowsThemeSwitcher
    print("✓ 成功导入 WindowsThemeSwitcher 类")
    
    print("\n正在启动 Windows Theme Switcher v1.6.1...")
    print("\n测试要点：")
    print("1. 程序应该启动后立即隐藏在屏幕右侧边缘")
    print("2. 将鼠标移动到屏幕右侧边缘的窗口对应区域应该能唤出窗口")
    print("3. 鼠标离开窗口区域后，窗口应该在0.5秒后自动隐藏")
    print("4. 即使通过非精确区域唤出窗口，自动隐藏功能也应该正常工作")
    print("\n按 Ctrl+C 退出测试\n")
    
    # 启动应用
    app = WindowsThemeSwitcher()
    app.run()
    
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ 运行时错误: {e}")
    sys.exit(1)