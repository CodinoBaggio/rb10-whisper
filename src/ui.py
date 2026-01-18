import tkinter as tk
from tkinter import messagebox
import webbrowser
from src.config import ConfigManager
import math

class SettingsWindow:
    """APIキー設定ウィンドウ"""
    def __init__(self, root, on_close_callback=None):
        self.root = root
        self.on_close_callback = on_close_callback
        
        self.window = tk.Toplevel(root)
        self.window.title("API Key Setup")
        self.window.geometry("720x220")
        self.window.resizable(True, True)
        self.window.attributes('-topmost', True)
        
        # モーダルウィンドウのように振る舞う
        # rootがwithdrawされている状態でtransientにすると表示されないことがあるためコメントアウト
        # self.window.transient(root)
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
        accent_color = "#00ffcc"
        btn_bg = "#00aa88"
        btn_active = "#00ccaa"
        
        self.window.configure(bg=bg_color)
        
        # 説明ラベル
        lbl_desc = tk.Label(self.window, text="OpenAI APIキーを入力してください。\n音声認識機能を使用するために必要です。", 
                           justify=tk.LEFT, padx=20, pady=10, bg=bg_color, fg=fg_color)
        lbl_desc.pack(anchor='w')
        
        # リンク
        link_lbl = tk.Label(self.window, text="APIキーの取得方法はこちら", fg="#4da6ff", cursor="hand2", padx=20, bg=bg_color)
        link_lbl.pack(anchor='w')
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open_new("https://platform.openai.com/account/api-keys"))
        
        # 入力フィールドコンテナ
        input_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        input_container.pack(fill='x')
        
        tk.Label(input_container, text="API Key:", bg=bg_color, fg=fg_color).pack(anchor='w')
        
        # 入力行フレーム（EntryとButtonを横並び）
        row_frame = tk.Frame(input_container, bg=bg_color)
        row_frame.pack(fill='x', pady=5)
        
        self.api_key_var = tk.StringVar(value=ConfigManager.load_api_key())
        
        # Entry (左側、広がる)
        self.entry = tk.Entry(row_frame, textvariable=self.api_key_var, show="*", 
                             bg="#333333", fg="white", insertbackground="white", relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)
        
        # 保存ボタン (右側、アイコン)
        # Unicodeのチェックマークを使用
        self.btn_save = tk.Button(row_frame, text="✔", command=self._save_and_close, 
                                 bg=btn_bg, fg="white", activebackground=btn_active, activeforeground="white",
                                 relief=tk.FLAT, width=4, font=("Helvetica", 12, "bold"), cursor="hand2")
        self.btn_save.pack(side=tk.LEFT, padx=(10, 0)) # 左に少しマージン
        
        # ホバーエフェクト
        def on_enter(e):
            self.btn_save['bg'] = btn_active
        def on_leave(e):
            self.btn_save['bg'] = btn_bg
            
        self.btn_save.bind("<Enter>", on_enter)
        self.btn_save.bind("<Leave>", on_leave)

    def _save_and_close(self):
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showerror("エラー", "APIキーが入力されていません。")
            return
        
        ConfigManager.save_api_key(key)
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback(True)

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback(False)
        self.window.destroy()


class OverlayWindow:
    """録音中のビジュアライザーオーバーレイ"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(root)
        
        # ウィンドウ設定
        self.window.overrideredirect(True)  # タイトルバーなし
        self.window.attributes('-topmost', True)  # 最前面
        self.window.attributes('-alpha', 0.85)  # 半透明
        
        # 画面中央下に配置
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        width = 300
        height = 100
        x = (screen_width - width) // 2
        y = screen_height - height - 100
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        self.canvas = tk.Canvas(self.window, width=width, height=height, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        self.bars = []
        self.num_bars = 50  # バーの数をさらに増やす
        self.bar_width = 4
        self.bar_spacing = 2
        
        # マウスイベント透過はTkinter単体では難しいが、今回は操作不要なのでそのまま
        
        self._init_bars(width, height)
        self.window.withdraw() # 初期状態は非表示
        
        self.is_visible = False
        self.is_thinking = False

    def _init_bars(self, width, height):
        self.canvas_height = height
        total_width = (self.bar_width * self.num_bars) + (self.bar_spacing * (self.num_bars - 1))
        start_x = (width - total_width) / 2
        
        for i in range(self.num_bars):
            x0 = start_x + i * (self.bar_width + self.bar_spacing)
            x1 = x0 + self.bar_width
            y1 = height
            y0 = height - 2
            bar = self.canvas.create_rectangle(x0, y0, x1, y1, fill="#ffffff", outline="")
            self.bars.append(bar)

    def show(self):
        self.window.deiconify()
        self.is_visible = True
        self.is_thinking = False
        for bar in self.bars:
            self.canvas.itemconfigure(bar, state="normal")

    def hide(self):
        self.window.withdraw()
        self.is_visible = False
        self.is_thinking = False

    def update_volume(self, volume):
        """
        音量(0.0 - 1.0)に応じてバーの高さを更新
        波形アニメーション
        """
        # Thinking中は音量更新を無視（アニメーションが上書きするため）
        if not self.is_visible or self.is_thinking:
            return

        import math
        import random
        import time
        
        # 時間経過で少しゆらぎを入れるためのオフセット
        t = time.time() * 10
        
        for i, bar in enumerate(self.bars):
            # 0.0 - 1.0 の正規化位置
            norm_pos = i / (self.num_bars - 1)
            
            # 中央(0.5)からの距離 (0.0 - 0.5)
            dist = abs(norm_pos - 0.5) 
            
            # ガウス関数っぽい形状を作る (中央が高く、端が低い)
            sigma = 0.15
            envelope = math.exp(-(dist**2) / (2 * sigma**2))
            
            # 音量を反映
            # 感度アップ: 小さな声でも反応しやすくするために 2.0倍くらいにブーストしつつ、最小値を少し底上げ
            boosted_volume = volume * 2.0
            amplitude = self.canvas_height * boosted_volume * 0.8           
            # ゆらぎ
            wave = (math.sin(norm_pos * 10 + t) * 0.2 + 1.0)
            
            h = amplitude * envelope * wave
            h = max(2, min(self.canvas_height, h))
            
            coords = self.canvas.coords(bar)
            x0, _, x1, _ = coords
            
            # 中央揃え（上下対称風）
            center_y = self.canvas_height / 2
            half_h = h / 2
            
            self.canvas.coords(bar, x0, center_y - half_h, x1, center_y + half_h)
            self.canvas.itemconfig(bar, fill="#ffffff")

    def set_thinking(self):
        """Thinking状態の表示（ブレスアニメーション）"""
        self.is_thinking = True
        self._animate_breath()

    def _animate_breath(self):
        if not self.is_thinking or not self.is_visible:
            return

        import math
        import time

        t = time.time()
        
        # ブレス周期 (2秒くらいで一周)
        cycle = (math.sin(t * 3) + 1.0) / 2.0 # 0.0 - 1.0
        
        # 最小の明るさ(高さ)と最大の明るさ(高さ)
        # 高で表現する: 全体がふわっと大きくなって小さくなる
        
        for i, bar in enumerate(self.bars):
            # 形状は緩やかな山
            norm_pos = i / (self.num_bars - 1)
            dist = abs(norm_pos - 0.5)
            sigma = 0.2
            shape = math.exp(-(dist**2) / (2 * sigma**2))
            
            # cycleに合わせて高さを変える
            # ベースの高さ + 呼吸分
            base_amp = 10
            breath_amp = 20 * cycle
            
            h = (base_amp + breath_amp) * shape
            h = max(2, h)
            
            coords = self.canvas.coords(bar)
            x0, _, x1, _ = coords
            
            center_y = self.canvas_height / 2
            half_h = h / 2
            
            self.canvas.coords(bar, x0, center_y - half_h, x1, center_y + half_h)
            self.canvas.itemconfig(bar, fill="#ffffff")  # 色は変えない（明滅ではなくサイズ変化で表現）
            
        # 30ms後に再実行 (約33fps)
        self.window.after(30, self._animate_breath)
