import tkinter as tk
from tkinter import ttk
import webbrowser
import sounddevice as sd
from src.config import ConfigManager
from src.dictionary import Dictionary
from src.version import APP_VERSION
import math
import keyboard
import threading
import ctypes
from ctypes import wintypes


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def calc_overlay_position(monitor_rect, overlay_width, overlay_height, bottom_offset):
    left, top, right, bottom = monitor_rect
    monitor_width = right - left
    monitor_height = bottom - top
    x = left + (monitor_width - overlay_width) // 2
    y = top + monitor_height - overlay_height - bottom_offset
    return x, y


def get_cursor_monitor_rect():
    user32 = ctypes.windll.user32
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_MONITORINFO)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL

    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise OSError("GetCursorPos failed")

    monitor = user32.MonitorFromPoint(point, 2)
    if not monitor:
        raise OSError("MonitorFromPoint failed")

    monitor_info = _MONITORINFO()
    monitor_info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
        raise OSError("GetMonitorInfoW failed")

    rect = monitor_info.rcMonitor
    return rect.left, rect.top, rect.right, rect.bottom

class SettingsWindow:
    """設定ウィンドウ"""
    def __init__(self, root, on_close_callback=None, suspend_callback=None):
        self.root = root
        self.on_close_callback = on_close_callback
        self.suspend_callback = suspend_callback

        self.window = tk.Toplevel(root)
        self.window.title("Settings")
        self.window.geometry("840x700")
        self.window.resizable(True, True)
        self.window.attributes('-topmost', True)

        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()

        self._setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────────────────
    # UI 構築
    # ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        bg  = "#202020"
        fg  = "#ffffff"
        btn_bg     = "#00aa88"
        btn_active = "#00ccaa"
        self._bg  = bg
        self._fg  = fg
        self._btn_bg     = btn_bg
        self._btn_active = btn_active

        self.window.configure(bg=bg)

        style = ttk.Style()
        style.theme_use('default')
        style.map('TCombobox',
                  fieldbackground=[('readonly', '#333333'), ('disabled', '#1a1a1a')],
                  foreground=[('readonly', 'white'), ('disabled', '#555555')],
                  background=[('readonly', '#444444'), ('disabled', '#2a2a2a')])
        style.configure("TCombobox", fieldbackground="#333333", background="#444444",
                        foreground="white", borderwidth=0)
        self.window.option_add("*TCombobox*Listbox.background", "#1a1a1a")
        self.window.option_add("*TCombobox*Listbox.foreground", "white")
        self.window.option_add("*TCombobox*Listbox.selectBackground", btn_bg)
        self.window.option_add("*TCombobox*Listbox.selectForeground", "white")

        # ── ボトム固定エリア ──
        close_cont = tk.Frame(self.window, padx=20, pady=12, bg=bg)
        close_cont.pack(side=tk.BOTTOM, fill='x')
        tk.Label(close_cont, text=f"Version {APP_VERSION}", bg=bg, fg="#aaaaaa",
                 font=("Helvetica", 9)).pack(side=tk.LEFT)
        tk.Button(close_cont, text="Close Settings", command=self._on_close_clicked,
                  bg="#444444", fg="white", activebackground="#555555",
                  relief=tk.FLAT, font=("Helvetica", 10), cursor="hand2").pack(side=tk.RIGHT)

        # ── スクロールエリア ──
        container = tk.Frame(self.window, bg=bg)
        container.pack(side=tk.TOP, fill='both', expand=True)

        canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=bg)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._canvas = canvas

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Backend ──────────────────────────────────────────
        bc = tk.Frame(scroll_frame, padx=20, pady=12, bg=bg)
        bc.pack(fill='x')

        tk.Label(bc, text="Backend:", bg=bg, fg=fg,
                 font=("Helvetica", 10, "bold")).pack(anchor='w')

        self.backend_var = tk.StringVar(value=ConfigManager.get_backend_type())

        # ── OpenAI sub-section ──
        openai_outer = tk.Frame(bc, bg=bg, padx=4)
        openai_outer.pack(fill='x', pady=(6, 0))

        tk.Radiobutton(openai_outer, text="OpenAI", variable=self.backend_var,
                       value="openai", command=self._on_backend_change,
                       bg=bg, fg=fg, selectcolor="#444444",
                       activebackground=bg, activeforeground=fg,
                       highlightthickness=0).pack(anchor='w')

        openai_fields = tk.Frame(openai_outer, bg=bg, padx=22)
        openai_fields.pack(fill='x')

        tk.Label(openai_fields, text="URL:", bg=bg, fg=fg,
                 font=("Helvetica", 9)).pack(anchor='w', pady=(4, 0))
        self.openai_url_var = tk.StringVar(value=ConfigManager.get_openai_url())
        self.openai_url_entry = tk.Entry(
            openai_fields, textvariable=self.openai_url_var,
            bg="#333333", fg="white", insertbackground="white",
            disabledbackground="#1a1a1a", disabledforeground="#555555",
            relief=tk.FLAT)
        self.openai_url_entry.pack(fill='x', ipady=5, pady=(2, 6))

        tk.Label(openai_fields, text="API Key:", bg=bg, fg=fg,
                 font=("Helvetica", 9)).pack(anchor='w')
        api_row = tk.Frame(openai_fields, bg=bg)
        api_row.pack(fill='x', pady=(2, 4))

        self.api_key_var     = tk.StringVar(value=ConfigManager.load_api_key())
        self.api_key_visible = False
        self.api_key_entry = tk.Entry(
            api_row, textvariable=self.api_key_var, show="*",
            bg="#333333", fg="white", insertbackground="white",
            disabledbackground="#1a1a1a", disabledforeground="#555555",
            relief=tk.FLAT)
        self.api_key_entry.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)

        self.btn_toggle_api = tk.Button(
            api_row, text="👁", command=self._toggle_api_visibility,
            bg="#444444", fg="white", activebackground="#555555",
            relief=tk.FLAT, width=4, font=("Helvetica", 12), cursor="hand2")
        self.btn_toggle_api.pack(side=tk.LEFT, padx=(8, 0))

        # ── Local sub-section ──
        local_outer = tk.Frame(bc, bg=bg, padx=4)
        local_outer.pack(fill='x', pady=(10, 0))

        tk.Radiobutton(local_outer, text="Local (speaches)", variable=self.backend_var,
                       value="local", command=self._on_backend_change,
                       bg=bg, fg=fg, selectcolor="#444444",
                       activebackground=bg, activeforeground=fg,
                       highlightthickness=0).pack(anchor='w')

        local_fields = tk.Frame(local_outer, bg=bg, padx=22)
        local_fields.pack(fill='x')

        tk.Label(local_fields, text="URL:", bg=bg, fg=fg,
                 font=("Helvetica", 9)).pack(anchor='w', pady=(4, 0))
        self.local_url_var = tk.StringVar(value=ConfigManager.get_whisper_url())
        self.local_url_entry = tk.Entry(
            local_fields, textvariable=self.local_url_var,
            bg="#333333", fg="white", insertbackground="white",
            disabledbackground="#1a1a1a", disabledforeground="#555555",
            relief=tk.FLAT)
        self.local_url_entry.pack(fill='x', ipady=5, pady=(2, 6))
        self.local_url_entry.bind("<FocusOut>", self._on_url_blur)

        tk.Label(local_fields, text="Model:", bg=bg, fg=fg,
                 font=("Helvetica", 9)).pack(anchor='w')
        self.model_row = tk.Frame(local_fields, bg=bg)
        self.model_row.pack(fill='x', pady=(2, 6))
        self.model_var = tk.StringVar(value=ConfigManager.get_whisper_model())
        self.model_widget = tk.Entry(
            self.model_row, textvariable=self.model_var,
            bg="#333333", fg="white", insertbackground="white",
            disabledbackground="#1a1a1a", disabledforeground="#555555",
            relief=tk.FLAT)
        self.model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)

        tk.Label(local_fields, text="Container (auto-start, optional):",
                 bg=bg, fg=fg, font=("Helvetica", 9)).pack(anchor='w')
        self.container_var = tk.StringVar(value=ConfigManager.get_docker_container())
        self.container_entry = tk.Entry(
            local_fields, textvariable=self.container_var,
            bg="#333333", fg="white", insertbackground="white",
            disabledbackground="#1a1a1a", disabledforeground="#555555",
            relief=tk.FLAT)
        self.container_entry.pack(fill='x', ipady=5, pady=(2, 4))

        # Apply Backend row
        ab_row = tk.Frame(bc, bg=bg)
        ab_row.pack(fill='x', pady=(10, 2))
        tk.Button(ab_row, text="Apply Backend", command=self._apply_backend,
                  bg=btn_bg, fg="white", activebackground=btn_active,
                  relief=tk.FLAT, font=("Helvetica", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT)
        self.lbl_backend_status = tk.Label(ab_row, text="", bg=bg,
                                           font=("Helvetica", 9))
        self.lbl_backend_status.pack(side=tk.LEFT, padx=10)

        # ── Separator ──────────────────────────────────────
        tk.Frame(scroll_frame, bg="#383838", height=1).pack(fill='x', padx=20, pady=2)

        # ── Hotkey ─────────────────────────────────────────
        hc = tk.Frame(scroll_frame, padx=20, pady=10, bg=bg)
        hc.pack(fill='x')

        tk.Label(hc, text="Recording Hotkey:", bg=bg, fg=fg,
                 font=("Helvetica", 10, "bold")).pack(anchor='w')

        modifier_options = ["Ctrl", "Alt"]

        # Hold row
        tk.Label(hc, text="Hold (押している間録音):",
                 bg=bg, fg=fg, font=("Helvetica", 9)).pack(anchor='w', pady=(6, 0))
        hold_row = tk.Frame(hc, bg=bg)
        hold_row.pack(fill='x', pady=(2, 5))

        hold_str   = ConfigManager.get_hotkey()
        hold_mod, hold_key = ConfigManager.parse_hotkey(hold_str)
        if not hold_key:
            hold_mod, hold_key = "alt", "x"

        self.hold_modifier_var = tk.StringVar(value=hold_mod.capitalize())
        self.hold_key_var      = tk.StringVar(value=hold_key)

        hold_modifier_combo = ttk.Combobox(hold_row, textvariable=self.hold_modifier_var,
                     values=modifier_options, state="readonly", width=6)
        hold_modifier_combo.pack(side=tk.LEFT)
        self._prevent_combobox_wheel_scroll(hold_modifier_combo)
        tk.Label(hold_row, text="+", bg=bg, fg=fg).pack(side=tk.LEFT, padx=4)
        self.hold_key_entry = tk.Entry(
            hold_row, textvariable=self.hold_key_var,
            bg="#333333", fg="white", insertbackground="white",
            readonlybackground="#333333", relief=tk.FLAT, width=8, state="readonly")
        self.hold_key_entry.pack(side=tk.LEFT, ipady=3)
        self.btn_capture_hold = tk.Button(
            hold_row, text="Press key...", command=lambda: self._capture_key("hold"),
            bg="#444444", fg="white", activebackground="#555555",
            relief=tk.FLAT, font=("Helvetica", 9), cursor="hand2")
        self.btn_capture_hold.pack(side=tk.LEFT, padx=(8, 0))

        # Toggle row
        tk.Label(hc, text="Toggle (押すたびにオン/オフ):",
                 bg=bg, fg=fg, font=("Helvetica", 9)).pack(anchor='w')
        toggle_row = tk.Frame(hc, bg=bg)
        toggle_row.pack(fill='x', pady=(2, 5))

        toggle_str   = ConfigManager.get_hotkey_toggle()
        toggle_mod, toggle_key = ConfigManager.parse_hotkey(toggle_str)
        if not toggle_key:
            toggle_mod, toggle_key = "alt", "z"

        self.toggle_modifier_var = tk.StringVar(value=toggle_mod.capitalize())
        self.toggle_key_var      = tk.StringVar(value=toggle_key)

        toggle_modifier_combo = ttk.Combobox(toggle_row, textvariable=self.toggle_modifier_var,
                     values=modifier_options, state="readonly", width=6)
        toggle_modifier_combo.pack(side=tk.LEFT)
        self._prevent_combobox_wheel_scroll(toggle_modifier_combo)
        tk.Label(toggle_row, text="+", bg=bg, fg=fg).pack(side=tk.LEFT, padx=4)
        self.toggle_key_entry = tk.Entry(
            toggle_row, textvariable=self.toggle_key_var,
            bg="#333333", fg="white", insertbackground="white",
            readonlybackground="#333333", relief=tk.FLAT, width=8, state="readonly")
        self.toggle_key_entry.pack(side=tk.LEFT, ipady=3)
        self.btn_capture_toggle = tk.Button(
            toggle_row, text="Press key...", command=lambda: self._capture_key("toggle"),
            bg="#444444", fg="white", activebackground="#555555",
            relief=tk.FLAT, font=("Helvetica", 9), cursor="hand2")
        self.btn_capture_toggle.pack(side=tk.LEFT, padx=(8, 0))

        # Apply Hotkey row
        ah_row = tk.Frame(hc, bg=bg)
        ah_row.pack(fill='x', pady=(4, 2))
        tk.Button(ah_row, text="Apply Hotkey", command=self._apply_hotkey,
                  bg=btn_bg, fg="white", activebackground=btn_active,
                  relief=tk.FLAT, font=("Helvetica", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT)
        self.lbl_hotkey_status = tk.Label(ah_row, text="", bg=bg,
                                          font=("Helvetica", 9))
        self.lbl_hotkey_status.pack(side=tk.LEFT, padx=10)

        # ── Separator ──────────────────────────────────────
        tk.Frame(scroll_frame, bg="#383838", height=1).pack(fill='x', padx=20, pady=2)

        # ── Microphone ─────────────────────────────────────
        mc = tk.Frame(scroll_frame, padx=20, pady=10, bg=bg)
        mc.pack(fill='x')

        tk.Label(mc, text="Microphone:", bg=bg, fg=fg,
                 font=("Helvetica", 10, "bold")).pack(anchor='w')

        mic_row = tk.Frame(mc, bg=bg)
        mic_row.pack(fill='x', pady=(4, 2))

        system_default = "System Default"
        try:
            all_devices = sd.query_devices()
            wasapi_idx = next(
                (i for i, h in enumerate(sd.query_hostapis()) if 'WASAPI' in h['name']),
                None
            )
            if wasapi_idx is not None:
                input_device_names = [
                    d['name'] for d in all_devices
                    if d['max_input_channels'] > 0 and d['hostapi'] == wasapi_idx
                ]
            else:
                input_device_names = [d['name'] for d in all_devices if d['max_input_channels'] > 0]
        except Exception:
            input_device_names = []
        mic_options = [system_default] + input_device_names

        current_mic  = ConfigManager.get_mic_device()
        initial_mic  = current_mic if current_mic in input_device_names else system_default
        self.mic_var = tk.StringVar(value=initial_mic)

        mic_combo = ttk.Combobox(mic_row, textvariable=self.mic_var,
                     values=mic_options, state="readonly")
        mic_combo.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)
        self._prevent_combobox_wheel_scroll(mic_combo)

        am_row = tk.Frame(mc, bg=bg)
        am_row.pack(fill='x', pady=(6, 2))
        tk.Button(am_row, text="Apply Mic", command=self._apply_mic,
                  bg=btn_bg, fg="white", activebackground=btn_active,
                  relief=tk.FLAT, font=("Helvetica", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT)
        self.lbl_mic_status = tk.Label(am_row, text="", bg=bg,
                                       font=("Helvetica", 9))
        self.lbl_mic_status.pack(side=tk.LEFT, padx=10)

        # ── Separator ──────────────────────────────────────
        tk.Frame(scroll_frame, bg="#383838", height=1).pack(fill='x', padx=20, pady=2)

        # ── AI Refinement (Ollama) ──────────────────────────
        arc = tk.Frame(scroll_frame, padx=20, pady=10, bg=bg)
        arc.pack(fill='x')

        tk.Label(arc, text="AI Text Refinement (Ollama):", bg=bg, fg=fg,
                 font=("Helvetica", 10, "bold")).pack(anchor='w')

        # Mode Selection
        mode_frame = tk.Frame(arc, bg=bg)
        mode_frame.pack(fill='x', pady=(4, 6))

        self.ai_mode_var = tk.StringVar(value=ConfigManager.get_ai_mode())

        modes = [
            ("Off (文字起こしそのまま)", "off"),
            ("限定AI校正 (フィラー除去・最小限の修正)", "refine"),
            ("AI編集 (選択テキスト必須)", "edit"),
        ]

        for text, val in modes:
            tk.Radiobutton(mode_frame, text=text, variable=self.ai_mode_var,
                           value=val, bg=bg, fg=fg, selectcolor="#444444",
                           activebackground=bg, activeforeground=fg,
                           highlightthickness=0).pack(anchor='w', pady=1)

        # Ollama URL & Model
        ollama_fields = tk.Frame(arc, bg=bg, padx=10)
        ollama_fields.pack(fill='x', pady=(4, 0))

        tk.Label(ollama_fields, text="Ollama URL:", bg=bg, fg=fg,
                 font=("Helvetica", 9)).pack(anchor='w')
        self.ollama_url_var = tk.StringVar(value=ConfigManager.get_ollama_url())
        self.ollama_url_entry = tk.Entry(
            ollama_fields, textvariable=self.ollama_url_var,
            bg="#333333", fg="white", insertbackground="white", relief=tk.FLAT)
        self.ollama_url_entry.pack(fill='x', ipady=5, pady=(2, 6))

        tk.Label(ollama_fields, text="Ollama Model:", bg=bg, fg=fg,
                 font=("Helvetica", 9)).pack(anchor='w')
        self.ollama_model_row = tk.Frame(ollama_fields, bg=bg)
        self.ollama_model_row.pack(fill='x', pady=(2, 6))

        current_ollama_model = ConfigManager.get_ollama_model()
        initial_models = [current_ollama_model] if current_ollama_model else ["qwen2.5:7b", "gemma3:4b"]

        self.ollama_model_var = tk.StringVar(value=current_ollama_model)
        self.ollama_model_widget = ttk.Combobox(
            self.ollama_model_row, textvariable=self.ollama_model_var,
            values=initial_models, state="readonly")
        self.ollama_model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)
        self._prevent_combobox_wheel_scroll(self.ollama_model_widget)

        self.btn_fetch_ollama_models = tk.Button(
            self.ollama_model_row, text="Fetch Models", command=self._start_ollama_model_fetch,
            bg="#444444", fg="white", activebackground="#555555",
            relief=tk.FLAT, font=("Helvetica", 9), cursor="hand2")
        self.btn_fetch_ollama_models.pack(side=tk.LEFT, padx=(8, 0))

        # Apply AI Refinement row
        aai_row = tk.Frame(arc, bg=bg)
        aai_row.pack(fill='x', pady=(6, 2))
        tk.Button(aai_row, text="Apply AI Refinement", command=self._apply_ai_refinement,
                  bg=btn_bg, fg="white", activebackground=btn_active,
                  relief=tk.FLAT, font=("Helvetica", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT)
        self.lbl_ai_status = tk.Label(aai_row, text="", bg=bg,
                                      font=("Helvetica", 9))
        self.lbl_ai_status.pack(side=tk.LEFT, padx=10)

        # ── Separator ──────────────────────────────────────
        tk.Frame(scroll_frame, bg="#383838", height=1).pack(fill='x', padx=20, pady=2)

        # ── 音声入力辞書 ────────────────────────────────────
        dc = tk.Frame(scroll_frame, padx=20, pady=10, bg=bg)
        dc.pack(fill='x')

        dict_head = tk.Frame(dc, bg=bg)
        dict_head.pack(fill='x')
        tk.Label(dict_head, text="音声入力辞書:", bg=bg, fg=fg,
                 font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(dict_head, text="+ 項目を追加", command=self._on_add_dictionary_row,
                  bg="#444444", fg="white", activebackground="#555555",
                  relief=tk.FLAT, font=("Helvetica", 9),
                  cursor="hand2").pack(side=tk.RIGHT)

        tk.Label(dc, text="Whisperに正しく認識させたい固有名詞を登録",
                 bg=bg, fg="#888888", font=("Helvetica", 9)).pack(anchor='w', pady=(2, 6))

        # 見出し行（各行の grid 列構成に合わせる）
        dict_header = tk.Frame(dc, bg=bg, padx=10)
        dict_header.pack(fill='x')
        dict_header.columnconfigure(0, weight=1, uniform="dict_col")
        dict_header.columnconfigure(1, weight=1, uniform="dict_col")
        tk.Label(dict_header, text="正しい表記", bg=bg, fg="#888888",
                 font=("Helvetica", 9), anchor='w').grid(row=0, column=0, sticky='ew', padx=(0, 6))
        tk.Label(dict_header, text="誤認識される表記 (任意)", bg=bg, fg="#888888",
                 font=("Helvetica", 9), anchor='w').grid(row=0, column=1, sticky='ew', padx=(0, 6))
        tk.Label(dict_header, text="", bg=bg, width=6).grid(row=0, column=2)

        # 行コンテナ（行の追加・削除でここだけが変化する）
        self.dict_rows_frame = tk.Frame(dc, bg=bg, padx=10)
        self.dict_rows_frame.pack(fill='x', pady=(2, 0))
        self.dict_rows = []

        self.lbl_dict_counter = tk.Label(dc, text="", bg=bg, fg="#888888",
                                         font=("Helvetica", 9))
        self.lbl_dict_counter.pack(anchor='w', pady=(6, 0))

        ad_row = tk.Frame(dc, bg=bg)
        ad_row.pack(fill='x', pady=(6, 2))
        tk.Button(ad_row, text="Apply Dictionary", command=self._apply_dictionary,
                  bg=btn_bg, fg="white", activebackground=btn_active,
                  relief=tk.FLAT, font=("Helvetica", 10, "bold"),
                  cursor="hand2").pack(side=tk.LEFT)
        self.lbl_dict_status = tk.Label(ad_row, text="", bg=bg,
                                        font=("Helvetica", 9))
        self.lbl_dict_status.pack(side=tk.LEFT, padx=10)

        self._load_dictionary_rows()

        # 初期状態を適用
        self._on_backend_change()

        # Local モードかつ localhost URL なら起動時にモデルフェッチ
        if (ConfigManager.get_backend_type() == "local"
                and self._is_localhost_url(ConfigManager.get_whisper_url())):
            self.window.after(200, lambda: self._start_model_fetch(ConfigManager.get_whisper_url()))

        # Ollama モデル一覧も起動時に自動フェッチ
        ollama_url = ConfigManager.get_ollama_url().strip()
        if ollama_url:
            self.window.after(300, self._start_ollama_model_fetch)

    # ──────────────────────────────────────────────────────────
    # Combobox ホイールスクロール対策
    # ──────────────────────────────────────────────────────────

    def _prevent_combobox_wheel_scroll(self, combobox) -> None:
        """Combobox上でのマウスホイールが値を変更しないようにし、代わりに設定ウィンドウ全体をスクロールさせる。"""
        def _on_wheel(event):
            if hasattr(self, "_canvas") and self._canvas.winfo_exists():
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
        combobox.bind("<MouseWheel>", _on_wheel)

    # ──────────────────────────────────────────────────────────
    # Backend 切り替え
    # ──────────────────────────────────────────────────────────

    def _on_backend_change(self):
        """ラジオボタン切り替え時に OpenAI / Local フィールドの有効・無効を更新する"""
        is_openai = self.backend_var.get() == "openai"
        oa = "normal"   if is_openai else "disabled"
        lo = "normal"   if not is_openai else "disabled"

        self.openai_url_entry.config(state=oa)
        self.api_key_entry.config(state=oa)
        self.btn_toggle_api.config(state=oa)

        self.local_url_entry.config(state=lo)
        self.container_entry.config(state=lo)

        # model_widget は Entry / Combobox で有効状態が異なる
        if lo == "disabled":
            self.model_widget.config(state="disabled")
        else:
            if isinstance(self.model_widget, ttk.Combobox):
                self.model_widget.config(state="readonly")
            else:
                self.model_widget.config(state="normal")

    def _toggle_api_visibility(self):
        if self.api_key_visible:
            self.api_key_entry.config(show="*")
            self.btn_toggle_api.config(text="👁")
            self.api_key_visible = False
        else:
            self.api_key_entry.config(show="")
            self.btn_toggle_api.config(text="🙈")
            self.api_key_visible = True

    # ──────────────────────────────────────────────────────────
    # 通知ヘルパー
    # ──────────────────────────────────────────────────────────

    def _show_status(self, label: tk.Label, message: str, success: bool = True):
        """Apply ボタン横のラベルに一時メッセージを表示（3秒後に消える）"""
        if not self.window.winfo_exists():
            return
        label.config(text=message, fg="#00cc88" if success else "#ff6666")
        self.window.after(3000, lambda: label.config(text="") if label.winfo_exists() else None)

    def _msgbox_error(self, message: str) -> None:
        """エラーダイアログを topmost を外して表示"""
        from tkinter import messagebox
        if not self.window.winfo_exists():
            return
        self.window.attributes('-topmost', False)
        messagebox.showerror("Error", message, parent=self.window)
        if self.window.winfo_exists():
            self.window.attributes('-topmost', True)

    def _set_cursor(self, cursor_type):
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.config(cursor=cursor_type)
            self.window.update_idletasks()

    # ──────────────────────────────────────────────────────────
    # Apply ボタン（ウィンドウを閉じない）
    # ──────────────────────────────────────────────────────────

    def _apply_backend(self):
        backend_type = self.backend_var.get()

        if backend_type == "openai":
            url     = self.openai_url_var.get().strip()
            api_key = self.api_key_var.get().strip()
            if not url:
                self._show_status(self.lbl_backend_status, "URL is empty.", success=False)
                return
            if not api_key:
                self._show_status(self.lbl_backend_status, "API Key is empty.", success=False)
                return
            self._set_cursor("watch")
            def task():
                try:
                    ConfigManager.set_backend_type("openai")
                    ConfigManager.set_openai_url(url)
                    ConfigManager.save_api_key(api_key)
                    self.window.after(0, lambda: self._show_status(
                        self.lbl_backend_status, "✓ Saved (OpenAI)"))
                except Exception as e:
                    self.window.after(0, lambda: self._show_status(
                        self.lbl_backend_status, f"Error: {e}", success=False))
                finally:
                    self.window.after(0, lambda: self._set_cursor(""))
            threading.Thread(target=task, daemon=True).start()

        else:  # local
            url       = self.local_url_var.get().strip()
            model     = self.model_var.get().strip()
            container = self.container_var.get().strip()
            if not url:
                self._show_status(self.lbl_backend_status, "URL is empty.", success=False)
                return
            if not url.startswith("http"):
                self._show_status(self.lbl_backend_status, "URL must start with 'http'.", success=False)
                return
            if not model or model == "Fetching...":
                self._show_status(self.lbl_backend_status, "Model is empty or loading.", success=False)
                return
            self._set_cursor("watch")
            def task():
                try:
                    ConfigManager.set_backend_type("local")
                    ConfigManager.set_whisper_url(url)
                    ConfigManager.set_whisper_model(model)
                    ConfigManager.set_docker_container(container)
                    self.window.after(0, lambda: self._show_status(
                        self.lbl_backend_status, "✓ Saved (Local)"))
                except Exception as e:
                    self.window.after(0, lambda: self._show_status(
                        self.lbl_backend_status, f"Error: {e}", success=False))
                finally:
                    self.window.after(0, lambda: self._set_cursor(""))
            threading.Thread(target=task, daemon=True).start()

    def _apply_hotkey(self):
        hold_mod   = self.hold_modifier_var.get().lower()
        hold_key   = self.hold_key_var.get().strip()
        toggle_mod = self.toggle_modifier_var.get().lower()
        toggle_key = self.toggle_key_var.get().strip()

        if not hold_key:
            self._show_status(self.lbl_hotkey_status, "Hold key not set.", success=False)
            return
        if not toggle_key:
            self._show_status(self.lbl_hotkey_status, "Toggle key not set.", success=False)
            return

        self._set_cursor("watch")
        def task():
            try:
                ConfigManager.set_hotkey(f"{hold_mod}+{hold_key}")
                ConfigManager.set_hotkey_toggle(f"{toggle_mod}+{toggle_key}")
                if self.on_close_callback:
                    self.window.after(0, lambda: self.on_close_callback("hotkey_only"))
                msg = (f"✓ Hold: {hold_mod.upper()}+{hold_key.upper()}"
                       f"  Toggle: {toggle_mod.upper()}+{toggle_key.upper()}")
                self.window.after(0, lambda: self._show_status(self.lbl_hotkey_status, msg))
            except Exception as e:
                self.window.after(0, lambda: self._show_status(
                    self.lbl_hotkey_status, f"Error: {e}", success=False))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))
        threading.Thread(target=task, daemon=True).start()

    def _apply_mic(self):
        selected = self.mic_var.get().strip()
        if not selected:
            return
        self._set_cursor("watch")
        def task():
            try:
                name_to_save = None if selected == "System Default" else selected
                ConfigManager.set_mic_device(name_to_save)
                self.window.after(0, lambda: self._show_status(
                    self.lbl_mic_status, f"✓ {selected}"))
            except Exception as e:
                self.window.after(0, lambda: self._show_status(
                    self.lbl_mic_status, f"Error: {e}", success=False))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))
        threading.Thread(target=task, daemon=True).start()

    def _apply_ai_refinement(self):
        mode  = self.ai_mode_var.get()
        url   = self.ollama_url_var.get().strip()
        model = self.ollama_model_var.get().strip()

        if not url:
            self._show_status(self.lbl_ai_status, "URL is empty.", success=False)
            return
        if not model:
            self._show_status(self.lbl_ai_status, "Model is empty.", success=False)
            return

        self._set_cursor("watch")
        def task():
            try:
                ConfigManager.set_ai_mode(mode)
                ConfigManager.set_ollama_url(url)
                ConfigManager.set_ollama_model(model)
                self.window.after(0, lambda: self._show_status(
                    self.lbl_ai_status, f"✓ Saved ({mode.upper()}: {model})"))
            except Exception as e:
                self.window.after(0, lambda: self._show_status(
                    self.lbl_ai_status, f"Error: {e}", success=False))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))
        threading.Thread(target=task, daemon=True).start()

    def _start_ollama_model_fetch(self):
        url = self.ollama_url_var.get().strip()
        if not url:
            return
        self.btn_fetch_ollama_models.config(state="disabled", text="Fetching...")
        def task():
            from src.llm_refiner import LLMRefiner
            models = LLMRefiner.fetch_available_models(url)
            self.window.after(0, lambda: self._on_ollama_models_fetched(models))
        threading.Thread(target=task, daemon=True).start()

    def _on_ollama_models_fetched(self, models: list):
        if not self.window.winfo_exists():
            return
        self.btn_fetch_ollama_models.config(state="normal", text="Fetch Models")
        if not models:
            self._show_status(self.lbl_ai_status, "No Ollama models found.", success=False)
            return
        current = self.ollama_model_var.get()
        initial = current if current in models else models[0]
        self.ollama_model_var.set(initial)
        self.ollama_model_widget.config(values=models)
        self._show_status(self.lbl_ai_status, f"✓ Fetched {len(models)} models")

    # ──────────────────────────────────────────────────────────
    # 音声入力辞書
    # ──────────────────────────────────────────────────────────

    def _load_dictionary_rows(self) -> None:
        """ConfigManager から辞書エントリを読み込み、行を並べる。0件なら空行を1つ出す。"""
        for widget in self.dict_rows_frame.winfo_children():
            widget.destroy()
        self.dict_rows = []

        entries = ConfigManager.get_dictionary()
        if not entries:
            self._add_dictionary_row("", "")
        else:
            for entry in entries:
                self._add_dictionary_row(entry.get("term", ""), entry.get("wrong", ""))

        self._update_dictionary_counter()

    def _add_dictionary_row(self, term: str = "", wrong: str = "") -> dict:
        """辞書1行分のウィジェットを作り、self.dict_rows に登録する。"""
        row_frame = tk.Frame(self.dict_rows_frame, bg=self._bg)
        row_frame.pack(fill='x', pady=2)
        row_frame.columnconfigure(0, weight=1, uniform="dict_col")
        row_frame.columnconfigure(1, weight=1, uniform="dict_col")

        term_var  = tk.StringVar(value=term)
        wrong_var = tk.StringVar(value=wrong)

        term_entry = tk.Entry(
            row_frame, textvariable=term_var,
            bg="#333333", fg="white", insertbackground="white", relief=tk.FLAT)
        term_entry.grid(row=0, column=0, sticky='ew', padx=(0, 6), ipady=5)

        wrong_entry = tk.Entry(
            row_frame, textvariable=wrong_var,
            bg="#333333", fg="white", insertbackground="white", relief=tk.FLAT)
        wrong_entry.grid(row=0, column=1, sticky='ew', padx=(0, 6), ipady=5)

        row_data = {
            "frame": row_frame,
            "term_var": term_var,
            "wrong_var": wrong_var,
        }

        delete_btn = tk.Button(
            row_frame, text="削除", command=lambda: self._on_remove_dictionary_row(row_data),
            bg="#444444", fg="white", activebackground="#555555",
            relief=tk.FLAT, font=("Helvetica", 9), cursor="hand2")
        delete_btn.grid(row=0, column=2, padx=(0, 0))
        row_data["delete_btn"] = delete_btn

        term_var.trace_add("write", lambda *_: self._update_dictionary_counter())
        wrong_var.trace_add("write", lambda *_: self._update_dictionary_counter())

        self.dict_rows.append(row_data)
        return row_data

    def _on_add_dictionary_row(self) -> None:
        """[+ 項目を追加] ボタン: 末尾に空行を追加する。"""
        self._add_dictionary_row("", "")
        self._update_dictionary_counter()

    def _on_remove_dictionary_row(self, row_data: dict) -> None:
        """[削除] ボタン: その行を削除する。全部消えたら空行を1つ残す。"""
        if row_data in self.dict_rows:
            self.dict_rows.remove(row_data)
        if row_data["frame"].winfo_exists():
            row_data["frame"].destroy()

        if not self.dict_rows:
            self._add_dictionary_row("", "")

        self._update_dictionary_counter()

    def _collect_dictionary_entries(self) -> list:
        """現在の行ウィジェットから {"term", "wrong"} のリストを取得する（未加工）。"""
        entries = []
        for row_data in self.dict_rows:
            if not row_data["frame"].winfo_exists():
                continue
            entries.append({
                "term": row_data["term_var"].get(),
                "wrong": row_data["wrong_var"].get(),
            })
        return entries

    def _update_dictionary_counter(self) -> None:
        """現在の入力内容から prompt suffix の長さを計算し、カウンタ表示を更新する。"""
        if not self.lbl_dict_counter.winfo_exists():
            return
        entries = self._collect_dictionary_entries()
        info = Dictionary.prompt_overflow_info(entries)
        max_chars = Dictionary.MAX_PROMPT_CHARS

        if info["truncated"]:
            dropped = info["total_count"] - info["kept_count"]
            text = f"プロンプト長: {info['raw_length']} / {max_chars} 文字（{dropped}語が除外されます）"
            color = "#ff6666"
        else:
            text = f"プロンプト長: {info['raw_length']} / {max_chars} 文字"
            color = "#888888"

        self.lbl_dict_counter.config(text=text, fg=color)

    def _apply_dictionary(self) -> None:
        """Apply Dictionary ボタン: term が空の行を除外して保存する。除外・フィラー衝突は警告する。"""
        raw_entries = self._collect_dictionary_entries()
        entries = []
        blank_term_count = 0
        for entry in raw_entries:
            term  = entry["term"].strip()
            wrong = entry["wrong"].strip()
            if not term:
                blank_term_count += 1
                continue
            entries.append({"term": term, "wrong": wrong})

        filler_hits = [
            e["wrong"] for e in entries
            if e["wrong"] and any(filler in e["wrong"] for filler in Dictionary.FILLER_PATTERNS)
        ]

        self._set_cursor("watch")

        def task():
            try:
                ConfigManager.set_dictionary(entries)

                warnings = []
                if blank_term_count:
                    warnings.append(f"「正しい表記」が空の{blank_term_count}行は保存されません")
                if filler_hits:
                    if len(filler_hits) == 1:
                        warnings.append(f"「{filler_hits[0]}」はフィラー除去と衝突し置換されません")
                    else:
                        warnings.append(f"{len(filler_hits)}件がフィラー除去と衝突し置換されません")

                def finish():
                    self._load_dictionary_rows()  # 実際に保存された内容で再描画
                    if warnings:
                        self._show_status(self.lbl_dict_status, "⚠ 保存したが: " + " / ".join(warnings), success=False)
                    else:
                        self._show_status(self.lbl_dict_status, "✓ Saved")

                self.window.after(0, finish)
            except Exception as exc:
                self.window.after(0, lambda: self._show_status(
                    self.lbl_dict_status, f"Error: {exc}", success=False))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))
        threading.Thread(target=task, daemon=True).start()

    # ──────────────────────────────────────────────────────────
    # モデルフェッチ
    # ──────────────────────────────────────────────────────────

    def _on_url_blur(self, event) -> None:
        if self.backend_var.get() != "local":
            return
        url = self.local_url_var.get().strip()
        if self._is_localhost_url(url):
            self._start_model_fetch(url)
        else:
            self._switch_to_model_entry()

    def _is_localhost_url(self, url: str) -> bool:
        return "localhost" in url or "127.0.0.1" in url

    def _start_model_fetch(self, url: str) -> None:
        self._fetch_serial = getattr(self, '_fetch_serial', 0) + 1
        serial = self._fetch_serial
        current = self.model_var.get()
        if current != "Fetching...":
            self._prefetch_model_value = current
        prefetched_model = self._prefetch_model_value
        self.model_var.set("Fetching...")
        self.model_widget.config(state="disabled")
        threading.Thread(
            target=self._fetch_models_async, args=(url, serial, prefetched_model), daemon=True
        ).start()

    def _fetch_models_async(self, url: str, serial: int, prefetched_model: str) -> None:
        import urllib.request
        import json as _json
        models_url = url.rstrip("/") + "/models"
        try:
            with urllib.request.urlopen(models_url, timeout=5) as resp:
                data = _json.loads(resp.read().decode())
            models = [item["id"] for item in data.get("data", [])]
            if models and serial == self._fetch_serial:
                self.window.after(
                    0,
                    lambda: self._switch_to_model_combo(models, serial, prefetched_model),
                )
                return
        except Exception:
            pass
        if serial == self._fetch_serial:
            self.window.after(
                0,
                lambda: self._switch_to_model_entry(prefetched_model, serial),
            )

    def _switch_to_model_combo(
        self, models: list, serial: int | None = None, prefetched_model: str | None = None
    ) -> None:
        if serial is not None and serial != self._fetch_serial:
            return
        if not self.window.winfo_exists():
            return
        current = self.model_var.get()
        prefetched = (
            prefetched_model if serial is not None
            else getattr(self, '_prefetch_model_value', None)
        )
        initial = (
            current if current in models else
            prefetched if prefetched in models else
            models[0]
        )
        self.model_widget.destroy()
        self.model_var.set(initial)
        self.model_widget = ttk.Combobox(
            self.model_row, textvariable=self.model_var,
            values=models, state="readonly")
        self.model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)
        self._prevent_combobox_wheel_scroll(self.model_widget)
        # Local が無効なら Combobox も無効にする
        if self.backend_var.get() != "local":
            self.model_widget.config(state="disabled")

    def _switch_to_model_entry(
        self, restore_value: str | None = None, serial: int | None = None
    ) -> None:
        if serial is not None and serial != self._fetch_serial:
            return
        if serial is None:
            self._fetch_serial = getattr(self, '_fetch_serial', 0) + 1
        if not self.window.winfo_exists():
            return
        current = self.model_var.get()
        value = restore_value if restore_value is not None else (
            ConfigManager.get_whisper_model() if current == "Fetching..." else current
        )
        if isinstance(self.model_widget, ttk.Combobox):
            self.model_widget.destroy()
            self.model_widget = tk.Entry(
                self.model_row, textvariable=self.model_var,
                bg="#333333", fg="white", insertbackground="white",
                disabledbackground="#1a1a1a", disabledforeground="#555555",
                relief=tk.FLAT)
            self.model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)
        else:
            # Local が有効なら normal に戻す
            if self.backend_var.get() == "local":
                self.model_widget.config(state="normal")
        self.model_var.set(value)
        # Local が無効ならそのまま disabled
        if self.backend_var.get() != "local":
            self.model_widget.config(state="disabled")

    # ──────────────────────────────────────────────────────────
    # キーキャプチャ
    # ──────────────────────────────────────────────────────────

    _MODIFIER_NAMES = {
        "ctrl", "alt", "shift", "win",
        "left ctrl", "right ctrl", "left alt", "right alt",
        "left shift", "right shift", "left windows", "right windows",
        "caps lock", "num lock", "scroll lock", "menu",
    }

    def _capture_key(self, target: str) -> None:
        if target == "hold":
            btn     = self.btn_capture_hold
            key_var = self.hold_key_var
        else:
            btn     = self.btn_capture_toggle
            key_var = self.toggle_key_var

        if btn.cget("text") == "Waiting...":
            return

        prev_value = key_var.get()
        if self.suspend_callback:
            self.suspend_callback(True)

        btn.config(text="Waiting...", state="disabled", bg="#886600")

        hook_ref    = [None]
        timeout_ref = [None]
        done_ref    = [False]

        def finish(key_name: str) -> None:
            if done_ref[0]:
                return
            done_ref[0] = True
            if hook_ref[0] is not None:
                keyboard.unhook(hook_ref[0])
                hook_ref[0] = None
            if timeout_ref[0] is not None:
                self.window.after_cancel(timeout_ref[0])
                timeout_ref[0] = None
            key_var.set(key_name)
            btn.config(text="Press key...", state="normal", bg="#444444")
            if self.suspend_callback:
                self.suspend_callback(False)

        def on_key(event) -> None:
            if event.event_type != keyboard.KEY_DOWN:
                return
            name = event.name.lower()
            if name in self._MODIFIER_NAMES:
                return
            if not self.window.winfo_exists():
                if hook_ref[0] is not None:
                    try:
                        keyboard.unhook(hook_ref[0])
                    except Exception:
                        pass
                    hook_ref[0] = None
                return
            self.window.after(0, lambda: finish(name))

        def on_timeout() -> None:
            self.window.after(0, lambda: finish(prev_value))

        hook_ref[0]    = keyboard.hook(on_key)
        timeout_ref[0] = self.window.after(10000, on_timeout)
        self._capture_hook_ref    = hook_ref
        self._capture_timeout_ref = timeout_ref

    def _cancel_capture(self) -> None:
        hook_ref    = getattr(self, '_capture_hook_ref',    [None])
        timeout_ref = getattr(self, '_capture_timeout_ref', [None])
        if hook_ref[0] is not None:
            try:
                keyboard.unhook(hook_ref[0])
            except Exception:
                pass
            hook_ref[0] = None
        if timeout_ref[0] is not None:
            try:
                self.window.after_cancel(timeout_ref[0])
            except Exception:
                pass
            timeout_ref[0] = None
        for btn_attr in ('btn_capture_hold', 'btn_capture_toggle'):
            btn = getattr(self, btn_attr, None)
            if btn and btn.winfo_exists() and btn.cget("text") == "Waiting...":
                btn.config(text="Press key...", state="normal", bg="#444444")
                if self.suspend_callback:
                    self.suspend_callback(False)

    # ──────────────────────────────────────────────────────────
    # ウィンドウ閉じる
    # ──────────────────────────────────────────────────────────

    def _on_close_clicked(self):
        self._cancel_capture()
        self.window.destroy()

    def _on_close(self):
        self._cancel_capture()
        if self.on_close_callback:
            self.on_close_callback(False)
        self.window.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# OverlayWindow（録音中ビジュアライザー）
# ──────────────────────────────────────────────────────────────────────────────

class OverlayWindow:
    """録音中のモダンなビジュアライザーオーバーレイ"""
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(root)

        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.8)

        screen_width  = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        width, height = 320, 80
        x = (screen_width - width) // 2
        y = screen_height - height - 120
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        self.bg_color = "#1a1a1a"
        self.canvas   = tk.Canvas(self.window, width=width, height=height,
                                  bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self.bars        = []
        self.num_bars    = 100
        self.bar_width   = 1
        self.bar_spacing = 2

        self.rec_colors      = self._generate_gradient("#00f5d4", "#9b5de5", self.num_bars)
        self.thinking_colors = self._generate_gradient("#ff0000", "#ff69b4", self.num_bars)
        self.colors          = self.rec_colors
        self._init_bars(width, height)
        self.window.withdraw()

        self.is_visible     = False
        self.is_thinking    = False
        self.current_volume = 0.0

    def _generate_gradient(self, start_hex, end_hex, steps):
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
        start_x    = (width - total_width) / 2
        center_y   = height / 2
        for i in range(self.num_bars):
            x   = start_x + (i * (self.bar_width + self.bar_spacing)) + (self.bar_width / 2)
            bar = self.canvas.create_line(x, center_y - 2, x, center_y + 2,
                                          fill=self.colors[i], width=self.bar_width,
                                          capstyle='round')
            self.bars.append(bar)

    def show(self):
        self.is_thinking    = False
        self.current_volume = 0.0
        for i, bar in enumerate(self.bars):
            self.canvas.itemconfig(bar, fill=self.rec_colors[i])
        self.canvas.update_idletasks()
        self._reposition_for_cursor()
        self.window.deiconify()
        self.is_visible = True
        self._draw_frame()

    def _reposition_for_cursor(self):
        width, height = 320, 80
        try:
            x, y = calc_overlay_position(
                get_cursor_monitor_rect(), width, height, 120
            )
        except Exception:
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width - width) // 2
            y = screen_height - height - 120
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def hide(self):
        self.is_thinking = False
        self.is_visible  = False
        for i, bar in enumerate(self.bars):
            self.canvas.itemconfig(bar, fill=self.rec_colors[i])
        self.canvas.update_idletasks()
        self.window.withdraw()

    def update_volume(self, volume):
        if not self.is_visible or self.is_thinking:
            return
        alpha = 0.3
        self.current_volume = self.current_volume * alpha + volume * (1 - alpha)

    def _draw_frame(self):
        if not self.is_visible:
            return
        import time
        t        = time.time()
        center_y = self.canvas_height / 2
        for i, bar in enumerate(self.bars):
            norm_pos = i / (self.num_bars - 1)
            dist     = abs(norm_pos - 0.5)
            envelope = math.exp(-(dist**2) / (2 * 0.18**2))
            if self.is_thinking:
                delay    = dist * 0.4
                p        = (t * 0.8 - delay) % 1.0
                p1       = math.exp(-((p - 0.2)**2) / (2 * 0.05**2)) * 1.0
                p2       = math.exp(-((p - 0.45)**2) / (2 * 0.04**2)) * 0.4
                local_pulse = (p1 + p2) * envelope
                h = 3 + 40 * local_pulse
                h = max(3, h)
                if local_pulse > 0.4:
                    self.canvas.itemconfig(bar, fill="#ffb6c1")
                else:
                    self.canvas.itemconfig(bar, fill=self.thinking_colors[i])
            else:
                anim_t = t * 6
                wave   = (math.sin(norm_pos * 14 + anim_t) * 0.2 +
                          math.sin(norm_pos * 9 - anim_t * 0.5) * 0.1 + 0.7)
                h = 3 + (self.canvas_height * self.current_volume * 1.6) * envelope * wave
                h = max(3, min(self.canvas_height - 6, h))
                self.canvas.itemconfig(bar, fill=self.rec_colors[i])
            x, _, _, _ = self.canvas.coords(bar)
            half_h     = h / 2
            self.canvas.coords(bar, x, center_y - half_h, x, center_y + half_h)
        self.root.after(16, self._draw_frame)

    def set_thinking(self):
        self.is_thinking = True
