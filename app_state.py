import os
import sys
from kivy.utils import platform
from kivy.storage.jsonstore import JsonStore
from cache import StockCache

# --- PORTABLE MODE PATH LOGIC ---
if platform == 'android':
    from android.storage import app_storage_path
    base_dir = app_storage_path()
elif platform == 'ios':
    base_dir = os.path.expanduser("~/Documents")
elif getattr(sys, 'frozen', False):
    # RUNNING AS EXE: Save in the exact folder where FinCalc.exe is located
    base_dir = os.path.dirname(sys.executable)
else:
    # RUNNING AS CODE: Save in the project folder
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Ensure we can write to this directory
# (Note: This might fail if you put the EXE in C:\Program Files without Admin rights)
if not os.path.exists(base_dir):
    try:
        os.makedirs(base_dir)
    except OSError:
        pass 

# Create cache directory next to the EXE
CACHE_DIR = os.path.join(base_dir, "image_cache")
if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
    except OSError:
        pass

# Persistent Store (Disk) -> Saved next to the EXE
cache_file = os.path.join(base_dir, 'data_cache.json')
cache_store = JsonStore(cache_file)

# Shared Cache (RAM)
stock_cache = StockCache(max_size=50)

# Defaults
default_currency = "USD"
default_rf = 4.2
global_currency_list = []
debug_mode = False
portfolio_data = [] 

# --- HISTORY HELPERS ---
def save_calc_history(expression):
    if not cache_store.exists("calc_history"):
        history = []
    else:
        history = cache_store.get("calc_history")['data']
    
    if history and history[-1] == expression:
        return

    history.append(expression)
    if len(history) > 50:
        history.pop(0)
        
    cache_store.put("calc_history", data=history)

def get_calc_history():
    if cache_store.exists("calc_history"):
        return cache_store.get("calc_history")['data']
    return []

# --- PORTFOLIO HELPERS ---
def get_portfolio():
    if cache_store.exists("portfolio"):
        return cache_store.get("portfolio")['data']
    return []

def add_trade(trade_data):
    holdings = get_portfolio()
    holdings.append(trade_data)
    cache_store.put("portfolio", data=holdings)

def remove_trade(trade_id):
    holdings = get_portfolio()
    updated = [t for t in holdings if t.get('id') != trade_id]
    cache_store.put("portfolio", data=updated)