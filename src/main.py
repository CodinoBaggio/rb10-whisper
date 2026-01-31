import tkinter as tk
import threading
import keyboard
import pyperclip
import pyautogui
import os
import time
import sys
import traceback

# 3rd party
import pystray
from PIL import Image, ImageDraw

# ログ出力用関数
def log_error(msg):
    with open("error.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

# プロジェクトルートパスをsys.pathに追加して、srcモジュールを解決できるようにする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Windows環境でのTcl/Tkパス設定
# PyInstallerでビルドされた場合(frozen)は設定不要（内部に含まれるため）
# 開発環境のみ設定する
if not getattr(sys, 'frozen', False):
    tcl_lib = r"C:\Users\kensho\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
    tk_lib = r"C:\Users\kensho\AppData\Local\Programs\Python\Python313\tcl\tk8.6"
    if os.path.exists(tcl_lib):
        os.environ["TCL_LIBRARY"] = tcl_lib
        os.environ["TK_LIBRARY"] = tk_lib

try:
    try:
        from src.ui import OverlayWindow, SettingsWindow
        from src.audio import AudioRecorder
        from src.transcriber import Transcriber
        from src.config import ConfigManager
    except ImportError:
        # exe化された場合や src 内部から実行された場合のフォールバック
        # PyInstallerでは構造がフラットになることが多いため
        from ui import OverlayWindow, SettingsWindow
        from audio import AudioRecorder
        from transcriber import Transcriber
        from config import ConfigManager
except ImportError as e:
    log_error(f"Import Error: {e}\n{traceback.format_exc()}")
    try:
        import tkinter.messagebox
        root = tk.Tk()
        root.withdraw()
        tkinter.messagebox.showerror("Startup Error", f"Import Error:\n{e}")
    except:
        pass
    sys.exit(1)

def create_icon_image():
    """システムトレイ用のアイコン画像を生成する"""
    # 64x64のアイコンを作成
    # 高解像度で描画してから縮小してアンチエイリアスを効かせる
    size = 256
    # 最終出力サイズ
    target_size = 64
    
    # 背景: 透過
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    
    # 色定義
    bg_color = (32, 32, 32)      # ダークグレー
    mic_color = (0, 200, 160)    # 明るめのティール (Cyber Green)
    
    
    # 1. 背景円 (削除して透過に)
    # margin = 16
    # dc.ellipse((margin, margin, size - margin, size - margin), fill=bg_color)
    
    # 全体を大きくするためにスケールアップ (約1.8倍)
    # Canvas: 256x256
    cx, cy = size // 2, size // 2

    # 2. マイク本体 (カプセル)
    # 幅 48 -> 86, 高さ 80 -> 144
    mic_w = 86
    mic_h = 144
    # 重心を少し上にずらす
    mic_y_offset = -10 
    mic_rect = (cx - mic_w//2, cy - mic_h//2 + mic_y_offset, cx + mic_w//2, cy + mic_h//2 + mic_y_offset)
    dc.rounded_rectangle(mic_rect, radius=40, fill=mic_color)
    
    # 3. マイクホルダー (U字)
    # 幅 72 -> 130, 高さ 60 -> 108
    u_w = 130
    u_h = 108
    u_y_start = cy + mic_y_offset + 20
    u_rect = (cx - u_w//2, u_y_start, cx + u_w//2, u_y_start + u_h)
    
    # 線幅 12 -> 20
    stroke_width = 20
    
    dc.arc(u_rect, start=0, end=180, fill=mic_color, width=stroke_width)
    
    # 4. スタンド支柱
    # 高さ 30 -> 40 (少し短めにバランス調整)
    stand_h = 40
    stem_top = u_y_start + u_h // 2
    dc.line((cx, stem_top, cx, stem_top + stand_h), fill=mic_color, width=stroke_width)
    
    # 5. 台座
    # 幅 80 -> 140
    base_w = 140
    base_y = stem_top + stand_h
    dc.line((cx - base_w//2, base_y, cx + base_w//2, base_y), fill=mic_color, width=stroke_width)
    
    # リサイズ (LANCZOS)
    try:
        resample_filter = Image.Resampling.LANCZOS
    except AttributeError:
        # 古いPillow用
        resample_filter = Image.ANTIALIAS
        
    image = image.resize((target_size, target_size), resample=resample_filter)
    
    return image

class AudioInputApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() # メインウィンドウは隠す

        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.overlay = OverlayWindow(self.root)
        
        self.is_recording = False
        self.processing = False
        self.processing_start_time = 0
        self.last_toggle_time = 0
        self.tray_icon = None
        
        # ホットキー設定
        # keyboardライブラリのコールバックは別スレッドで実行されるため、
        # Tkinterの操作をメインスレッドで行うように after でラップする
        self.reload_hotkeys()
        
        self.last_watchdog_time = time.time()
        self.last_hotkey_reload_time = time.time()
        self._monitor_watchdog()
        
        self._check_api_key_on_startup()
        self._setup_tray_icon()

    def reload_hotkeys(self):
        """ホットキーを再登録する（フック消失対策）"""
        try:
            # 既存の全フックを解除
            keyboard.unhook_all()
            # 解除が確実にOS側に反映されるよう、最小限の待機（0.01s）
            time.sleep(0.01)
            
            hotkey = ConfigManager.get_hotkey()
            keyboard.add_hotkey(hotkey, lambda: self.root.after(0, self.toggle_recording))
            keyboard.add_hotkey('esc', lambda: self.root.after(0, self.cancel_recording))
            print(f"Hotkeys reloaded. Active hotkey: [{hotkey.upper()}]")
            self.last_hotkey_reload_time = time.time()
        except Exception as e:
            msg = f"Failed to reload hotkeys: {e}"
            print(msg)
            log_error(msg)

    def _monitor_watchdog(self):
        """
        システムの生存確認とスリープ復帰検知を行うウォッチドッグ
        """
        try:
            current_time = time.time()
            # 1. スリープ復帰検知
            # 予定より大きく時間が飛んでいたらスリープしていたとみなす
            # 監視間隔(5s) + マージン(3s) = 8s
            if current_time - self.last_watchdog_time > 8:
                print("System resume detected. Reloading hotkeys...")
                self.reload_hotkeys()
            
            # 2. 定期リフレッシュは廃止（ユーザー要望）
            # ロック解除検知は時間差分だけでは難しいが、
            # スリープを伴う運用であれば上記でカバーできる
            # elif (current_time - self.last_hotkey_reload_time > 60) and (not self.is_recording):
            #    print("Periodic hotkey refresh.")
            #    self.reload_hotkeys()

            self.last_watchdog_time = current_time
        except Exception as e:
            print(f"Watchdog Error: {e}")
        
        # 5秒後にまたチェック
        self.root.after(5000, self._monitor_watchdog)

    def _setup_tray_icon(self):
        """システムトレイアイコンの設定"""
        image = create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Settings", self._open_settings_from_tray),
            pystray.MenuItem("Exit", self._quit_app_from_tray)
        )
        self.tray_icon = pystray.Icon("rb10-whisper", image, "rb10-whisper", menu)

    def _open_settings_from_tray(self, icon, item):
        # トレイスレッドからTkinterスレッドへ依頼
        self.root.after(0, self._open_settings)

    def _quit_app_from_tray(self, icon, item):
        # トレイスレッドからTkinterスレッドへ依頼
        self.root.after(0, self._on_exit)

    def _check_api_key_on_startup(self):
        """起動時にAPIキーを確認"""
        print("Initializing application...")
        if not ConfigManager.has_valid_key():
            print("API Key not found. Opening settings...")
            self._open_settings()
        else:
            hotkey = ConfigManager.get_hotkey()
            print(f"Ready to record (Press {hotkey.upper()})")

    def _open_settings(self):
        """設定画面を開く"""
        # リスト選択式への変更に伴い、設定中のホットキー停止は不要（むしろ混乱の元）なため削除
            
        def on_close(saved):
            if saved == "hotkey_only":
                self.reload_hotkeys()
                print("Hotkey config updated via settings.")
            elif saved is True:
                self.transcriber.reload_key()
                self.reload_hotkeys()
                print("All settings reloaded.")
            else:
                # ウィンドウを閉じた際などは念のため最新状態で初期化
                self.reload_hotkeys()
                print("Settings window closed.")
                
        SettingsWindow(self.root, on_close_callback=on_close)

    def toggle_recording(self):
        """録音の開始/停止トグル"""
        current_time = time.time()
        if current_time - self.last_toggle_time < 0.5:
             # デバウンス: 0.5秒以内の連打は無視
            return
        self.last_toggle_time = current_time

        if not ConfigManager.has_valid_key():
            self._open_settings()
            return

        if self.processing:
            # スタック対策: 一定時間以上処理中の場合は強制リセット
            if time.time() - self.processing_start_time > 35:
                print("Warning: Processing state stuck. Force resetting.")
                self.processing = False
                self.overlay.hide()
            else:
                return # 処理中は無視

        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_and_transcribe()

    def start_recording(self):
        print("Start Recording...")
        self.is_recording = True
        self.overlay.show()
        
        # アイコンの状態を変えてもいいかも（赤くするとか）
        
        # UIスレッドからの更新用コールバック
        def update_volume_ui(vol):
            self.root.after(0, lambda: self.overlay.update_volume(vol))

        self.recorder.start(volume_callback=update_volume_ui)

    def stop_and_transcribe(self):
        print("Stop Recording...")
        self.is_recording = False
        self.processing = True
        self.processing_start_time = time.time()
        
        # Thinking表示
        self.overlay.set_thinking()
        
        # 録音停止・ファイル保存
        audio_path = self.recorder.stop()
        
        # 音量チェック (閾値以下の場合はスキップ)
        # RMS 0.01 はノイズをより確実に弾く設定
        if self.recorder.max_volume < 0.01:
            print(f"Skipping transcription (Input too quiet: {self.recorder.max_volume:.5f})")
            if audio_path and os.path.exists(audio_path):
                try: os.remove(audio_path)
                except: pass
            self.processing = False
            self.root.after(0, self.overlay.hide)
            return

        # 別スレッドで文字起こし実行（UIをフリーズさせないため）
        threading.Thread(target=self._transcribe_thread, args=(audio_path,)).start()

    def _transcribe_thread(self, audio_path):
        if not audio_path:
            self.processing = False
            self.root.after(0, self.overlay.hide)
            return

        try:
            text = self.transcriber.transcribe(audio_path)
            print(f"Transcribed: {text}")
            
            if text:
                # クリップボードにコピー & ペースト
                pyperclip.copy(text)
                
                # ペースト実行 (Ctrl+V)
                # 少し待ってから実行（クリップボード反映待ち）
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'v')
                
        except Exception as e:
            msg = f"Error: {e}"
            print(msg)
            log_error(msg)
        finally:
            # 一時ファイル削除
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
            
            self.processing = False
            self.root.after(0, self.overlay.hide)

    def cancel_recording(self):
        """録音キャンセル"""
        if self.is_recording:
            print("Cancelled.")
            self.is_recording = False
            audio_path = self.recorder.stop()
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
            self.overlay.hide()

    def run(self):
        # トレイアイコンを別スレッドで開始
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

        # Ctrl+C (SIGINT) を効くようにするハック
        self.root.after(100, self._check_signal)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_exit()
        except Exception as e:
            log_error(f"Runtime Error: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")

    def _check_signal(self):
        # 何もしないが、これでPythonがシグナルを処理できる
        self.root.after(100, self._check_signal)

    def _on_exit(self):
        print("\nExiting application...")
        if hasattr(self, 'recorder'):
            self.recorder.stop()
        
        # トレイアイコン停止
        if self.tray_icon:
            self.tray_icon.stop()
            
        try:
            self.root.destroy()
        except:
            pass
        sys.exit(0)

if __name__ == "__main__":
    try:
        app = AudioInputApp()
        app.run()
    except Exception as e:
        log_error(f"Fatal Startup Error: {e}\n{traceback.format_exc()}")
        try:
            import tkinter.messagebox
            root = tk.Tk()
            root.withdraw()
            tkinter.messagebox.showerror("Startup Error", f"Fatal Error:\n{e}")
        except:
             pass
