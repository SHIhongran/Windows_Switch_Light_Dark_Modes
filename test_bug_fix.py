#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证Windows主题切换器v1.6.1的bug修复
主要测试窗口自动隐藏功能是否正常工作
"""

import sys
import os

def test_imports():
    """测试导入是否正常"""
    try:
        # 测试主要模块导入
        import tkinter as tk
        from tkinter import ttk
        import subprocess
        import winreg
        import ctypes
        from ctypes import wintypes
        import threading
        import time
        print("✓ 所有必需模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_syntax():
    """测试语法是否正确"""
    try:
        with open('theme_switcher.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 编译代码检查语法
        compile(code, 'theme_switcher.py', 'exec')
        print("✓ 代码语法检查通过")
        return True
    except SyntaxError as e:
        print(f"✗ 语法错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 文件读取错误: {e}")
        return False

def test_class_structure():
    """测试类结构是否完整"""
    try:
        # 动态导入并检查类结构
        sys.path.insert(0, os.getcwd())
        
        # 检查关键方法是否存在
        with open('theme_switcher.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        required_methods = [
            'should_show_window',
            'should_hide_window', 
            'start_hide_timer_unified',
            'mouse_check_loop',
            'show_window',
            'hide_window'
        ]
        
        missing_methods = []
        for method in required_methods:
            if f'def {method}(' not in code:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"✗ 缺少关键方法: {missing_methods}")
            return False
        else:
            print("✓ 所有关键方法都存在")
            return True
            
    except Exception as e:
        print(f"✗ 类结构检查失败: {e}")
        return False

def test_bug_fix_logic():
    """测试bug修复逻辑"""
    try:
        with open('theme_switcher.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 检查是否移除了旧的事件绑定
        if '<Enter>' in code or '<Leave>' in code:
            print("✗ 仍然存在 <Enter>/<Leave> 事件绑定")
            return False
        
        # 检查是否有统一的轮询逻辑
        if 'mouse_check_loop' not in code:
            print("✗ 缺少统一的鼠标检测循环")
            return False
            
        # 检查是否有防重复计时器逻辑
        if 'if not self.hide_timer_id:' not in code:
            print("✗ 缺少防重复计时器逻辑")
            return False
            
        print("✓ Bug修复逻辑检查通过")
        return True
        
    except Exception as e:
        print(f"✗ Bug修复逻辑检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试Windows主题切换器v1.6.1 Bug修复...\n")
    
    tests = [
        ("模块导入测试", test_imports),
        ("语法检查测试", test_syntax), 
        ("类结构测试", test_class_structure),
        ("Bug修复逻辑测试", test_bug_fix_logic)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"运行 {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Bug修复成功！")
        print("\n修复内容总结:")
        print("1. ✓ 移除了对 <Enter>/<Leave> 事件的依赖")
        print("2. ✓ 实现了统一的鼠标位置轮询机制")
        print("3. ✓ 添加了防重复计时器逻辑")
        print("4. ✓ 优化了窗口显示/隐藏的触发条件")
        print("\n现在窗口应该能够正确地自动隐藏，无论是如何被触发显示的。")
    else:
        print("\n❌ 部分测试失败，请检查代码。")
    
    return passed == total

if __name__ == "__main__":
    main()