import logging
import sys
import os
from kivy.utils import platform

# Window size for desktop dev
if platform not in ['android', 'ios']:
    from kivy.core.window import Window
    Window.size = (360, 640)

from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.storage.jsonstore import JsonStore 

from threading_utils import run_bg
import app_state # <--- Uses the new portable base_dir

# Import Screens
from screens.stock import StockScreen
from screens.crypto import CryptoScreen
from screens.currency_converter import CurrencyScreen
from screens.calculator import CalculatorScreen
from screens.settings import SettingsScreen
from screens.portfolio import PortfolioScreen

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FinCalcApp(MDApp):
    # Global Settings
    default_currency = StringProperty("USD")
    default_rf = NumericProperty(4.2)
    last_ticker = StringProperty("NVDA")
    debug_mode = BooleanProperty(False)

    def build(self):
        self.title = "FinCalc"
        self.theme_cls.primary_palette = "Teal"
        
        # --- PORTABLE MODE ---
        # Saves 'user_settings.json' right next to FinCalc.exe
        settings_file = os.path.join(app_state.base_dir, "user_settings.json")
        self.store = JsonStore(settings_file)
        
        # 1. Load All Settings
        if self.store.exists("config"):
            config = self.store.get("config")
            
            # Visuals
            self.theme_cls.theme_style = config.get("theme_style", "Light")
            self.theme_cls.primary_palette = config.get("primary_palette", "Teal")
            
            # Data
            self.default_currency = config.get("default_currency", "USD")
            self.default_rf = config.get("default_rf", 4.2)
            self.last_ticker = config.get("last_ticker", "NVDA")
            self.debug_mode = config.get("debug_mode", False)
        
        return Builder.load_file(resource_path("interface.kv"))

    def save_setting(self, key, value):
        """Universal Save Function"""
        if hasattr(self, key):
            setattr(self, key, value)
            
        if key == "theme_style":
            self.theme_cls.theme_style = value
        elif key == "primary_palette":
            self.theme_cls.primary_palette = value

        if self.store.exists("config"):
            config = self.store.get("config")
        else:
            config = {}
            
        config[key] = value
        self.store.put("config", **config)

if __name__ == "__main__":
    FinCalcApp().run()