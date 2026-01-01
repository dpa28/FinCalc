from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.button import MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast

class SettingsScreen(MDScreen):
    dialog = None

    def on_enter(self):
        app = MDApp.get_running_app()
        if 'rf_label' in self.ids:
            self.ids.rf_label.secondary_text = f"{app.default_rf}%"
        if 'curr_label' in self.ids:
            self.ids.curr_label.secondary_text = app.default_currency
        
        if 'debug_label' in self.ids:
            is_debug = getattr(app, 'debug_mode', False)
            self.ids.debug_label.secondary_text = "Enabled" if is_debug else "Disabled"
            self.ids.debug_icon.icon = "bug" if is_debug else "bug-outline"

    def toggle_dark_mode(self):
        app = MDApp.get_running_app()
        new_style = "Dark" if app.theme_cls.theme_style == "Light" else "Light"
        app.save_setting("theme_style", new_style)

    def change_theme_color(self):
        colors = ["Teal", "Green", "Blue", "Purple", "Red", "Orange", "Amber", "DeepOrange"]
        items = [OneLineAvatarIconListItem(text=c, on_release=lambda x, c=c: self.set_color(c)) for c in colors]
            
        self.dialog = MDDialog(
            title="Pick a Color", type="simple", items=items,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def set_color(self, color_name):
        app = MDApp.get_running_app()
        app.save_setting("primary_palette", color_name)
        if self.dialog: self.dialog.dismiss()

    def change_rf_rate(self):
        app = MDApp.get_running_app()
        
        self.tf_rate = MDTextField(
            text=str(app.default_rf),
            hint_text="Risk-Free Rate (%)",
            input_filter="float",
            mode="rectangle"
        )
        
        content = MDBoxLayout(orientation="vertical", size_hint_y=None, height="80dp")
        content.add_widget(self.tf_rate)

        self.dialog = MDDialog(
            title="Set Risk-Free Rate",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDFlatButton(text="SAVE", on_release=self.save_rf_from_dialog)
            ]
        )
        self.dialog.open()

    def save_rf_from_dialog(self, btn):
        # --- FIX: INPUT VALIDATION ---
        try:
            val_text = self.tf_rate.text.replace(',', '.')
            val = float(val_text)
            app = MDApp.get_running_app()
            app.save_setting("default_rf", val)
            if 'rf_label' in self.ids:
                self.ids.rf_label.secondary_text = f"{val}%"
            self.dialog.dismiss()
        except ValueError:
            self.tf_rate.error = True
            toast("Invalid number")

    def change_default_currency(self):
        currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CNY", "INR"]
        items = [OneLineAvatarIconListItem(text=c, on_release=lambda x, c=c: self.set_currency(c)) for c in currencies]

        self.dialog = MDDialog(
            title="Select Currency", type="simple", items=items,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def set_currency(self, currency):
        app = MDApp.get_running_app()
        app.save_setting("default_currency", currency)
        if 'curr_label' in self.ids:
            self.ids.curr_label.secondary_text = currency
        if self.dialog: self.dialog.dismiss()

    def toggle_debug(self):
        app = MDApp.get_running_app()
        current = getattr(app, 'debug_mode', False)
        app.debug_mode = not current
        app.save_setting("debug_mode", app.debug_mode)
        
        if 'debug_label' in self.ids:
            self.ids.debug_label.secondary_text = "Enabled" if app.debug_mode else "Disabled"
            self.ids.debug_icon.icon = "bug" if app.debug_mode else "bug-outline"