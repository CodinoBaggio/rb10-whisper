import sys
import os
import ctypes
import traceback

def log_fatal_error(message):
    with open("fatal_error.log", "w", encoding="utf-8") as f:
        f.write(message)

try:
    # PyInstaller OneFileモードのDLLロード対策
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # sys.pathに一時ディレクトリを追加
        if sys._MEIPASS not in sys.path:
            sys.path.append(sys._MEIPASS)
        
        try:
            os.add_dll_directory(sys._MEIPASS)
        except Exception:
            pass 

    import tkinter as tk
    from tkinter import messagebox
except Exception as e:
    err_msg = f"Failed to import tkinter:\n{traceback.format_exc()}\n\n"
    # デバッグ情報
    if hasattr(sys, '_MEIPASS'):
        meipass = sys._MEIPASS
        err_msg += f"sys._MEIPASS: {meipass}\n"
        
        # クリティカルなファイルの存在確認
        check_files = ['_tkinter.pyd', 'tcl86t.dll', 'tk86t.dll', 'base_library.zip']
        for f in check_files:
            f_path = os.path.join(meipass, f)
            exists = os.path.exists(f_path)
            err_msg += f"File '{f}': {'FOUND' if exists else 'NOT FOUND'} ({f_path})\n"
            
        # _tcl_dataチェック
        tcl_data_path = os.path.join(meipass, '_tcl_data')
        err_msg += f"Dir '_tcl_data': {'FOUND' if os.path.isdir(tcl_data_path) else 'NOT FOUND'}\n"

    err_msg += f"sys.path:\n" + "\n".join(sys.path) + "\n"
    
    log_fatal_error(err_msg)
    sys.exit(1)

# 開発環境で実行する場合、sys.pathにsrcが認識されるようにする

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
