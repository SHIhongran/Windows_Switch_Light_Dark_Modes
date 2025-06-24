import tkinter as tk
import tkinter.ttk as ttk
import subprocess
import winreg
import sys
import os
import ctypes
from ctypes import wintypes
import threading
import time

class WindowsThemeSwitcher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        # 窗口尺寸 (3:4 竖直宽高比)
        self.window_width = 180
        self.window_height = 240
        
        # 拖动相关变量
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        
        # 吸附相关变量
        self.docked_edge = None  # 'left', 'right', 'top', 'bottom'
        self.DOCK_OFFSET = 3  # 隐藏时可见像素数
        self.is_hidden = False
        
        # 鼠标检测相关
        self.mouse_check_thread = None
        self.mouse_check_running = False
        
        # 自动隐藏计时器
        self.hide_timer = None
        
        # 收缩状态指示器
        self.dock_indicator = None
        
        # 颜色主题定义
        self.light_theme_colors = {
            'bg': '#f5f7fc',
            'fg': '#333333',
            'btn_bg': '#e8ecf4',
            'btn_active_bg': '#dfe4ee',
            'troughcolor': '#e8ecf4',
            'activebackground': '#dfe4ee'
        }
        
        self.dark_theme_colors = {
            'bg': '#17191f',
            'fg': '#e0e0e0',
            'btn_bg': '#2c2f3a',
            'btn_active_bg': '#3a3e4c',
            'troughcolor': '#2c2f3a',
            'activebackground': '#3a3e4c'
        }
        
        self.setup_window()
        self.create_ui()
        self.bind_events()
        self.center_window()
        self.update_theme_status()
        self.update_ui_theme()
        
    def setup_window(self):
        """设置窗口基本属性"""
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(False, False)
        
    def create_ui(self):
        """创建用户界面"""
        # 主容器
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 内容容器，用于居中
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.place(relx=0.5, rely=0.5, anchor='center')

        # 关闭按钮
        self.close_btn = tk.Button(self.root, text="×",
                                 font=('Arial', 10, 'bold'),
                                 border=0, cursor='hand2',
                                 command=self.root.quit)
        self.close_btn.place(x=self.window_width - 25, y=5, width=20, height=20)
        
        # 状态标签
        self.status_label = tk.Label(self.content_frame, text="Current Theme: Light", font=("Microsoft YaHei UI", 9))
        self.status_label.pack(pady=(0, 15))
        
        # 主题切换按钮
        self.theme_button = tk.Button(self.content_frame, text="Switch to Dark Mode", 
                                    command=self.execute_theme_toggle, relief=tk.FLAT, font=("Microsoft YaHei UI", 10, 'bold'),
                                    padx=25, pady=10)
        self.theme_button.pack(pady=(0, 15))
        
        # 重启选项复选框
        self.restart_var = tk.BooleanVar(value=True)
        self.restart_checkbox = tk.Checkbutton(self.content_frame, text="切换后重启资源管理器", 
                                             variable=self.restart_var, font=("Microsoft YaHei UI", 8))
        self.restart_checkbox.pack()
        
        # 独立重启按钮
        self.restart_button = tk.Button(self.content_frame, text="立即重启资源管理器", 
                                      command=self.execute_restart_explorer, relief=tk.FLAT, font=("Microsoft YaHei UI", 9),
                                      padx=10, pady=5)
        self.restart_button.pack(pady=(10, 0))
        
        # 电源设置被移除，因为旧版UI没有此功能

    def bind_events(self):
        """绑定事件"""
        # 拖动事件
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.on_drag)
        self.root.bind('<ButtonRelease-1>', self.end_drag)
        
        # 鼠标进入/离开事件
        self.root.bind('<Enter>', self.on_mouse_enter)
        self.root.bind('<Leave>', self.on_mouse_leave)
        
        # 为所有子控件绑定拖动事件
        for widget in self.get_all_children(self.root):
            # 不为关闭按钮绑定拖动事件
            if widget == self.close_btn:
                continue
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.on_drag)
            widget.bind('<ButtonRelease-1>', self.end_drag)
            
    def get_all_children(self, widget):
        """递归获取所有子控件"""
        children = []
        for child in widget.winfo_children():
            children.append(child)
            children.extend(self.get_all_children(child))
        return children
        
    def start_drag(self, event):
        """开始拖动"""
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.is_dragging = True
        
        # 如果窗口是隐藏状态，先显示出来
        if self.is_hidden:
            self.show_window()
            
    def on_drag(self, event):
        """拖动过程中"""
        if self.is_dragging:
            x = self.root.winfo_x() + (event.x_root - self.drag_start_x)
            y = self.root.winfo_y() + (event.y_root - self.drag_start_y)
            self.root.geometry(f"+{x}+{y}")
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
            
    def end_drag(self, event):
        """结束拖动"""
        self.is_dragging = False
        self.check_dock()
        
    def check_dock(self):
        """检查是否需要吸附到边缘"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        
        # 检查边缘吸附
        if x <= 20:  # 左边缘
            self.dock('left')
        elif x + self.window_width >= screen_width - 20:  # 右边缘
            self.dock('right')
        elif y <= 20:  # 上边缘
            self.dock('top')
        elif y + self.window_height >= screen_height - 20:  # 下边缘
            self.dock('bottom')
        else:
            self.undock()
            
    def dock(self, edge):
        """吸附到指定边缘"""
        self.docked_edge = edge
        self.hide_window()
        self.start_mouse_check()
        
    def undock(self):
        """取消吸附"""
        if self.docked_edge:
            self.docked_edge = None
            self.is_hidden = False
            self.stop_mouse_check()
            self.remove_dock_indicator()
            
    def hide_window(self):
        """隐藏窗口到边缘"""
        if not self.docked_edge:
            return
            
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if self.docked_edge == 'left':
            new_x = -self.window_width + self.DOCK_OFFSET
            new_y = self.root.winfo_y()
        elif self.docked_edge == 'right':
            new_x = screen_width - self.DOCK_OFFSET
            new_y = self.root.winfo_y()
        elif self.docked_edge == 'top':
            new_x = self.root.winfo_x()
            new_y = -self.window_height + self.DOCK_OFFSET
        elif self.docked_edge == 'bottom':
            new_x = self.root.winfo_x()
            new_y = screen_height - self.DOCK_OFFSET
            
        self.root.geometry(f"+{new_x}+{new_y}")
        self.is_hidden = True
        self.create_dock_indicator()
        
    def show_window(self):
        """显示窗口"""
        if not self.is_hidden or not self.docked_edge:
            return
            
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if self.docked_edge == 'left':
            new_x = 0
            new_y = self.root.winfo_y()
        elif self.docked_edge == 'right':
            new_x = screen_width - self.window_width
            new_y = self.root.winfo_y()
        elif self.docked_edge == 'top':
            new_x = self.root.winfo_x()
            new_y = 0
        elif self.docked_edge == 'bottom':
            new_x = self.root.winfo_x()
            new_y = screen_height - self.window_height
            
        self.root.geometry(f"+{new_x}+{new_y}")
        self.is_hidden = False
        self.remove_dock_indicator()
        
    def create_dock_indicator(self):
        """创建收缩状态指示器"""
        if self.dock_indicator:
            return
            
        self.dock_indicator = tk.Toplevel()
        self.dock_indicator.overrideredirect(True)
        self.dock_indicator.attributes('-topmost', True)
        
        # 根据当前主题设置颜色
        current_theme = self.get_current_theme()
        if current_theme == 'light':
            indicator_color = '#FFFFFF'  # 白色
        else:
            indicator_color = '#000000'  # 黑色
            
        self.dock_indicator.configure(bg=indicator_color)
        
        # 设置指示器位置和大小
        if self.docked_edge in ['left', 'right']:
            width = self.DOCK_OFFSET
            height = self.window_height
        else:
            width = self.window_width
            height = self.DOCK_OFFSET
            
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        
        if self.docked_edge == 'right':
            x = self.root.winfo_x() + self.window_width - self.DOCK_OFFSET
        elif self.docked_edge == 'bottom':
            y = self.root.winfo_y() + self.window_height - self.DOCK_OFFSET
            
        self.dock_indicator.geometry(f"{width}x{height}+{x}+{y}")
        
    def remove_dock_indicator(self):
        """移除收缩状态指示器"""
        if self.dock_indicator:
            self.dock_indicator.destroy()
            self.dock_indicator = None
            
    def update_dock_indicator_color(self):
        """更新收缩状态指示器颜色"""
        if self.dock_indicator:
            current_theme = self.get_current_theme()
            if current_theme == 'light':
                indicator_color = '#FFFFFF'  # 白色
            else:
                indicator_color = '#000000'  # 黑色
            self.dock_indicator.configure(bg=indicator_color)
            
    def start_mouse_check(self):
        """开始鼠标位置检测"""
        if not self.mouse_check_running:
            self.mouse_check_running = True
            self.mouse_check_thread = threading.Thread(target=self.mouse_check_loop, daemon=True)
            self.mouse_check_thread.start()
            
    def stop_mouse_check(self):
        """停止鼠标位置检测"""
        self.mouse_check_running = False
        
    def mouse_check_loop(self):
        """鼠标位置检测循环"""
        while self.mouse_check_running:
            if self.should_show_window():
                self.root.after(0, self.show_window)
            time.sleep(0.1)
            
    def should_show_window(self):
        """判断是否应该显示窗口"""
        if not self.is_hidden or not self.docked_edge:
            return False
            
        mouse_x, mouse_y = self.get_mouse_position()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        trigger_zone = 10  # 触发区域像素
        
        if self.docked_edge == 'left' and mouse_x <= trigger_zone:
            return True
        elif self.docked_edge == 'right' and mouse_x >= screen_width - trigger_zone:
            return True
        elif self.docked_edge == 'top' and mouse_y <= trigger_zone:
            return True
        elif self.docked_edge == 'bottom' and mouse_y >= screen_height - trigger_zone:
            return True
            
        return False
        
    def get_mouse_position(self):
        """获取鼠标位置"""
        try:
            point = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            return point.x, point.y
        except:
            return 0, 0
            
    def on_mouse_enter(self, event):
        """鼠标进入窗口"""
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
            self.hide_timer = None
            
    def on_mouse_leave(self, event):
        """鼠标离开窗口"""
        if self.docked_edge and not self.is_hidden:
            self.hide_timer = self.root.after(500, self.hide_window)
            
    def center_window(self):
        """窗口居中"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        
        self.root.geometry(f"+{x}+{y}")
        
    def get_current_theme(self):
        """获取当前系统主题"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except:
            return "light"
            
    def update_theme_status(self):
        """更新主题状态显示"""
        current_theme = self.get_current_theme()
        
        if current_theme == "light":
            self.status_label.config(text="Current Theme: Light")
            self.theme_button.config(text="Switch to Dark Mode")
        else:
            self.status_label.config(text="Current Theme: Dark")
            self.theme_button.config(text="Switch to Light Mode")
            
        # 更新UI主题和指示器颜色
        self.update_ui_theme()
        self.update_dock_indicator_color()
        
    def update_ui_theme(self):
        """更新UI主题颜色"""
        current_theme = self.get_current_theme()
        colors = self.light_theme_colors if current_theme == 'light' else self.dark_theme_colors
        
        # 更新窗口背景
        self.root.configure(bg=colors['bg'])
        
        # 更新所有Frame
        for widget in [self.main_frame, self.content_frame]:
            widget.configure(bg=colors['bg'])
            
        # 更新所有Label
        self.status_label.configure(bg=colors['bg'], fg=colors['fg'])
            
        # 更新所有Button
        for widget in [self.theme_button, self.restart_button]:
            widget.configure(bg=colors['btn_bg'], fg=colors['fg'], 
                           activebackground=colors['btn_active_bg'], relief=tk.FLAT)
        
        # 更新关闭按钮颜色
        self.close_btn.configure(bg=colors['bg'], fg=colors['fg'], activebackground=colors['btn_active_bg'])

        # 更新Checkbutton
        self.restart_checkbox.configure(bg=colors['bg'], fg=colors['fg'], 
                                      selectcolor=colors['bg'], activebackground=colors['bg'])
        
        # 电源相关的UI更新被移除
        
    def execute_theme_toggle(self):
        """执行主题切换"""
        try:
            if self.restart_var.get():
                # 切换主题并重启资源管理器
                script_path = self.get_resource_path("toggle_and_restart.bat")
            else:
                # 仅切换主题
                script_path = self.get_resource_path("toggle_theme.bat")
                
            subprocess.run([script_path], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 延迟更新状态，等待注册表更改生效
            self.root.after(1000, self.update_theme_status)
        except Exception as e:
            print(f"Error executing theme toggle: {e}")
            
    def execute_restart_explorer(self):
        """执行重启资源管理器"""
        try:
            script_path = self.get_resource_path("restart_explorer_only.bat")
            subprocess.run([script_path], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error restarting explorer: {e}")
            
    def on_sleep_change(self, value):
        """睡眠时间滑条变化处理"""
        v = int(value)
        
        if v == 25:
            # 最右端：从不睡眠
            self.sleep_label.config(text="睡眠设置: 从不")
            minutes = 0
        else:
            # 1-24：对应5-120分钟
            minutes = v * 5
            self.sleep_label.config(text=f"睡眠设置: {minutes} 分钟")
            
        # 设置系统睡眠时间
        self.set_sleep_timeout(minutes)
        
    def set_sleep_timeout(self, minutes):
        """设置系统睡眠时间"""
        try:
            # 设置AC电源睡眠时间
            subprocess.run(['powercfg', '/change', 'standby-timeout-ac', str(minutes)], 
                         creationflags=subprocess.CREATE_NO_WINDOW)
            # 设置DC电源睡眠时间
            subprocess.run(['powercfg', '/change', 'standby-timeout-dc', str(minutes)], 
                         creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error setting sleep timeout: {e}")
            
    def get_resource_path(self, relative_path):
        """获取资源文件路径"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
        
    def run(self):
        """运行程序"""
        try:
            self.root.mainloop()
        finally:
            self.stop_mouse_check()
            self.remove_dock_indicator()

if __name__ == "__main__":
    app = WindowsThemeSwitcher()
    app.run()