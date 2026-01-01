import logging
import os
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import TwoLineAvatarIconListItem
from kivy.properties import StringProperty, BooleanProperty

from ui.widgets import CryptoListItem
from networking import SafeRequest
from currency import get_currency_symbol, CurrencySearchHelper, COINGECKO_CURRENCIES, ICON_SUPPORTED_CURRENCIES
from threading_utils import run_bg, ui
import app_state

class CryptoScreen(MDScreen):
    current_currency = StringProperty("usd")
    is_loading = BooleanProperty(False)

    def on_enter(self):
        app = MDApp.get_running_app()
        if self.current_currency.upper() != app.default_currency: 
            self.set_currency(app.default_currency)
        
        # Load Cache
        if not self.ids.crypto_list.children and app_state.cache_store.exists("last_crypto_list"):
            try:
                entry = app_state.cache_store.get("last_crypto_list")
                if 'data' in entry:
                    self.update_list(entry['data'])
            except Exception as e:
                logging.error(f"Crypto Cache Error: {e}")
            
            self.load_market_data()

    def show_currency_selector(self): 
        CurrencySearchHelper(self.set_currency, specific_list=COINGECKO_CURRENCIES).open_selector()
    
    def set_currency(self, currency_code):
        self.current_currency = currency_code.lower()
        if self.current_currency in ICON_SUPPORTED_CURRENCIES:
            self.ids.currency_btn.icon = f"currency-{self.current_currency}"
        else:
            self.ids.currency_btn.icon = "currency-sign"
        self.ids.crypto_list.clear_widgets()
        self.load_market_data()

    def load_market_data(self):
        if self.is_loading: return
        self.is_loading = True
        self.ids.loading_spinner.active = True
        run_bg(self.fetch_top_10)

    def fetch_top_10(self):
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {"vs_currency": self.current_currency, "order": "market_cap_desc", "per_page": 10, "page": 1, "sparkline": "false"}
            data = SafeRequest.get(url, params=params)
            
            if isinstance(data, list):
                # Phase 3.5: Download images for cache
                for coin in data:
                    img_url = coin.get('image')
                    coin_id = coin.get('id')
                    if img_url and coin_id:
                        local_path = os.path.join(app_state.CACHE_DIR, f"{coin_id}.png")
                        # Download if not exists or basic check (could be improved)
                        if not os.path.exists(local_path):
                            SafeRequest.download_image(img_url, local_path)
                        
                        # Update data to point to local path for offline use
                        coin['local_image'] = local_path

                app_state.cache_store.put("last_crypto_list", data=data)
                ui(self.update_list, data)
            else: 
                ui(self.show_error, "Rate Limit or Network Error")
        except Exception as e: 
            logging.error(f"Crypto Fetch Error: {e}")
            ui(self.show_error, "Unknown Error")

    def update_list(self, data):
        self.ids.loading_spinner.active = False
        self.ids.crypto_list.clear_widgets()
        self.is_loading = False
        if not isinstance(data, list): return
        
        symbol_prefix = get_currency_symbol(self.current_currency.upper())
        suffix = "" if symbol_prefix.strip() == self.current_currency.upper() else f" {self.current_currency.upper()}"

        for coin in data:
            name = coin.get('name')
            symbol = coin.get('symbol', '').upper()
            price = coin.get('current_price', 0)
            p_text = f"{symbol_prefix}{price:.6f}" if price < 0.01 else f"{symbol_prefix}{price:,.2f}"
            
            # Use local image if available, else URL
            img_src = coin.get('local_image') if coin.get('local_image') and os.path.exists(coin.get('local_image')) else coin.get('image')

            item = CryptoListItem(
                text=f"{name} ({symbol})", 
                secondary_text=f"{p_text}{suffix}",
                image_source=img_src,
                coin_data=coin,
                on_release=lambda x, c=coin: self.show_coin_details(c)
            )
            self.ids.crypto_list.add_widget(item)

    # ... (show_coin_details, search_crypto, perform_search, show_error remain same) ...
    def show_coin_details(self, coin):
        if not coin: return
        mcap = coin.get('market_cap', 0)
        vol = coin.get('total_volume', 0)
        mcap_text = f"${mcap:,.0f}" if mcap else "N/A"
        vol_text = f"${vol:,.0f}" if vol else "N/A"
        change_24h = coin.get('price_change_percentage_24h', 0)
        c_color = "00C853" if change_24h >= 0 else "D50000"
        details = (
            f"Price Change (24h): [color={c_color}]{change_24h:.2f}%[/color]\n"
            f"Market Cap: {mcap_text}\n"
            f"Volume (24h): {vol_text}\n"
            f"High 24h: {coin.get('high_24h', 0)}\n"
            f"Low 24h: {coin.get('low_24h', 0)}"
        )
        self.dialog = MDDialog(title=f"{coin.get('name')} Details", text=details, buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())])
        self.dialog.open()

    def search_crypto(self):
        query = self.ids.search_field.text.lower().strip()
        if not query or self.is_loading: return
        self.is_loading = True
        self.ids.loading_spinner.active = True
        self.ids.crypto_list.clear_widgets()
        run_bg(self.perform_search, query)

    def perform_search(self, query):
        try:
            search_data = SafeRequest.get("https://api.coingecko.com/api/v3/search", params={"query": query})
            if not search_data or not search_data.get('coins'): 
                ui(self.show_error, "No results found")
                return 
            
            top_matches = search_data['coins'][:5]
            ids = ",".join([c['id'] for c in top_matches])
            price_data = SafeRequest.get("https://api.coingecko.com/api/v3/coins/markets", params={"ids": ids, "vs_currency": self.current_currency})
            
            if not price_data: 
                ui(self.show_error, "Price fetch failed")
                return
            ui(self.update_list, price_data)
        except Exception as e: 
            logging.error(f"Search Error: {e}")
            ui(self.show_error, "Search failed")

    def show_error(self, msg):
        self.ids.loading_spinner.active = False
        self.is_loading = False
        if not self.ids.crypto_list.children:
            self.ids.crypto_list.clear_widgets()
            self.ids.crypto_list.add_widget(TwoLineAvatarIconListItem(text="Error", secondary_text=msg))
        else:
            logging.warning(f"Background update failed: {msg}")