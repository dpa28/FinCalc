from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.properties import BooleanProperty
from kivymd.toast import toast

from currency import get_currency_symbol, CurrencySearchHelper
from networking import SafeRequest
from threading_utils import run_bg, ui
import app_state

class CurrencyScreen(MDScreen):
    is_loading = BooleanProperty(False)

    def on_enter(self):
        if app_state.cache_store.exists("last_conversion"):
            last = app_state.cache_store.get("last_conversion")
            self.ids.btn_from.text = last.get('base', 'USD')
            self.ids.btn_to.text = last.get('target', 'EUR')

    def open_selector_from(self): 
        CurrencySearchHelper(lambda c: self.set_btn_text(self.ids.btn_from, c)).open_selector()

    def open_selector_to(self): 
        CurrencySearchHelper(lambda c: self.set_btn_text(self.ids.btn_to, c)).open_selector()

    def set_btn_text(self, btn, text): 
        btn.text = text
    
    def convert_currency(self):
        if self.is_loading: return
        amount_text = self.ids.amount_field.text.strip()
        
        # --- FIX: VALIDATION CRASH ---
        try:
            amount = float(amount_text)
        except ValueError:
            self.ids.amount_field.error = True
            toast("Invalid Amount")
            return
            
        self.ids.amount_field.error = False
        
        base, target = self.ids.btn_from.text, self.ids.btn_to.text
        app_state.cache_store.put("last_conversion", base=base, target=target)
        
        if base == target: 
            self.ids.result_label.text = f"{get_currency_symbol(target)}{amount:,.2f}"
            return
            
        self.is_loading = True
        self.ids.result_label.text = "Converting..."
        self.ids.rate_label.text = ""
        run_bg(self.fetch_conversion, amount, base, target)

    def fetch_conversion(self, amount, base, target):
        resp = SafeRequest.get(f"https://open.er-api.com/v6/latest/{base}")
        if resp and "rates" in resp:
            rate = resp["rates"].get(target)
            if rate: 
                val = amount * rate
                rate_text = f"1 {base} = {rate:.4f} {target}"
                ui(self.update_ui, f"{get_currency_symbol(target)}{val:,.2f}", rate_text)
            else:
                ui(self.update_ui, "Error", "Rate not found")
        else:
            ui(self.update_ui, "Error", "Network Error")

    def update_ui(self, result, rate):
        self.is_loading = False
        self.ids.result_label.text = result
        self.ids.rate_label.text = rate