import logging
import io
import re  # <--- NEW: Regex support
import yfinance as yf
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.core.image import Image as CoreImage
from kivymd.toast import toast
from threading_utils import run_bg, ui

class StockScreen(MDScreen):
    def on_enter(self):
        app = MDApp.get_running_app()
        if 'ticker_field' in self.ids:
            self.ids.ticker_field.text = app.last_ticker
            self.search_stock(save=False)

    def search_stock(self, save=True):
        if 'ticker_field' not in self.ids: return
        
        raw_ticker = self.ids.ticker_field.text.strip().upper()
        
        # --- FIX: STRICT VALIDATION ---
        # Allow A-Z, 0-9, and hyphen/period (for crypto/foreign stocks like BTC-USD or 7203.T)
        if not re.match(r'^[A-Z0-9\-\.]{1,10}$', raw_ticker):
            ui(self.update_label, "Invalid Ticker")
            toast("Invalid Format: Use letters/numbers only")
            return

        if save:
            app = MDApp.get_running_app()
            app.save_setting("last_ticker", raw_ticker)

        if 'price_label' in self.ids: self.ids.price_label.text = "Loading..."
        if 'chart_image' in self.ids: self.ids.chart_image.opacity = 0
        
        run_bg(self.fetch_stock_data, raw_ticker, "1mo")

    def fetch_stock_data(self, ticker, period="1mo"):
        data = None
        try:
            stock = yf.Ticker(ticker)
            
            interval = "2m" if period == "1d" else "1d"
            if period == "1wk": interval = "1h"
            
            hist = stock.history(period=period, interval=interval)
            info = stock.info
            
            if hist.empty:
                ui(self.update_label, "No Data")
                return

            current_price = hist['Close'].iloc[-1]
            start_price = hist['Close'].iloc[0]
            
            change = current_price - start_price
            pct_change = (change / start_price) * 100 if start_price != 0 else 0
            
            color = "#00C853" if change >= 0 else "#D50000"
            change_str = f"{change:+.2f} ({pct_change:+.2f}%)"

            chart_buf = self.generate_chart(hist, change >= 0, period)
            
            data = {
                'price': f"${current_price:,.2f}",
                'change': change_str,
                'color': color,
                'chart': chart_buf,
                'details': {
                    'open': info.get('open', 0),
                    'high': info.get('dayHigh', 0),
                    'low': info.get('dayLow', 0),
                    'mkt_cap': info.get('marketCap', 0),
                    'pe': info.get('trailingPE', 0),
                    'vol': info.get('volume', 0)
                }
            }
            ui(self.display_data, data)
            
        except Exception as e:
            logging.error(f"Stock Error: {e}")
            ui(self.update_label, "Fetch Failed")

    def generate_chart(self, hist, is_green, period):
        fig = None
        try:
            app = MDApp.get_running_app()
            is_dark = app.theme_cls.theme_style == "Dark"
            text_color = "white" if is_dark else "black"
            
            plt.close('all')
            fig, ax = plt.subplots(figsize=(5, 3.5), facecolor='none') 
            color = '#00C853' if is_green else '#D50000'
            
            ax.plot(hist.index, hist['Close'], color=color, linewidth=2)
            ax.fill_between(hist.index, hist['Close'], hist['Close'].min(), color=color, alpha=0.1)
            
            ax.grid(True, linestyle='--', alpha=0.3, color=text_color)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color(text_color)
            ax.spines['left'].set_color(text_color)
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            
            if period == "1d":
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            elif period in ["1mo", "3mo"]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                
            plt.xticks(rotation=45, fontsize=8)
            plt.yticks(fontsize=8)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', transparent=True)
            buf.seek(0)
            return buf
        except Exception:
            return None
        finally:
            if fig:
                plt.close(fig)

    def update_label(self, text):
        if 'price_label' in self.ids:
            self.ids.price_label.text = text
            self.ids.price_label.theme_text_color = "Primary"

    def display_data(self, data):
        if 'price_label' in self.ids:
            self.ids.price_label.text = f"{data['price']}\n{data['change']}"
            self.ids.price_label.theme_text_color = "Custom"
            self.ids.price_label.text_color = data['color']
        
        if 'chart_image' in self.ids and data['chart']:
            im_data = io.BytesIO(data['chart'].getvalue())
            self.ids.chart_image.texture = CoreImage(im_data, ext="png").texture
            self.ids.chart_image.opacity = 1
            
        det = data.get('details', {})
        if 'lbl_open' in self.ids: self.ids.lbl_open.text = f"Open: ${det['open']:,.2f}"
        if 'lbl_high' in self.ids: self.ids.lbl_high.text = f"High: ${det['high']:,.2f}"
        if 'lbl_low' in self.ids: self.ids.lbl_low.text = f"Low: ${det['low']:,.2f}"
        if 'lbl_cap' in self.ids:
            cap = det['mkt_cap']
            if cap is None: cap = 0
            if cap > 1e12: cap_str = f"{cap/1e12:.2f}T"
            elif cap > 1e9: cap_str = f"{cap/1e9:.2f}B"
            else: cap_str = f"{cap/1e6:.2f}M"
            self.ids.lbl_cap.text = f"Mkt Cap: {cap_str}"