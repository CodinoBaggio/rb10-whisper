import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser
import sounddevice as sd
from src.config import ConfigManager
import math
import keyboard
import threading

class SettingsWindow:
    """APIキー設定ウィンドウ"""
    def __init__(self, root, on_close_callback=None):
        self.root = root
        self.on_close_callback = on_close_callback
        
        self.window = tk.Toplevel(root)
        self.window.title("Settings")
        self.window.geometry("800x500")
        self.window.resizable(True, True)
        self.window.attributes('-topmost', True)
        
        # モーダルウィンドウのように振る舞う
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()
        
        self._setup_ui()
        
        # ウィンドウが閉じられたときの処理
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        # 色定義
        bg_color = "#202020"
        fg_color = "#ffffff"
        btn_bg = "#00aa88"
        btn_active = "#00ccaa"
        save_btn_bg = "#444444"
        
        self.window.configure(bg=bg_color)
        
        # スタイル設定（Combobox用）
        style = ttk.Style()
        style.theme_use('default')
        # readonly状態の時の背景色と文字色を強制指定
        style.map('TCombobox', 
                  fieldbackground=[('readonly', '#333333')],
                  foreground=[('readonly', 'white')],
                  background=[('readonly', '#444444')])
        style.configure("TCombobox", fieldbackground="#333333", background="#444444", foreground="white", borderwidth=0)
        
        # プルダウン（リスト部分）の色設定
        self.window.option_add("*TCombobox*Listbox.background", "#1a1a1a")
        self.window.option_add("*TCombobox*Listbox.foreground", "white")
        self.window.option_add("*TCombobox*Listbox.selectBackground", btn_bg)
        self.window.option_add("*TCombobox*Listbox.selectForeground", "white")
        
        # 説明ラベル
        lbl_desc = tk.Label(self.window, text="OpenAI APIキーを入力してください。\n音声認識機能を使用するために必要です。", 
                           justify=tk.LEFT, padx=20, pady=10, bg=bg_color, fg=fg_color)
        lbl_desc.pack(anchor='w')
        
        # リンク
        link_lbl = tk.Label(self.window, text="APIキーの取得方法はこちら", fg="#4da6ff", cursor="hand2", padx=20, bg=bg_color)
        link_lbl.pack(anchor='w')
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open_new("https://platform.openai.com/account/api-keys"))
        
        # APIキーコンテナ
        input_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        input_container.pack(fill='x')
        
        tk.Label(input_container, text="API Key:", bg=bg_color, fg=fg_color).pack(anchor='w')
        
        # APIキー入力行
        row_frame = tk.Frame(input_container, bg=bg_color)
        row_frame.pack(fill='x', pady=5)
        
        self.api_key_var = tk.StringVar(value=ConfigManager.load_api_key())
        self.api_key_visible = False
        
        self.entry = tk.Entry(row_frame, textvariable=self.api_key_var, show="*", 
                             bg="#333333", fg="white", insertbackground="white", relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)
        
        self.btn_toggle_api = tk.Button(row_frame, text="👁", command=self._toggle_api_visibility,
                                     bg="#444444", fg="white", activebackground="#555555",
                                     relief=tk.FLAT, width=4, font=("Helvetica", 12), cursor="hand2")
        self.btn_toggle_api.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_save_key = tk.Button(row_frame, text="Save Key", command=self._save_api_key,
                                    bg=btn_bg, fg="white", activebackground=btn_active,
                                    relief=tk.FLAT, width=10, font=("Helvetica", 10, "bold"), cursor="hand2")
        self.btn_save_key.pack(side=tk.LEFT, padx=(10, 0))

        # ホットキー設定コンテナ
        hotkey_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        hotkey_container.pack(fill='x')
        
        tk.Label(hotkey_container, text="Recording Hotkey:", bg=bg_color, fg=fg_color).pack(anchor='w')
        
        hotkey_row = tk.Frame(hotkey_container, bg=bg_color)
        hotkey_row.pack(fill='x', pady=5)
        
        self.hotkey_var = tk.StringVar(value=ConfigManager.get_hotkey())
        
        hotkey_options = ["fn", "alt", "ctrl", "shift"]
        self.hotkey_combo = ttk.Combobox(hotkey_row, textvariable=self.hotkey_var, values=hotkey_options, state="readonly")
        self.hotkey_combo.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)
        
        self.btn_apply_hotkey = tk.Button(hotkey_row, text="Apply Hotkey", command=self._apply_hotkey,
                                        bg=btn_bg, fg="white", activebackground=btn_active,
                                        relief=tk.FLAT, width=12, font=("Helvetica", 10, "bold"), cursor="hand2")
        self.btn_apply_hotkey.pack(side=tk.LEFT, padx=(10, 0))
        
        lbl_hotkey_desc = tk.Label(hotkey_container, text="設定を変更したら「Apply Hotkey」を押してください\n※FnキーはWindowsの仕様上、機能しない場合があります。",
                                  bg=bg_color, fg="#aaaaaa", font=("Helvetica", 9), justify=tk.LEFT)
        lbl_hotkey_desc.pack(anchor='w')

        # マイク選択コンテナ
        mic_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        mic_container.pack(fill='x')

        tk.Label(mic_container, text="Microphone:", bg=bg_color, fg=fg_color).pack(anchor='w')

        mic_row = tk.Frame(mic_container, bg=bg_color)
        mic_row.pack(fill='x', pady=5)

        system_default = "System Default"
        try:
            all_devices = sd.query_devices()
            input_device_names = [
                d['name'] for d in all_devices if d['max_input_channels'] > 0
            ]
        except Exception:
            input_device_names = []
        mic_options = [system_default] + input_device_names

        current_mic = ConfigManager.get_mic_device()
        initial_mic = current_mic if current_mic in input_device_names else system_default
        self.mic_var = tk.StringVar(value=initial_mic)

        self.mic_combo = ttk.Combobox(mic_row, textvariable=self.mic_var,
                                      values=mic_options, state="readonly")
        self.mic_combo.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)

        self.btn_apply_mic = tk.Button(mic_row, text="Apply Mic", command=self._apply_mic,
                                       bg=btn_bg, fg="white", activebackground=btn_active,
                                       relief=tk.FLAT, width=12,
                                       font=("Helvetica", 10, "bold"), cursor="hand2")
        self.btn_apply_mic.pack(side=tk.LEFT, padx=(10, 0))

        lbl_mic_desc = tk.Label(mic_container,
                                text="設定を変更したら「Apply Mic」を押してください",
                                bg=bg_color, fg="#aaaaaa", font=("Helvetica", 9),
                                justify=tk.LEFT)
        lbl_mic_desc.pack(anchor='w')

        # 下部の閉じるボタンエリア
        close_container = tk.Frame(self.window, padx=20, pady=20, bg=bg_color)
        close_container.pack(side=tk.BOTTOM, fill='x')

        self.btn_close = tk.Button(close_container, text="Close Settings", command=self._on_close_clicked,
                                         bg="#444444", fg="white", activebackground="#555555",
                                         relief=tk.FLAT, height=1, font=("Helvetica", 10), cursor="hand2")
        self.btn_close.pack(side=tk.RIGHT)

    def _toggle_api_visibility(self):
        """APIキーの伏せ字表示を切り替え"""
        if self.api_key_visible:
            self.entry.config(show="*")
            self.btn_toggle_api.config(text="👁")
            self.api_key_visible = False
        else:
            self.entry.config(show="")
            self.btn_toggle_api.config(text="🙈")
            self.api_key_visible = True

    def _set_cursor(self, cursor_type):
        """カーソルを切り替える (例: 'watch', 'arrow', '')"""
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.config(cursor=cursor_type)
            self.window.update_idletasks()

    def _save_api_key(self):
        """APIキーのみを保存"""
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showerror("Error", "API Key is empty.")
            return

        self._set_cursor("watch")
        
        def task():
            try:
                ConfigManager.save_api_key(key)
                self.window.after(0, lambda: self._on_save_completed("API Key saved!"))
                # メインスレッドでコールバック（キー再読み込み）を呼ぶ
                if self.on_close_callback:
                    self.window.after(0, lambda: self.on_close_callback(True))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", f"Failed to save key: {e}"))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))

        threading.Thread(target=task, daemon=True).start()

    def _apply_hotkey(self):
        """ホットキーのみを適用"""
        hotkey = self.hotkey_var.get().strip()
        if not hotkey:
            return

        self._set_cursor("watch")
        
        def task():
            try:
                ConfigManager.set_hotkey(hotkey)
                # メインスレッドでコールバック（ホットキー再読み込み）を呼ぶ
                if self.on_close_callback:
                    # saved=True で呼ぶが、ウィンドウは閉じないように main.py 側も調整が必要
                    # あるいは直接新しい反映メソッドを設ける
                    # ここでは既存の仕組み(on_close_callback)を利用しつつ、main.py 側で
                    # 「保存のみ（ウィンドウ閉じない）」パターンを想定するか
                    # とりあえず現状は保存だけして通知する
                    self.window.after(0, lambda: self._on_save_completed(f"Hotkey [{hotkey.upper()}] applied!"))
                    # reload_hotkeys を即座に呼ぶためにコールバック実行
                    self.window.after(0, lambda: self.on_close_callback("hotkey_only"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", f"Failed to apply hotkey: {e}"))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))

        threading.Thread(target=task, daemon=True).start()

    def _apply_mic(self):
        """マイク設定を適用"""
        selected = self.mic_var.get().strip()
        if not selected:
            return

        self._set_cursor("watch")

        def task():
            try:
                name_to_save = None if selected == "System Default" else selected
                ConfigManager.set_mic_device(name_to_save)
                label = "System Default" if name_to_save is None else selected
                self.window.after(0, lambda: self._on_save_completed(f"Mic [{label}] applied!"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", f"Failed to apply mic: {e}"))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))

        threading.Thread(target=task, daemon=True).start()

    def _on_save_completed(self, message):
        """保存完了時の通知"""
        messagebox.showinfo("Success", message)
        self.window.destroy()

    def _on_close_clicked(self):
        """Closeボタンが押されたとき"""
        self.window.destroy()

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback(False)
        self.window.destroy()

class OverlayWindow:
    """録音中のモダンなビジュアライザーオーバーレイ"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(root)
        
        # ウィンドウ設定
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.8) # 透過度
        
        # 画面中央下に配置
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        width = 320
        height = 80
        x = (screen_width - width) // 2
        y = screen_height - height - 120
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # モダンな背景色
        self.bg_color = "#1a1a1a"
        self.canvas = tk.Canvas(self.window, width=width, height=height, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()
        
        self.bars = []
        self.num_bars = 100 # 多すぎず、かつ高密度なバランス
        self.bar_width = 1   # 最小の細さ
        self.bar_spacing = 2 # 間隔を広げて独立した「線」に見せる
        
        # 配色：録音中（ティールからパープル）
        self.rec_colors = self._generate_gradient("#00f5d4", "#9b5de5", self.num_bars)
        # 配色：思考中（赤からピンクへのグラデーション）
        self.thinking_colors = self._generate_gradient("#ff0000", "#ff69b4", self.num_bars)
        
        self.colors = self.rec_colors # 初期カラー
        self._init_bars(width, height)
        self.window.withdraw()
        
        self.is_visible = False
        self.is_thinking = False
        self.current_volume = 0.0

    def _generate_gradient(self, start_hex, end_hex, steps):
        """グラデーションカラーを生成"""
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        
        s_rgb = hex_to_rgb(start_hex)
        e_rgb = hex_to_rgb(end_hex)
        
        gradient = []
        for i in range(steps):
            ratio = i / (steps - 1)
            r = int(s_rgb[0] + (e_rgb[0] - s_rgb[0]) * ratio)
            g = int(s_rgb[1] + (e_rgb[1] - s_rgb[1]) * ratio)
            b = int(s_rgb[2] + (e_rgb[2] - s_rgb[2]) * ratio)
            gradient.append(f'#{r:02x}{g:02x}{b:02x}')
        return gradient

    def _init_bars(self, width, height):
        self.canvas_height = height
        total_width = (self.bar_width * self.num_bars) + (self.bar_spacing * (self.num_bars - 1))
        start_x = (width - total_width) / 2
        
        center_y = height / 2
        for i in range(self.num_bars):
            x = start_x + (i * (self.bar_width + self.bar_spacing)) + (self.bar_width / 2)
            # 描画負荷が低い create_line で角丸を表現
            bar = self.canvas.create_line(x, center_y - 2, x, center_y + 2, 
                                        fill=self.colors[i], width=self.bar_width, capstyle='round')
            self.bars.append(bar)

    def show(self):
        self.is_thinking = False
        self.current_volume = 0.0
        
        # 表示前に色を録音中用(rec_colors)にリセット
        for i, bar in enumerate(self.bars):
            self.canvas.itemconfig(bar, fill=self.rec_colors[i])
        
        # 描画を強制的に反映させてからウィンドウを表示する
        self.canvas.update_idletasks()
        
        self.window.deiconify()
        self.is_visible = True
        self._draw_frame() # 描画ループ開始

    def hide(self):
        self.is_thinking = False
        self.is_visible = False
        
        # 隠す前に色を録音中用(rec_colors)にリセットしておく（次回表示時のフラッシング防止）
        for i, bar in enumerate(self.bars):
            self.canvas.itemconfig(bar, fill=self.rec_colors[i])
        self.canvas.update_idletasks()
        
        self.window.withdraw()

    def update_volume(self, volume):
        """音量に合わせてバーを更新"""
        if not self.is_visible or self.is_thinking:
            return
        
        # なめらかな追従
        alpha = 0.3 # 前回の値をどれだけ残すか
        self.current_volume = self.current_volume * alpha + volume * (1 - alpha)

    def _draw_frame(self):
        """アニメーションのメインループ (60fps目標)"""
        if not self.is_visible:
            return

        import time
        t = time.time()
        center_y = self.canvas_height / 2
        
        # 心拍リズムの計算 (ドクッ、ドクッ...)
        pulse = 0.0
        if self.is_thinking:
            # 二峰性拍動 (systole: 大, diastole: 小)
            # 周期を約1.2秒に設定
            cycle_t = (t * 0.8) % 1.0
            # 第1波（ドクッ）
            pulse1 = math.exp(-((cycle_t - 0.2)**2) / (2 * 0.05**2)) * 1.0
            # 第2波（ドクッ）
            pulse2 = math.exp(-((cycle_t - 0.45)**2) / (2 * 0.04**2)) * 0.4
            pulse = pulse1 + pulse2

        for i, bar in enumerate(self.bars):
            norm_pos = i / (self.num_bars - 1)
            dist = abs(norm_pos - 0.5)
            envelope = math.exp(-(dist**2) / (2 * 0.18**2)) # 広がりを微調整
            
            if self.is_thinking:
                # 思考中：心音アニメーション（ベース高を録音待機時と同じ 3px に合わせる）
                delay = dist * 0.4
                p = (t * 0.8 - delay) % 1.0
                p1 = math.exp(-((p - 0.2)**2) / (2 * 0.05**2)) * 1.0
                p2 = math.exp(-((p - 0.45)**2) / (2 * 0.04**2)) * 0.4
                local_pulse = (p1 + p2) * envelope
                
                # ベース高 3 + 拍動分 40
                h = 3 + 40 * local_pulse
                h = max(3, h)
                
                if local_pulse > 0.4: 
                    self.canvas.itemconfig(bar, fill="#ffb6c1") # ライトピンクで発光感を出す (白を廃止)
                else:
                    self.canvas.itemconfig(bar, fill=self.thinking_colors[i])
            else:
                # 録音中：音量反応
                anim_t = t * 6
                wave = (math.sin(norm_pos * 14 + anim_t) * 0.2 + 
                       math.sin(norm_pos * 9 - anim_t * 0.5) * 0.1 + 0.7)
                # ベース高 3
                h = 3 + (self.canvas_height * self.current_volume * 1.6) * envelope * wave
                h = max(3, min(self.canvas_height - 6, h))
                self.canvas.itemconfig(bar, fill=self.rec_colors[i])
            
            # 座標更新
            x, _, _, _ = self.canvas.coords(bar)
            half_h = h / 2
            self.canvas.coords(bar, x, center_y - half_h, x, center_y + half_h)

        # 16ms間隔で更新 (約60fps)
        self.root.after(16, self._draw_frame)

    def set_thinking(self):
        self.is_thinking = True
        # _draw_frame は show() からループし続けているのでフラグ切り替えのみでOK
