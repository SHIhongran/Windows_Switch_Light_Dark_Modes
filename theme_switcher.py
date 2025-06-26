import tkinter as tk
from tkinter import ttk
import subprocess
import winreg
import sys
import os
import ctypes
from ctypes import wintypes
import threading
import time
import configparser
from datetime import datetime

class WindowsThemeSwitcher:
    def __init__(self):
        self.root = tk.Tk()
        
        # 立即隐藏主窗口
        self.root.withdraw()

        # 定义色彩系统
        self.light_theme_colors = {
            'bg': '#f5f7fc',
            'fg': '#333333',
            'btn_bg': '#e8ecf4',
            'btn_active_bg': '#dfe4ee'
        }
        self.dark_theme_colors = {
            'bg': '#17191f',
            'fg': '#e0e0e0',
            'btn_bg': '#2c2f3a',
            'btn_active_bg': '#3a3e4c'
        }

        self.root.title("Windows主题切换器")
        self.root.geometry("180x280")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)

        self.is_docked = False
        self.dock_side = None
        self.is_hidden = False
        self.mouse_check_thread = None
        self.mouse_check_running = False
        self.hide_timer_id = None
        self.restart_explorer = tk.BooleanVar(value=True)
        self.dock_indicator = None
        self.DOCK_OFFSET = 5
        
        # UI锁定相关变量
        self.ui_mask = None
        self.interactive_widgets = []
        
        # 定时切换相关变量
        self.is_timed_switching_enabled = False
        self.dark_time = "20:00"
        self.light_time = "06:00"
        self.last_auto_switch_minute = None
        self.config_file = "config.ini"
        
        # 加载配置
        self.load_config()

        # 显示启动画面
        self.show_splash_screen()
        
        self.setup_window_style()
        self.create_ui()
        self.bind_events()
        self.update_theme_status()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def setup_window_style(self):
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)

    def create_ui(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)

        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.place(relx=0.5, rely=0.5, anchor='center')

        self.close_btn = tk.Button(self.root, text="×",
                                 font=('Arial', 10, 'bold'),
                                 border=0, cursor='hand2',
                                 command=self.root.quit)
        self.close_btn.place(x=155, y=5, width=20, height=20)

        self.status_label = tk.Label(self.content_frame, text="当前主题: 检测中...",
                                    font=('Microsoft YaHei UI', 9),
                                    wraplength=150)
        self.status_label.pack(pady=(0, 15))

        self.toggle_btn = tk.Button(self.content_frame, text="切换主题",
                                   font=('Microsoft YaHei UI', 10, 'bold'),
                                   border=0, cursor='hand2',
                                   padx=25, pady=10,
                                   command=self.execute_theme_toggle_with_lock)
        self.toggle_btn.pack(pady=(0, 15))

        self.restart_check = tk.Checkbutton(self.content_frame,
                                          text="切换后重启资源管理器",
                                          variable=self.restart_explorer,
                                          font=('Microsoft YaHei UI', 8),
                                          wraplength=140,
                                          command=self.save_config)
        self.restart_check.pack()

        self.restart_now_btn = tk.Button(self.content_frame, text="立即重启资源管理器",
                                         font=('Microsoft YaHei UI', 9),
                                         border=0, cursor='hand2',
                                         padx=10, pady=5,
                                         command=self.execute_restart_explorer_with_lock)
        self.restart_now_btn.pack(pady=(10, 0))
        
        # 创建定时切换功能模块
        self.create_timer_module()
        
        # 收集可交互控件
        self.interactive_widgets = [self.close_btn, self.toggle_btn, self.restart_check, self.restart_now_btn,
                                   self.timer_toggle_btn, self.dark_time_label, self.light_time_label,
                                   self.dark_icon_label, self.light_icon_label]
        
        # 创建UI蒙版（默认隐藏）
        self.create_ui_mask()
    
    def create_timer_module(self):
        """创建定时切换功能模块"""
        # 创建定时切换功能容器
        self.timer_frame = tk.Frame(self.content_frame)
        self.timer_frame.pack(pady=(15, 0), fill='x')
        
        # 启用/禁用开关按钮
        self.timer_toggle_btn = tk.Button(self.timer_frame, 
                                         text="×" if not self.is_timed_switching_enabled else "√",
                                         font=('Arial', 10, 'bold'),
                                         width=3, height=1,
                                         border=0, cursor='hand2',
                                         command=self.toggle_timer_enabled)
        self.timer_toggle_btn.pack(side='left', padx=(0, 12))
        
        # 暗色时间设置区域
        self.dark_time_frame = tk.Frame(self.timer_frame, cursor='hand2')
        self.dark_time_frame.pack(side='left', padx=(0, 8))
        self.dark_time_frame.bind('<Button-1>', lambda e: self.open_time_picker('dark'))
        
        self.dark_time_label = tk.Label(self.dark_time_frame, 
                                       text=self.dark_time,
                                       font=('Microsoft YaHei UI', 8),
                                       cursor='hand2')
        self.dark_time_label.pack(side='left')
        self.dark_time_label.bind('<Button-1>', lambda e: self.open_time_picker('dark'))
        
        self.dark_icon_label = tk.Label(self.dark_time_frame, 
                                       text="🕒",
                                       font=('Arial', 8),
                                       cursor='hand2')
        self.dark_icon_label.pack(side='left', padx=(3, 0))
        self.dark_icon_label.bind('<Button-1>', lambda e: self.open_time_picker('dark'))
        
        # 浅色时间设置区域
        self.light_time_frame = tk.Frame(self.timer_frame, cursor='hand2')
        self.light_time_frame.pack(side='left', padx=(8, 0))
        self.light_time_frame.bind('<Button-1>', lambda e: self.open_time_picker('light'))
        
        self.light_time_label = tk.Label(self.light_time_frame, 
                                        text=self.light_time,
                                        font=('Microsoft YaHei UI', 8),
                                        cursor='hand2')
        self.light_time_label.pack(side='left')
        self.light_time_label.bind('<Button-1>', lambda e: self.open_time_picker('light'))
        
        self.light_icon_label = tk.Label(self.light_time_frame, 
                                        text="🕒",
                                        font=('Arial', 8),
                                        cursor='hand2')
        self.light_icon_label.pack(side='left', padx=(3, 0))
        self.light_icon_label.bind('<Button-1>', lambda e: self.open_time_picker('light'))
        
        # 启动定时检查器
        self.schedule_checker()



    def bind_events(self):
        """绑定事件 - 精准绑定拖动事件到背景容器"""
        # 只为背景容器和非交互控件绑定拖动事件
        self.main_frame.bind('<Button-1>', self.start_drag)
        self.main_frame.bind('<B1-Motion>', self.on_drag)
        self.main_frame.bind('<ButtonRelease-1>', self.end_drag)
        
        self.content_frame.bind('<Button-1>', self.start_drag)
        self.content_frame.bind('<B1-Motion>', self.on_drag)
        self.content_frame.bind('<ButtonRelease-1>', self.end_drag)
        
        self.status_label.bind('<Button-1>', self.start_drag)
        self.status_label.bind('<B1-Motion>', self.on_drag)
        self.status_label.bind('<ButtonRelease-1>', self.end_drag)

    def should_show_window(self, mouse_x, mouse_y):
        """检查是否应该显示窗口 - 精准区域触发"""
        if not self.is_hidden:
            return False
            
        try:
            window_x = self.root.winfo_x()
            window_y = self.root.winfo_y()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            screen_width = self.root.winfo_screenwidth()
        except:
            return False
            
        if self.dock_side == 'left':
            return (mouse_x < self.DOCK_OFFSET) and \
                   (window_y < mouse_y < window_y + window_height)
                   
        elif self.dock_side == 'right':
            return (mouse_x > screen_width - self.DOCK_OFFSET) and \
                   (window_y < mouse_y < window_y + window_height)
                   
        elif self.dock_side == 'top':
            return (mouse_y < self.DOCK_OFFSET) and \
                   (window_x < mouse_x < window_x + window_width)
                   
        return False

    def should_hide_window(self, mouse_x, mouse_y):
        """检查是否应该隐藏窗口 - 鼠标离开窗口区域"""
        if self.is_hidden or not self.is_docked:
            return False
            
        try:
            window_x = self.root.winfo_x()
            window_y = self.root.winfo_y()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
        except:
            return False
            
        # 检查鼠标是否在窗口区域外
        mouse_outside = not (window_x <= mouse_x <= window_x + window_width and 
                           window_y <= mouse_y <= window_y + window_height)
        
        return mouse_outside

    def start_hide_timer_unified(self):
        """统一的隐藏计时器启动方法"""
        # 取消之前的计时器
        if self.hide_timer_id:
            self.root.after_cancel(self.hide_timer_id)
            
        # 启动新的隐藏计时器
        if self.is_docked and not self.is_hidden:
            self.hide_timer_id = self.root.after(500, self.hide_window)

    def start_drag(self, event):
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.window_start_x = self.root.winfo_x()
        self.window_start_y = self.root.winfo_y()

    def on_drag(self, event):
        if self.is_hidden:
            self.show_window()
        dx = event.x_root - self.drag_start_x
        dy = event.y_root - self.drag_start_y
        new_x = self.window_start_x + dx
        new_y = self.window_start_y + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def end_drag(self, event):
        screen_width = self.root.winfo_screenwidth()
        x = self.root.winfo_x()
        window_width = self.root.winfo_width()
        snap_threshold = 50
        if x <= snap_threshold:
            self.dock_to_edge('left')
        elif x + window_width >= screen_width - snap_threshold:
            self.dock_to_edge('right')
        elif self.root.winfo_y() <= snap_threshold:
            self.dock_to_edge('top')
        else:
            self.undock()

    def dock_to_edge(self, side):
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_width()
        self.is_docked = True
        self.dock_side = side
        if side == 'left':
            self.root.geometry(f"+0+{self.root.winfo_y()}")
        elif side == 'right':
            self.root.geometry(f"+{screen_width - window_width}+{self.root.winfo_y()}")
        elif side == 'top':
            self.root.geometry(f"+{self.root.winfo_x()}+0")
        self.root.after(1000, self.hide_window)

    def undock(self):
        self.is_docked = False
        self.dock_side = None
        self.remove_dock_indicator()
        self.stop_mouse_check()
        if self.hide_timer_id:
            self.root.after_cancel(self.hide_timer_id)
            self.hide_timer_id = None

    def hide_window(self):
        """隐藏窗口 - 统一管理版本"""
        if not self.is_docked:
            return
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        if self.dock_side == 'left':
            self.root.geometry(f"+{-window_width + self.DOCK_OFFSET}+{current_y}")
        elif self.dock_side == 'right':
            self.root.geometry(f"+{screen_width - self.DOCK_OFFSET}+{current_y}")
        elif self.dock_side == 'top':
            self.root.geometry(f"+{current_x}+{-window_height + self.DOCK_OFFSET}")
        self.is_hidden = True
        self.create_dock_indicator()
        # 隐藏后启动鼠标检测，用于检测何时显示
        if not self.mouse_check_running:
            self.start_mouse_check()

    def show_window(self):
        """显示窗口 - 统一管理版本"""
        if not self.is_hidden:
            return
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_width()
        current_y = self.root.winfo_y()
        current_x = self.root.winfo_x()
        if self.dock_side == 'left':
            self.root.geometry(f"+0+{current_y}")
        elif self.dock_side == 'right':
            self.root.geometry(f"+{screen_width - window_width}+{current_y}")
        elif self.dock_side == 'top':
            self.root.geometry(f"+{current_x}+0")
        self.is_hidden = False
        self.remove_dock_indicator()
        # 显示后继续鼠标检测，用于检测何时隐藏
        if not self.mouse_check_running:
            self.start_mouse_check()

    def start_mouse_check(self):
        """启动鼠标检测线程 - 统一管理显示和隐藏逻辑"""
        if self.mouse_check_running:
            return
        self.mouse_check_running = True
        self.mouse_check_thread = threading.Thread(target=self.mouse_check_loop, daemon=True)
        self.mouse_check_thread.start()

    def stop_mouse_check(self):
        """停止鼠标检测线程"""
        self.mouse_check_running = False

    def mouse_check_loop(self):
        """鼠标检测循环 - 统一处理显示和隐藏逻辑"""
        while self.mouse_check_running and self.is_docked:
            try:
                mouse_x, mouse_y = self.get_mouse_position()
                
                if self.is_hidden:
                    # 窗口隐藏时：检测是否应该显示
                    if self.should_show_window(mouse_x, mouse_y):
                        self.root.after(0, self.show_window)
                        # 显示后继续检测，不退出循环
                else:
                    # 窗口显示时：检测是否应该隐藏
                    if self.should_hide_window(mouse_x, mouse_y):
                        # 只有在没有活动计时器时才启动新的隐藏计时器
                        if not self.hide_timer_id:
                            self.root.after(0, self.start_hide_timer_unified)
                    else:
                        # 鼠标回到窗口内，取消隐藏计时器
                        if self.hide_timer_id:
                            self.root.after_cancel(self.hide_timer_id)
                            self.hide_timer_id = None
                        
                time.sleep(0.1)
            except:
                break



    def get_mouse_position(self):
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def create_dock_indicator(self):
        if self.dock_indicator:
            return
        self.dock_indicator = tk.Toplevel(self.root)
        self.dock_indicator.overrideredirect(True)
        self.dock_indicator.attributes('-topmost', True)
        self.update_dock_indicator_color()
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        if self.dock_side == 'left':
            self.dock_indicator.geometry(f"{self.DOCK_OFFSET}x{window_height}+0+{current_y}")
        elif self.dock_side == 'right':
            self.dock_indicator.geometry(f"{self.DOCK_OFFSET}x{window_height}+{screen_width - self.DOCK_OFFSET}+{current_y}")
        elif self.dock_side == 'top':
            self.dock_indicator.geometry(f"{window_width}x{self.DOCK_OFFSET}+{current_x}+0")

    def remove_dock_indicator(self):
        if self.dock_indicator:
            self.dock_indicator.destroy()
            self.dock_indicator = None

    def update_dock_indicator_color(self):
        if self.dock_indicator:
            theme = self.get_current_theme()
            indicator_color = '#FFFFFF' if theme == 'light' else '#000000'
            self.dock_indicator.configure(bg=indicator_color)

    def center_window(self):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"+{x}+{y}")

    def get_current_theme(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return 'light' if value == 1 else 'dark'
        except:
            return 'unknown'

    def update_ui_theme(self):
        theme = self.get_current_theme()
        colors = self.dark_theme_colors if theme == 'dark' else self.light_theme_colors
        self.root.config(bg=colors['bg'])
        self.main_frame.config(bg=colors['bg'])
        self.content_frame.config(bg=colors['bg'])
        self.status_label.config(bg=colors['bg'], fg=colors['fg'])
        self.toggle_btn.config(bg=colors['btn_bg'], fg=colors['fg'], activebackground=colors['btn_active_bg'], relief=tk.FLAT)
        self.restart_check.config(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['bg'], activebackground=colors['bg'], activeforeground=colors['fg'])
        self.restart_now_btn.config(bg=colors['btn_bg'], fg=colors['fg'], activebackground=colors['btn_active_bg'], relief=tk.FLAT)
        self.close_btn.config(bg=colors['bg'], fg=colors['fg'], activebackground=colors['btn_active_bg'])
        
        # 更新定时切换模块颜色
        if hasattr(self, 'timer_frame'):
            self.timer_frame.config(bg=colors['bg'])
            self.timer_toggle_btn.config(bg=colors['btn_bg'], fg=colors['fg'], activebackground=colors['btn_active_bg'], relief=tk.FLAT)
            self.dark_time_frame.config(bg=colors['bg'])
            self.light_time_frame.config(bg=colors['bg'])
            self.dark_time_label.config(bg=colors['bg'], fg=colors['fg'])
            self.light_time_label.config(bg=colors['bg'], fg=colors['fg'])
            self.dark_icon_label.config(bg=colors['bg'])
            self.light_icon_label.config(bg=colors['bg'])
        
        # 更新蒙版颜色
        self.update_ui_mask_color()

    def update_theme_status(self):
        theme = self.get_current_theme()
        if theme == 'light':
            self.status_label.config(text="当前主题: 浅色模式")
            self.toggle_btn.config(text="切换到暗色")
        elif theme == 'dark':
            self.status_label.config(text="当前主题: 暗色模式")
            self.toggle_btn.config(text="切换到浅色")
        else:
            self.status_label.config(text="当前主题: 检测失败")
            self.toggle_btn.config(text="切换主题")
        self.update_ui_theme()
        self.update_dock_indicator_color()

    def execute_restart_explorer(self):
        try:
            script_path = self.resource_path("restart_explorer_only.bat")
            subprocess.run([script_path], creationflags=subprocess.CREATE_NO_WINDOW, check=True)
        except Exception as e:
            self.status_label.config(text=f"重启失败: {e}")

    def execute_theme_toggle(self):
        try:
            if self.restart_explorer.get():
                script_path = self.resource_path("toggle_and_restart.bat")
            else:
                script_path = self.resource_path("toggle_theme.bat")
            subprocess.run([script_path], creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            self.root.after(500, self.update_theme_status)
        except Exception as e:
            self.status_label.config(text=f"切换失败: {e}")
    
    def show_splash_screen(self):
        """显示启动画面"""
        # 创建启动画面窗口
        self.splash = tk.Toplevel()
        self.splash.overrideredirect(True)
        self.splash.geometry("400x225")
        
        # 检测当前主题并设置背景色
        current_theme = self.get_current_theme()
        bg_color = '#f5f7fc' if current_theme == 'light' else '#17191f'
        fg_color = '#333333' if current_theme == 'light' else '#e0e0e0'
        
        self.splash.configure(bg=bg_color)
        
        # 计算屏幕中央位置
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 225) // 2
        self.splash.geometry(f"400x225+{x}+{y}")
        
        # 创建内容
        main_frame = tk.Frame(self.splash, bg=bg_color)
        main_frame.pack(fill='both', expand=True)
        
        # 程序标题
        title_label = tk.Label(main_frame, text="Windows主题切换器", 
                              font=('Microsoft YaHei UI', 16, 'bold'),
                              bg=bg_color, fg=fg_color)
        title_label.pack(pady=(60, 20))
        
        # 版本信息
        version_label = tk.Label(main_frame, text="版本 1.6.2", 
                                font=('Microsoft YaHei UI', 10),
                                bg=bg_color, fg=fg_color)
        version_label.pack(pady=(0, 30))
        
        # 初始化提示
        status_label = tk.Label(main_frame, text="正在初始化...", 
                               font=('Microsoft YaHei UI', 9),
                               bg=bg_color, fg=fg_color)
        status_label.pack(pady=(0, 40))
        
        # 2秒后显示主窗口
        self.splash.after(2000, self.show_main_window)
    
    def show_main_window(self):
        """销毁启动画面并显示主程序"""
        # 销毁启动画面
        if hasattr(self, 'splash'):
            self.splash.destroy()
        
        # ---- 实现边缘启动逻辑 ----
        # 1. 立即设置初始停靠状态
        self.dock_side = 'right'  # 设置默认停靠在右侧
        self.is_docked = True
        self.is_hidden = True       # 立即将状态标记为隐藏

        # 2. 计算并预设边缘位置（在显示窗口之前）
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # X坐标：屏幕宽度 - 可见触发条的宽度
        x_pos = screen_width - self.DOCK_OFFSET
        
        # Y坐标：屏幕高度的一半 - 窗口高度的一半
        y_pos = (screen_height // 2) - (240 // 2)  # 使用固定高度240

        # 3. 先设置位置，再显示窗口（避免窗口闪烁）
        self.root.geometry(f'+{int(x_pos)}+{int(y_pos)}')
        self.root.deiconify()

        # 4. 创建指示器并启动鼠标检测
        self.create_dock_indicator()
        self.start_mouse_check()
    
    def create_ui_mask(self):
        """创建UI蒙版"""
        self.ui_mask = tk.Frame(self.main_frame)
        # 默认隐藏蒙版
        self.ui_mask.place_forget()
    
    def update_ui_mask_color(self):
        """根据当前主题更新蒙版颜色"""
        if self.ui_mask:
            theme = self.get_current_theme()
            # 使用较浅的颜色来模拟半透明效果
            mask_color = '#f0f0f0' if theme == 'light' else '#404040'
            self.ui_mask.configure(bg=mask_color)
    
    def lock_ui(self):
        """锁定UI"""
        # 禁用所有可交互控件
        for widget in self.interactive_widgets:
            widget.configure(state=tk.DISABLED)
        
        # 更新蒙版颜色并显示
        self.update_ui_mask_color()
        self.ui_mask.place(relwidth=1, relheight=1)
        self.ui_mask.lift()
        
        # 添加处理中提示标签
        if not hasattr(self, 'processing_label'):
            self.processing_label = tk.Label(self.ui_mask, text="处理中...", 
                                           font=('Microsoft YaHei UI', 10),
                                           bg=self.ui_mask.cget('bg'))
        
        theme = self.get_current_theme()
        label_fg = '#666666' if theme == 'light' else '#cccccc'
        self.processing_label.configure(fg=label_fg, bg=self.ui_mask.cget('bg'))
        self.processing_label.place(relx=0.5, rely=0.5, anchor='center')
    
    def unlock_ui(self):
        """解锁UI"""
        # 启用所有可交互控件
        for widget in self.interactive_widgets:
            widget.configure(state=tk.NORMAL)
        
        # 隐藏处理中标签
        if hasattr(self, 'processing_label'):
            self.processing_label.place_forget()
        
        # 隐藏蒙版
        self.ui_mask.place_forget()
    
    def execute_theme_toggle_with_lock(self):
        """带锁定的主题切换"""
        # 立即锁定UI
        self.lock_ui()
        
        # 判断锁定时间
        lock_duration = 3000 if self.restart_explorer.get() else 500
        
        # 异步执行脚本
        self.root.after(100, self.execute_theme_toggle)
        
        # 按预设时长解锁UI
        self.root.after(lock_duration, self.unlock_ui)
    
    def execute_restart_explorer_with_lock(self):
        """带锁定的重启资源管理器"""
        # 立即锁定UI
        self.lock_ui()
        
        # 异步执行脚本
        self.root.after(100, self.execute_restart_explorer)
        
        # 3秒后解锁UI
        self.root.after(3000, self.unlock_ui)
    
    def load_config(self):
        """加载配置文件"""
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file, encoding='utf-8')
            if 'TimerSettings' in config:
                self.is_timed_switching_enabled = config.getboolean('TimerSettings', 'enabled', fallback=False)
                self.dark_time = config.get('TimerSettings', 'dark_time', fallback='20:00')
                self.light_time = config.get('TimerSettings', 'light_time', fallback='06:00')
                restart_on_switch = config.getboolean('TimerSettings', 'restart_on_switch', fallback=True)
                self.restart_explorer.set(restart_on_switch)
        except Exception:
            # 如果配置文件不存在或损坏，使用默认值
            self.is_timed_switching_enabled = False
            self.dark_time = "20:00"
            self.light_time = "06:00"
            self.restart_explorer.set(True)
    
    def save_config(self):
        """保存配置文件"""
        config = configparser.ConfigParser()
        config['TimerSettings'] = {
            'enabled': str(self.is_timed_switching_enabled),
            'dark_time': self.dark_time,
            'light_time': self.light_time,
            'restart_on_switch': str(self.restart_explorer.get())
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def toggle_timer_enabled(self):
        """切换定时功能启用状态"""
        self.is_timed_switching_enabled = not self.is_timed_switching_enabled
        self.timer_toggle_btn.config(text="√" if self.is_timed_switching_enabled else "×")
        self.save_config()
    
    def open_time_picker(self, time_type):
        """打开时间选择器"""
        # 创建模态对话框
        picker = tk.Toplevel(self.root)
        picker.title(f"设置{'暗色' if time_type == 'dark' else '浅色'}模式时间")
        picker.geometry("250x150")
        picker.resizable(False, False)
        picker.transient(self.root)
        picker.grab_set()
        
        # 居中显示
        picker.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - picker.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - picker.winfo_height()) // 2
        picker.geometry(f"+{x}+{y}")
        
        # 应用主题颜色
        theme = self.get_current_theme()
        colors = self.dark_theme_colors if theme == 'dark' else self.light_theme_colors
        picker.config(bg=colors['bg'])
        
        # 获取当前时间
        current_time = self.dark_time if time_type == 'dark' else self.light_time
        hour, minute = current_time.split(':')
        
        # 创建UI
        main_frame = tk.Frame(picker, bg=colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(main_frame, 
                              text=f"设置{'暗色' if time_type == 'dark' else '浅色'}模式时间",
                              font=('Microsoft YaHei UI', 10, 'bold'),
                              bg=colors['bg'], fg=colors['fg'])
        title_label.pack(pady=(0, 15))
        
        # 时间选择区域
        time_frame = tk.Frame(main_frame, bg=colors['bg'])
        time_frame.pack(pady=(0, 15))
        
        # 小时选择
        hour_label = tk.Label(time_frame, text="小时:", 
                             font=('Microsoft YaHei UI', 9),
                             bg=colors['bg'], fg=colors['fg'])
        hour_label.grid(row=0, column=0, padx=(0, 5))
        
        hour_var = tk.StringVar(value=hour)
        hour_combo = ttk.Combobox(time_frame, textvariable=hour_var, 
                                 values=[f"{i:02d}" for i in range(24)],
                                 width=5, state="readonly")
        hour_combo.grid(row=0, column=1, padx=(0, 15))
        
        # 分钟选择
        minute_label = tk.Label(time_frame, text="分钟:", 
                               font=('Microsoft YaHei UI', 9),
                               bg=colors['bg'], fg=colors['fg'])
        minute_label.grid(row=0, column=2, padx=(0, 5))
        
        minute_var = tk.StringVar(value=minute)
        minute_combo = ttk.Combobox(time_frame, textvariable=minute_var,
                                   values=[f"{i:02d}" for i in range(60)],
                                   width=5, state="readonly")
        minute_combo.grid(row=0, column=3)
        
        # 按钮区域
        button_frame = tk.Frame(main_frame, bg=colors['bg'])
        button_frame.pack()
        
        def confirm_time():
            new_time = f"{hour_var.get()}:{minute_var.get()}"
            if time_type == 'dark':
                self.dark_time = new_time
                self.dark_time_label.config(text=new_time)
            else:
                self.light_time = new_time
                self.light_time_label.config(text=new_time)
            self.save_config()
            picker.destroy()
        
        def cancel_time():
            picker.destroy()
        
        confirm_btn = tk.Button(button_frame, text="确认",
                               font=('Microsoft YaHei UI', 9),
                               bg=colors['btn_bg'], fg=colors['fg'],
                               activebackground=colors['btn_active_bg'],
                               border=0, cursor='hand2',
                               padx=15, pady=5,
                               command=confirm_time)
        confirm_btn.pack(side='left', padx=(0, 10))
        
        cancel_btn = tk.Button(button_frame, text="取消",
                              font=('Microsoft YaHei UI', 9),
                              bg=colors['btn_bg'], fg=colors['fg'],
                              activebackground=colors['btn_active_bg'],
                              border=0, cursor='hand2',
                              padx=15, pady=5,
                              command=cancel_time)
        cancel_btn.pack(side='left')
    
    def schedule_checker(self):
        """后台调度检查器"""
        try:
            # 检查是否启用定时切换
            if self.is_timed_switching_enabled:
                current_time = datetime.now()
                current_hour_minute = f"{current_time.hour:02d}:{current_time.minute:02d}"
                current_minute_key = f"{current_time.hour:02d}:{current_time.minute:02d}"
                
                # 防止同一分钟内重复切换
                if self.last_auto_switch_minute != current_minute_key:
                    current_theme = self.get_current_theme()
                    
                    # 检查是否需要切换到暗色模式
                    if (current_hour_minute == self.dark_time and 
                        current_theme == 'light'):
                        self.execute_auto_theme_toggle()
                        self.last_auto_switch_minute = current_minute_key
                    
                    # 检查是否需要切换到浅色模式
                    elif (current_hour_minute == self.light_time and 
                          current_theme == 'dark'):
                        self.execute_auto_theme_toggle()
                        self.last_auto_switch_minute = current_minute_key
        except Exception as e:
            print(f"定时检查器错误: {e}")
        
        # 每60秒检查一次
        self.root.after(60000, self.schedule_checker)
    
    def execute_auto_theme_toggle(self):
        """执行自动主题切换（智能判断是否重启资源管理器）"""
        try:
            # 根据复选框状态选择执行的脚本
            if self.restart_explorer.get():
                script_path = self.resource_path("toggle_and_restart.bat")
            else:
                script_path = self.resource_path("toggle_theme.bat")
            
            subprocess.run([script_path], creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            # 延迟更新状态
            self.root.after(500, self.update_theme_status)
        except Exception as e:
            print(f"自动切换失败: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WindowsThemeSwitcher()
    app.run()