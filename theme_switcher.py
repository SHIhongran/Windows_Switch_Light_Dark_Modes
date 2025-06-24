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

class WindowsThemeSwitcher:
    def __init__(self):
        self.root = tk.Tk()

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
        self.root.geometry("180x240")
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

        self.setup_window_style()
        self.create_ui()
        self.bind_events()
        self.update_theme_status()
        # self.center_window() # 删除此行

        # ---- 实现边缘启动逻辑 ----
        # 1. 立即设置初始停靠状态
        self.dock_side = 'right'  # 设置默认停靠在右侧
        self.is_docked = True
        self.is_hidden = True       # 立即将状态标记为隐藏

        # 2. 计算并设置边缘位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # X坐标：屏幕宽度 - 可见触发条的宽度
        x_pos = screen_width - self.DOCK_OFFSET
        
        # Y坐标：屏幕高度的一半 - 窗口高度的一半
        y_pos = (screen_height // 2) - (self.root.winfo_height() // 2)

        # 应用计算出的初始位置
        self.root.geometry(f'+{int(x_pos)}+{int(y_pos)}')

        # 3. 创建指示器并启动鼠标检测
        self.create_dock_indicator()
        self.start_mouse_check()

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
                                   command=self.execute_theme_toggle)
        self.toggle_btn.pack(pady=(0, 15))

        self.restart_check = tk.Checkbutton(self.content_frame,
                                          text="切换后重启资源管理器",
                                          variable=self.restart_explorer,
                                          font=('Microsoft YaHei UI', 8),
                                          wraplength=140)
        self.restart_check.pack()

        self.restart_now_btn = tk.Button(self.content_frame, text="立即重启资源管理器",
                                         font=('Microsoft YaHei UI', 9),
                                         border=0, cursor='hand2',
                                         padx=10, pady=5,
                                         command=self.execute_restart_explorer)
        self.restart_now_btn.pack(pady=(10, 0))

    def bind_events(self):
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.on_drag)
        self.root.bind('<ButtonRelease-1>', self.end_drag)
        self.root.bind('<Enter>', self.on_mouse_enter)
        self.root.bind('<Leave>', self.on_mouse_leave)
        for widget in self.root.winfo_children():
            self.bind_drag_events(widget)

    def bind_drag_events(self, widget):
        widget.bind('<Button-1>', self.start_drag)
        widget.bind('<B1-Motion>', self.on_drag)
        widget.bind('<ButtonRelease-1>', self.end_drag)
        widget.bind('<Enter>', self.on_mouse_enter)
        widget.bind('<Leave>', self.on_mouse_leave)
        for child in widget.winfo_children():
            self.bind_drag_events(child)

    def on_mouse_enter(self, event):
        if self.hide_timer_id:
            self.root.after_cancel(self.hide_timer_id)
            self.hide_timer_id = None

    def on_mouse_leave(self, event):
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
        self.start_mouse_check()

    def show_window(self):
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
        self.stop_mouse_check()

    def start_mouse_check(self):
        if self.mouse_check_running:
            return
        self.mouse_check_running = True
        self.mouse_check_thread = threading.Thread(target=self.mouse_check_loop, daemon=True)
        self.mouse_check_thread.start()

    def stop_mouse_check(self):
        self.mouse_check_running = False

    def mouse_check_loop(self):
        while self.mouse_check_running and self.is_hidden:
            try:
                mouse_x, mouse_y = self.get_mouse_position()
                if self.should_show_window(mouse_x, mouse_y):
                    self.root.after(0, self.show_window)
                    break
                time.sleep(0.1)
            except:
                break

    def should_show_window(self, mouse_x, mouse_y):
        screen_width = self.root.winfo_screenwidth()
        trigger_zone = 10
        if self.dock_side == 'left':
            return mouse_x <= trigger_zone
        elif self.dock_side == 'right':
            return mouse_x >= screen_width - trigger_zone
        elif self.dock_side == 'top':
            return mouse_y <= trigger_zone
        return False

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

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WindowsThemeSwitcher()
    app.run()