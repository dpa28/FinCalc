import threading
from kivy.clock import Clock

def run_bg(target, *args, **kwargs):
    """Runs a function in a background thread."""
    threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

def ui(callback, *args, **kwargs):
    """Schedules a function to run on the main UI thread."""
    Clock.schedule_once(lambda dt: callback(*args, **kwargs))