import logging
import uuid
import os
import io
import yfinance as yf
import pandas as pd
from kivymd.toast import toast
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

from datetime import datetime
from kivymd.app import MDApp
from kivymd.uix.pickers import MDDatePicker, MDTimePicker
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget, IconRightWidget, OneLineListItem
from kivy.core.image import Image as CoreImage

from threading_utils import run_bg, ui
import app_state

class PortfolioScreen(MDScreen):
    dialog = None
    
    # Input Fields
    ticker_field = None
    shares_field = None
    date_field = None
    time_field = None
    selected_date_obj = None
    
    def on_enter(self):
        self.ids.balance_label.text = "Loading..."
        self.ids.gain_label.text = ""
        self.ids.chart_image.opacity = 0
        run_bg(self.refresh_portfolio_data)

    # --- CSV EXPORT (NEW) ---
    def export_portfolio_csv(self):
        try:
            data = app_state.get_portfolio()
            if not data:
                toast("Portfolio is empty")
                return

            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Save to "Portable" Directory
            filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d')}.csv"
            path = os.path.join(app_state.base_dir, filename)
            
            df.to_csv(path, index=False)
            toast(f"Exported to {filename}")
        except Exception as e:
            logging.error(f"Export Error: {e}")
            toast("Export Failed")

    # --- PICKER METHODS ---
    def open_date_picker_btn(self, instance):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.on_date_save)
        date_dialog.open()

    def on_date_save(self, instance, value, date_range):
        if hasattr(self, 'date_field'):
            self.date_field.text = str(value)
        self.selected_date_obj = value

    def open_time_picker_btn(self, instance):
        time_dialog = MDTimePicker()
        time_dialog.bind(on_save=self.on_time_save)
        time_dialog.open()

    def on_time_save(self, instance, time):
        if hasattr(self, 'time_field'):
            self.time_field.text = str(time)

    # --- DATA REFRESH LOGIC ---
    def refresh_portfolio_data(self):
        holdings = app_state.get_portfolio()
        if not holdings:
            ui(self.update_ui_empty)
            return

        try:
            unique_tickers = list(set([t['ticker'] for t in holdings]))
            current_prices = {}
            
            if unique_tickers:
                data = yf.download(unique_tickers, period="1d", group_by='ticker', progress=False)
                
                for ticker in unique_tickers:
                    try:
                        if data.empty: price = 0.0
                        elif isinstance(data.columns, pd.MultiIndex) and ticker in data.columns:
                            price = data[ticker]['Close'].iloc[-1].item()
                        elif 'Close' in data.columns:
                            price = data['Close'].iloc[-1].item()
                        else: price = 0.0
                        current_prices[ticker] = price
                    except:
                        current_prices[ticker] = 0.0

            total_value = 0.0
            total_cost = 0.0
            allocation_data = {} 
            enriched_holdings = []

            for trade in holdings:
                t_ticker = trade['ticker']
                t_shares = float(trade['shares'])
                t_cost_basis = float(trade['cost_basis'])
                
                live_price = current_prices.get(t_ticker, t_cost_basis)
                current_market_value = live_price * t_shares
                original_cost = t_cost_basis * t_shares
                
                total_value += current_market_value
                total_cost += original_cost
                
                if t_ticker in allocation_data:
                    allocation_data[t_ticker] += current_market_value
                else:
                    allocation_data[t_ticker] = current_market_value

                enriched_holdings.append({
                    "data": trade,
                    "current_price": live_price,
                    "market_value": current_market_value,
                    "gain_val": current_market_value - original_cost,
                    "gain_pct": ((current_market_value - original_cost)/original_cost)*100 if original_cost else 0
                })

            chart_bytes = self.generate_pie_chart(allocation_data)

            ui_data = {
                "holdings": enriched_holdings,
                "total_value": total_value,
                "total_gain": total_value - total_cost,
                "total_gain_pct": ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
                "chart_bytes": chart_bytes
            }
            ui(self.update_ui_full, ui_data)

        except Exception as e:
            logging.error(f"Portfolio Calc Error: {e}")
            ui(self.show_error, "Failed to fetch prices")

    def generate_pie_chart(self, allocation_data):
        fig = None
        try:
            labels = [l for l,s in allocation_data.items() if s > 0]
            sizes = [s for s in allocation_data.values() if s > 0]
            if not sizes: return None
            
            app = MDApp.get_running_app()
            is_dark = app.theme_cls.theme_style == "Dark"
            text_color = "white" if is_dark else "black"

            plt.close('all')
            fig = plt.figure(figsize=(6, 6), dpi=100, facecolor='none')
            colors = ['#00897B', '#4DB6AC', '#80CBC4', '#B2DFDB', '#00695C']
            
            patches, texts, autotexts = plt.pie(
                sizes, labels=labels, autopct='%1.1f%%', 
                startangle=90, colors=colors[:len(labels)]
            )
            
            for t in texts:
                t.set_color(text_color)
                t.set_fontsize(10)
            
            for t in autotexts:
                t.set_color('white')
                t.set_fontsize(9)
                t.set_weight('bold')

            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', transparent=True)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            return None
        finally:
            if fig: plt.close(fig)

    def update_ui_empty(self):
        self.ids.balance_label.text = "$0.00"
        self.ids.gain_label.text = "No positions"
        self.ids.chart_image.opacity = 0
        self.ids.portfolio_list.clear_widgets()

    def update_ui_full(self, data):
        val = data['total_value']
        gain = data['total_gain']
        pct = data['total_gain_pct']
        
        self.ids.balance_label.text = f"${val:,.2f}"
        symbol = "+" if gain >= 0 else ""
        self.ids.gain_label.text = f"{symbol}${gain:,.2f} ({symbol}{pct:.2f}%)"
        self.ids.gain_label.text_color = "#00C853" if gain >= 0 else "#D50000"

        self.ids.portfolio_list.clear_widgets()
        for item in data['holdings']:
            trade = item['data']
            li = TwoLineAvatarIconListItem(
                text=f"{trade['ticker']} ({trade['shares']} sh) @ ${trade['cost_basis']:.2f}",
                secondary_text=f"Current: ${item['market_value']:,.2f} | {symbol}${item['gain_val']:,.2f} ({symbol}{item['gain_pct']:.1f}%)",
                on_release=lambda x, i=item: self.show_trade_details(i)
            )
            li.add_widget(IconLeftWidget(icon="chart-pie"))
            li.add_widget(IconRightWidget(icon="trash-can", on_release=lambda x, tid=trade['id']: self.delete_trade(tid)))
            self.ids.portfolio_list.add_widget(li)

        if data['chart_bytes']:
            self.ids.chart_image.texture = CoreImage(io.BytesIO(data['chart_bytes']), ext="png").texture
            self.ids.chart_image.opacity = 1

    def delete_trade(self, trade_id):
        app_state.remove_trade(trade_id)
        run_bg(self.refresh_portfolio_data)

    def show_trade_details(self, item):
        trade = item['data']
        details = [
            f"Ticker: {trade['ticker']}", f"Shares: {trade['shares']}",
            f"Purchase Date: {trade['date']}", f"Time: {trade.get('time','')}",
            f"Cost Basis: ${trade['cost_basis']:,.2f}", "-------------------",
            f"Current Value: ${item['market_value']:,.2f}", f"Gain/Loss: ${item['gain_val']:,.2f}"
        ]
        content = MDBoxLayout(orientation="vertical", spacing="10dp", adaptive_height=True)
        for line in details: content.add_widget(OneLineListItem(text=line, divider=None))
        self.dialog = MDDialog(title="Trade Details", type="custom", content_cls=content, buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.dialog.dismiss())])
        self.dialog.open()

    def show_add_dialog(self):
        self.ticker_field = MDTextField(hint_text="Ticker", mode="rectangle")
        self.shares_field = MDTextField(hint_text="Shares", input_filter="float", mode="rectangle")
        self.date_field = MDTextField(hint_text="Date", mode="rectangle", icon_right="calendar", text=str(datetime.now().date()))
        self.time_field = MDTextField(hint_text="Time", mode="rectangle", icon_right="clock", text=datetime.now().strftime("%H:%M:%S"))
        self.selected_date_obj = datetime.now().date()

        btn_box = MDBoxLayout(orientation="horizontal", spacing="10dp", adaptive_height=True)
        btn_box.add_widget(MDFlatButton(text="DATE", on_release=self.open_date_picker_btn))
        btn_box.add_widget(MDFlatButton(text="TIME", on_release=self.open_time_picker_btn))

        content = MDBoxLayout(orientation="vertical", spacing="12dp", height="350dp", size_hint_y=None)
        content.add_widget(self.ticker_field)
        content.add_widget(self.shares_field)
        content.add_widget(self.date_field)
        content.add_widget(self.time_field)
        content.add_widget(btn_box)

        self.dialog = MDDialog(title="Simulate Trade", type="custom", content_cls=content, buttons=[
            MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
            MDRaisedButton(text="SIMULATE", on_release=self.process_trade)
        ])
        self.dialog.open()

    def process_trade(self, *args):
        if not self.ticker_field.text or not self.shares_field.text:
            return 

        try:
            shares = float(self.shares_field.text)
            ticker = self.ticker_field.text.upper().strip()
            date_obj = getattr(self, 'selected_date_obj', None)
            time_text = self.time_field.text if hasattr(self, 'time_field') else "12:00:00"

            from threading_utils import run_bg
            run_bg(self.fetch_historical_price, ticker, date_obj, time_text, shares)
            
            self.dialog.dismiss()
        except ValueError:
            toast("Invalid number format")

    def fetch_historical_price(self, ticker, date_obj, time_text, shares):
        try:
            stock = yf.Ticker(ticker)
            check_data = stock.history(period="5d")
            
            if check_data.empty:
                ui(toast, f"Error: Stock '{ticker}' not found.")
                return

            if date_obj:
                target_date = date_obj.strftime("%Y-%m-%d")
                hist = stock.history(start=target_date, period="5d")
                price = float(hist.iloc[0]['Open']) if not hist.empty else float(check_data.iloc[-1]['Close'])
            else:
                price = float(check_data.iloc[-1]['Close'])

            asset_data = {
                "id": str(uuid.uuid4()),
                "ticker": ticker,
                "shares": shares,
                "cost_basis": price,
                "price": price,
                "date": date_obj.strftime("%Y-%m-%d") if date_obj else "Today",
                "time": time_text
            }
            ui(self.finish_trade, asset_data)
        except Exception as e:
            ui(toast, f"Error adding stock: {str(e)}")

    def finish_trade(self, asset_data):
        if app_state:
            app_state.add_trade(asset_data)
        self.refresh_portfolio_data()
        toast(f"Added {asset_data['ticker']} @ ${asset_data['cost_basis']:.2f}")

    def show_error(self, msg): 
        self.ids.gain_label.text = msg