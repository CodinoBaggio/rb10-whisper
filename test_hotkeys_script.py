import time
from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys

def on_press():
    print("Pressed!")

def on_release():
    print("Released!")

bindings = [
    ["control", on_press, on_release, False],
    ["shift", on_press, on_release, False],
    ["alt", on_press, on_release, False]
]

register_hotkeys(bindings)
start_checking_hotkeys()

print("Listening for control, shift, alt for 5 seconds...")
time.sleep(5)
stop_checking_hotkeys()
print("Done.")
