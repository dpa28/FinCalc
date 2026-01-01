from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineListItem
from kivymd.uix.boxlayout import MDBoxLayout
import app_state

# --- CONSTANTS ---
COINGECKO_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "CNY", "AUD", "CAD", "CHF", "HKD", "SGD", 
    "INR", "KRW", "RUB", "BRL", "NGN", "TRY", "MXN", "ZAR", "AED", "SAR",
    "BTC", "ETH", "SATS", "XAU", "XAG", "ARS", "BDT", "BHD", "BMD", "CLP", 
    "CZK", "DKK", "GEL", "HUF", "IDR", "ILS", "KWD", "LKR", "MMK", "MYR", 
    "NOK", "NZD", "PHP", "PKR", "PLN", "SEK", "THB", "TWD", "UAH", "VEF", 
    "VND", "XDR", "BNB", "XRP", "SOL", "DOT", "LINK", "LTC", "BCH", "XLM", "EOS", "YFI", "BITS"
]
ICON_SUPPORTED_CURRENCIES = ["usd", "eur", "gbp", "jpy", "cny", "inr", "rub", "btc", "eth", "krw", "try", "ngn"]
FALLBACK_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CNY", "RUB", "INR", "BRL", "CAD", "AUD"]

def get_currency_symbol(code):
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", 
        "INR": "₹", "BRL": "R$", "RUB": "₽", "KRW": "₩", "TRY": "₺", 
        "NGN": "₦", "ZAR": "R", "PHP": "₱", "THB": "฿", "VND": "₫"
    }
    return symbols.get(code, f"{code} ")

class CurrencySelectorContent(MDBoxLayout): 
    pass

class CurrencySearchHelper:
    # FIXED: Removed 'app' from signature. We use app_state now.
    def __init__(self, callback, specific_list=None):
        self.callback = callback
        self.specific_list = specific_list
        self.all_currencies = []
        self.dialog = None

    def open_selector(self):
        if self.specific_list: 
            self.all_currencies = self.specific_list
        elif app_state.global_currency_list: 
            self.all_currencies = app_state.global_currency_list
        else: 
            self.all_currencies = FALLBACK_CURRENCIES
            
        self.content = CurrencySelectorContent()
        self.content.ids.search_field.bind(text=self.filter_list)
        
        initial_view = self.all_currencies if len(self.all_currencies) < 100 else FALLBACK_CURRENCIES
        self.populate_list(initial_view)
        
        self.dialog = MDDialog(
            title="Select Currency", 
            type="custom", 
            content_cls=self.content, 
            buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def populate_list(self, currency_list):
        scroll_list = self.content.ids.currency_scroll_list
        scroll_list.clear_widgets()
        for code in currency_list:
            item = OneLineListItem(text=code, on_release=lambda x, c=code: self.select_item(c))
            scroll_list.add_widget(item)

    def filter_list(self, instance, text):
        query = text.upper().strip()
        if not query: 
            default_view = self.all_currencies if len(self.all_currencies) < 100 else FALLBACK_CURRENCIES
            self.populate_list(default_view)
        else: 
            filtered = [c for c in self.all_currencies if query in c]
            self.populate_list(filtered)

    def select_item(self, code): 
        self.dialog.dismiss()
        self.callback(code)