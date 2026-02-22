import time
import keyboard

_hotkey_name = "shift"
_key_held = False
_is_toggled = False
_last_press_time = 0
_other_key_pressed_during_hold = False
_hold_timer_active = False
is_recording = False

def start_recording():
    global is_recording
    print(">>> Recording Started")
    is_recording = True

def stop_and_transcribe():
    global is_recording
    print(">>> Recording Stopped and Transcribing")
    is_recording = False

def check_hold_start():
    global _hold_timer_active, _is_toggled
    _hold_timer_active = False
    
    if _key_held and not _other_key_pressed_during_hold:
        if not is_recording:
            print("Hold Timer Triggered!")
            _is_toggled = False
            start_recording()

def handle_double_tap():
    global _is_toggled
    if _is_toggled:
        print("Double Tap: Toggled OFF")
        _is_toggled = False
        if is_recording:
            stop_and_transcribe()
    else:
        print("Double Tap: Toggled ON")
        if not is_recording:
            _is_toggled = True
            start_recording()

def on_key_event(event):
    global _key_held, _other_key_pressed_during_hold, _hold_timer_active, _last_press_time

    is_target_key = (event.name.lower() == _hotkey_name)

    if event.event_type == keyboard.KEY_DOWN:
        if not is_target_key:
            if _key_held:
                _other_key_pressed_during_hold = True
                print(f"Interference detected by key: {event.name}")
        else:
            if not _key_held:
                _key_held = True
                _other_key_pressed_during_hold = False
                
                if _hold_timer_active:
                    pass # Timer is already running
                else:
                    _hold_timer_active = True
                    # Simulate tk.after
                    import threading
                    threading.Timer(0.3, check_hold_start).start()

    elif event.event_type == keyboard.KEY_UP:
        if is_target_key:
            _key_held = False
            
            if is_recording and not _is_toggled:
                print("Hold Released")
                stop_and_transcribe()

            if not _other_key_pressed_during_hold:
                current_time = time.time()
                if current_time - _last_press_time < 0.4:
                    handle_double_tap()
                    _last_press_time = 0
                else:
                    _last_press_time = current_time

keyboard.hook(on_key_event)

print("Testing logic (Hotkey: shift). Press ESC to quit.")
keyboard.wait('esc')
