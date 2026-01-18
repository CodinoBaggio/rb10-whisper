import sys
import os
import ctypes
import tkinter as tk
from tkinter import messagebox

# 開発環境で実行する場合、sys.pathにsrcが認識されるようにする
# ただし、このスクリプトはルートにあるので、通常は import src.main がそのまま通るはず。

def check_single_instance():
    """多重起動防止チェック"""
    mutex_name = "Global\\RB10_WHISPER_MUTEX"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    
    ERROR_ALREADY_EXISTS = 183
    
    if last_error == ERROR_ALREADY_EXISTS:
        return False
    return True

if __name__ == "__main__":
    if not check_single_instance():
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("Warning", "rb10-whisper is already running.")
        sys.exit(0)

    try:
        from src.main import AudioInputApp
        app = AudioInputApp()
        app.run()
    except Exception as e:
        # 重大な起動エラー
        import traceback
        
        # エラーログ記録
        with open("fatal_error.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fatal Error", f"Failed to start application:\n{e}\n\nCheck fatal_error.log")
