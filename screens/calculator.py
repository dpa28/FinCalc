import math
import re
import logging
import ast
import operator

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRectangleFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty

# --- SAFE IMPORTS ---
try:
    import app_state  # Required for history persistence
except ImportError:
    app_state = None

# --- LIMITS TO PREVENT HANGS ---
MAX_POWER = 10000  # Prevents 9^9^9^9
MAX_NODES = 500    # Prevents deeply nested equations
MAX_RESULT = 1e100 # Prevents memory overflow

# --- PHASE 3.3: Safe Math Operators (HARDENED) ---
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    'sqrt': math.sqrt,
    'log': math.log,
    'ln': math.log,
    'exp': math.exp,
    'abs': abs,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
}

class CalculatorScreen(MDScreen):
    display_text = ObjectProperty(None)
    
    # History State
    history_list = []
    history_index = -1 
    temp_input = ""    

    # Menus
    dialog = None 
    current_time_field = None
    current_unit_btn = None
    time_menu = None

    def on_enter(self):
        if app_state:
            self.history_list = app_state.get_calc_history()
        self.history_index = -1

    def safe_eval_node(self, node, depth=0):
        """Recursive evaluator with safety guards and complexity limits."""
        if depth > 100: 
            raise ValueError("Expression too complex")
        
        # Numbers / Constants
        if isinstance(node, (ast.Constant, ast.Num)):
            val = node.value if isinstance(node, ast.Constant) else node.n
            if isinstance(val, (int, float)): return val
            raise ValueError("Unsupported constant type")
            
        # Binary Operations (1 + 1, 9 ^ 9)
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError("Unsupported operator")
            
            left = self.safe_eval_node(node.left, depth + 1)
            right = self.safe_eval_node(node.right, depth + 1)
            
            # --- CRITICAL HANG PREVENTER: Power Guard ---
            if op_type == ast.Pow:
                if right > MAX_POWER or (abs(left) > 1 and right > 500):
                    raise OverflowError("Power too large")
            
            result = SAFE_OPERATORS[op_type](left, right)
            
            # Prevent memory overflow from massive results
            if isinstance(result, (int, float)) and abs(result) > MAX_RESULT:
                raise OverflowError("Result too large")
            return result

        # Unary Operations (-5, +5)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError("Unsupported unary operator")
            return SAFE_OPERATORS[op_type](self.safe_eval_node(node.operand, depth + 1))

        # Functions (sqrt, sin, etc)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name): 
                raise ValueError("Simple functions only")
            
            func_name = node.func.id
            if func_name not in SAFE_FUNCTIONS: 
                raise ValueError(f"Unknown function: {func_name}")
            
            if len(node.args) != 1: 
                raise ValueError("One argument required")
                
            arg = self.safe_eval_node(node.args[0], depth + 1)
            return SAFE_FUNCTIONS[func_name](arg)

        raise ValueError("Unsafe syntax detected")

    # --- UI & NAVIGATION ---
    def move_cursor(self, direction):
        if not self.display_text: return
        self.display_text.focus = True
        col, _ = self.display_text.cursor
        text_len = len(self.display_text.text)
        new_col = max(0, col - 1) if direction == 'left' else min(text_len, col + 1)
        self.display_text.cursor = (new_col, 0)

    def navigate_history(self, direction):
        if app_state and not self.history_list:
            self.history_list = app_state.get_calc_history()
        if not self.history_list: return 

        if direction == 'up':
            if self.history_index == -1:
                self.temp_input = self.display_text.text
                self.history_index = len(self.history_list) - 1
            else:
                self.history_index = max(0, self.history_index - 1)
        elif direction == 'down':
            if self.history_index == -1: return
            self.history_index += 1
            if self.history_index >= len(self.history_list):
                self.history_index = -1
                self.display_text.text = self.temp_input
                return

        if self.history_index != -1:
            self.display_text.text = self.history_list[self.history_index]

    def add_to_display(self, value):
        if self.display_text.text in ["Error", "Syntax Error", "Too Large", "Div by 0", "Overflow"]:
            self.display_text.text = ""
        
        col, _ = self.display_text.cursor
        current = self.display_text.text
        self.display_text.text = current[:col] + str(value) + current[col:]
        self.display_text.cursor = (col + 1, 0)

    def remove_last(self):
        if self.display_text.text in ["Error", "Syntax Error", "Too Large"]:
            self.display_text.text = ""
            return
        col, _ = self.display_text.cursor
        if col > 0:
            current = self.display_text.text
            self.display_text.text = current[:col-1] + current[col:]
            self.display_text.cursor = (col - 1, 0)

    def clear_display(self):
        self.display_text.text = ""
        self.history_index = -1

    def calculate_result(self, *args):
        raw = self.display_text.text.strip()
        if not raw or raw == "0": 
            self.display_text.text = "0"
            return

        try:
            # --- 1. CLEANING & IMPLICIT MULTIPLICATION ---
            # Handles (9)(9), 9π, 9√, 9(5)
            clean = re.sub(r'(\d)([√π\(])', r'\1*\2', raw)
            clean = re.sub(r'(\))(\d)', r'\1*\2', clean)
            clean = re.sub(r'(\))(\()', r'\1*\2', clean)
            
            clean = clean.replace("×", "*").replace("÷", "/")
            clean = clean.replace("^", "**")
            clean = clean.replace("√", "sqrt(")
            clean = clean.replace("π", str(math.pi))
            clean = clean.replace("e", str(math.e))

            # Auto-balance parentheses
            open_c, close_c = clean.count("("), clean.count(")")
            if open_c > close_c: clean += ")" * (open_c - close_c)

            # --- 2. SECURITY & MAGNITUDE CHECK ---
            tree = ast.parse(clean, mode='eval')
            
            # Check node complexity
            if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
                self.display_text.text = "Too Complex"
                return

            # --- 3. EVALUATE ---
            
            res = self.safe_eval_node(tree.body)

            # --- 4. FORMAT OUTPUT ---
            if isinstance(res, (int, float)):
                if math.isnan(res): self.display_text.text = "Undefined"
                elif math.isinf(res): self.display_text.text = "Infinity"
                elif abs(res) > 1e15 or (0 < abs(res) < 1e-6): 
                    self.display_text.text = f"{res:.6e}"
                elif res == int(res) and abs(res) < 1e12: 
                    self.display_text.text = str(int(res))
                else: 
                    # Truncate floating point noise
                    self.display_text.text = f"{res:.10g}"
            
            if app_state:
                app_state.save_calc_history(raw)
                self.history_list = app_state.get_calc_history()

        except OverflowError: self.display_text.text = "Overflow"
        except ZeroDivisionError: self.display_text.text = "Div by 0"
        except Exception as e:
            logging.error(f"Calc Error: {e}")
            self.display_text.text = "Syntax Error"

    # --- FORMULA POPUPS ---
    def open_formula_menu(self):
        items = [
            ("Option Pricing", "bs"), ("Net Present Value", "npv"), 
            ("Compound Interest", "compound"), ("CAPM", "capm"), 
            ("Loan (PMT)", "pmt"), ("Growth (CAGR)", "cagr"), 
            ("ROI", "roi"), ("Break-Even", "breakeven"), ("Quadratic", "quad")
        ]
        menu_items = [{"text": i[0], "viewclass": "OneLineListItem", "on_release": lambda x=i[1]: self.menu_callback(x)} for i in items]
        self.menu = MDDropdownMenu(caller=self.ids.function_btn, items=menu_items, width_mult=4)
        self.menu.open()
    
    def menu_callback(self, t):
        self.menu.dismiss()
        menu_map = {
            "bs": self.show_bs_popup, "npv": self.show_npv_popup, 
            "compound": self.show_compound_popup, "capm": self.show_capm_popup, 
            "pmt": self.show_pmt_popup, "cagr": self.show_cagr_popup, 
            "roi": self.show_roi_popup, "breakeven": self.show_breakeven_popup, 
            "quad": self.show_quad_popup
        }
        if t in menu_map: menu_map[t]()

    def create_textfield(self, hint, text=""): 
        return MDTextField(hint_text=hint, text=str(text), input_filter="float", mode="fill")
    
    def create_time_widget(self):
        layout = MDBoxLayout(orientation='horizontal', spacing="10dp", size_hint_y=None, height="65dp")
        t_field = MDTextField(hint_text="Duration", input_filter="float", mode="fill", size_hint_x=0.6)
        unit_btn = MDRectangleFlatButton(text="Years", size_hint_x=0.4, pos_hint={'center_y': 0.6})
        
        def set_unit(val): 
            unit_btn.text = val
            self.time_menu.dismiss()
            
        self.time_menu = MDDropdownMenu(
            caller=unit_btn, 
            items=[
                {"text": "Years", "on_release": lambda: set_unit("Years")}, 
                {"text": "Months", "on_release": lambda: set_unit("Months")}
            ], 
            width_mult=2
        )
        unit_btn.bind(on_release=lambda x: self.time_menu.open())
        layout.add_widget(t_field); layout.add_widget(unit_btn)
        return layout, t_field, unit_btn
        
    def validate_inputs(self, fields):
        valid = True
        for f in fields:
            if not f.text: f.error = True; valid = False
            else: f.error = False
        return valid
        
    def create_popup(self, title, widgets, callback):
        content = MDBoxLayout(orientation="vertical", spacing="15dp", adaptive_height=True, padding=[0, "10dp", 0, 0])
        content.add_widget(Widget(size_hint_y=None, height="10dp"))
        for w in widgets: content.add_widget(w)
        self.dialog = MDDialog(
            title=title, type="custom", content_cls=content, 
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()), 
                MDFlatButton(text="CALCULATE", on_release=callback)
            ]
        )
        self.dialog.open()

    # --- MATH CORE ---
    def norm_cdf(self, x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def calculate_black_scholes(self, S, K, T, r, sigma, opt_type):
        if T <= 0 or sigma <= 0: return 0.0
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if opt_type == "call":
            return S * self.norm_cdf(d1) - K * math.exp(-r * T) * self.norm_cdf(d2)
        return K * math.exp(-r * T) * self.norm_cdf(-d2) - S * self.norm_cdf(-d1)

    def show_bs_popup(self):
        app = MDApp.get_running_app()
        self.bs_S, self.bs_K = self.create_textfield("Stock Price"), self.create_textfield("Strike Price")
        self.bs_v = self.create_textfield("Volatility % (e.g. 20)")
        self.bs_r = self.create_textfield("Risk-Free Rate %", str(app.default_rf))
        t_layout, self.bs_t, self.bs_unit = self.create_time_widget()
        self.create_popup("Black-Scholes", [self.bs_S, self.bs_K, self.bs_v, self.bs_r, t_layout], self.run_bs_calc)
    
    def run_bs_calc(self, inst):
        if not self.validate_inputs([self.bs_S, self.bs_K, self.bs_v, self.bs_r, self.bs_t]): return
        try:
            S, K, v, r, t = float(self.bs_S.text), float(self.bs_K.text), float(self.bs_v.text)/100, float(self.bs_r.text)/100, float(self.bs_t.text)
            if self.bs_unit.text == "Months": t /= 12.0
            call = self.calculate_black_scholes(S, K, t, r, v, "call")
            put = self.calculate_black_scholes(S, K, t, r, v, "put")
            self.display_text.text = f"C:${call:.2f} P:${put:.2f}"
            self.dialog.dismiss()
        except: self.display_text.text = "Input Error"

    def show_compound_popup(self):
        self.cp_p, self.cp_r = self.create_textfield("Principal"), self.create_textfield("Annual Rate %")
        t_layout, self.cp_t, self.cp_u = self.create_time_widget()
        self.create_popup("Compound Interest", [self.cp_p, self.cp_r, t_layout], self.run_cp_calc)

    def run_cp_calc(self, inst):
        if not self.validate_inputs([self.cp_p, self.cp_r, self.cp_t]): return
        try:
            p, r, t = float(self.cp_p.text), float(self.cp_r.text)/100, float(self.cp_t.text)
            if self.cp_u.text == "Months": t /= 12.0
            res = p * (1 + r)**t
            self.display_text.text = f"${res:,.2f}"
            self.dialog.dismiss()
        except: self.display_text.text = "Input Error"

    def show_capm_popup(self):
        app = MDApp.get_running_app()
        self.c_rf, self.c_b, self.c_rm = self.create_textfield("Risk-Free %", str(app.default_rf)), self.create_textfield("Beta"), self.create_textfield("Market Return %")
        self.create_popup("CAPM", [self.c_rf, self.c_b, self.c_rm], self.run_capm_calc)

    def run_capm_calc(self, inst):
        if not self.validate_inputs([self.c_rf, self.c_b, self.c_rm]): return
        try:
            rf, b, rm = float(self.c_rf.text), float(self.c_b.text), float(self.c_rm.text)
            res = rf + b * (rm - rf)
            self.display_text.text = f"{res:.2f}%"
            self.dialog.dismiss()
        except: self.display_text.text = "Input Error"

    def show_breakeven_popup(self):
        self.be_f, self.be_p, self.be_v = self.create_textfield("Fixed Costs"), self.create_textfield("Price Per Unit"), self.create_textfield("Var Cost Per Unit")
        self.create_popup("Break-Even", [self.be_f, self.be_p, self.be_v], self.run_be_calc)

    def run_be_calc(self, inst):
        if not self.validate_inputs([self.be_f, self.be_p, self.be_v]): return
        try:
            f, p, v = float(self.be_f.text), float(self.be_p.text), float(self.be_v.text)
            res = int(f / (p - v))
            self.display_text.text = f"{res} Units"
            self.dialog.dismiss()
        except: self.display_text.text = "Input Error"

    def show_quad_popup(self):
        self.qa, self.qb, self.qc = self.create_textfield("a"), self.create_textfield("b"), self.create_textfield("c")
        self.create_popup("Quadratic", [self.qa, self.qb, self.qc], self.run_quad_calc)

    def run_quad_calc(self, inst):
        if not self.validate_inputs([self.qa, self.qb, self.qc]): return
        try:
            a, b, c = float(self.qa.text), float(self.qb.text), float(self.qc.text)
            d = b**2 - 4*a*c
            if d < 0: self.display_text.text = "Complex Sol"
            else:
                x1 = (-b + math.sqrt(d)) / (2*a)
                x2 = (-b - math.sqrt(d)) / (2*a)
                self.display_text.text = f"{x1:.2f}, {x2:.2f}"
            self.dialog.dismiss()
        except: self.display_text.text = "Error"

    def show_roi_popup(self):
        self.ri_c, self.ri_g = self.create_textfield("Cost"), self.create_textfield("Gain")
        self.create_popup("ROI", [self.ri_c, self.ri_g], self.run_roi_calc)

    def run_roi_calc(self, inst):
        if not self.validate_inputs([self.ri_c, self.ri_g]): return
        try:
            c, g = float(self.ri_c.text), float(self.ri_g.text)
            res = ((g - c) / c) * 100
            self.display_text.text = f"{res:.2f}%"
            self.dialog.dismiss()
        except: self.display_text.text = "Error"

    def show_pmt_popup(self):
        self.pm_l, self.pm_r = self.create_textfield("Loan Principal"), self.create_textfield("Annual Rate %")
        t_layout, self.pm_t, self.pm_u = self.create_time_widget()
        self.create_popup("Loan PMT", [self.pm_l, self.pm_r, t_layout], self.run_pmt_calc)

    def run_pmt_calc(self, inst):
        if not self.validate_inputs([self.pm_l, self.pm_r, self.pm_t]): return
        try:
            p, r, t = float(self.pm_l.text), (float(self.pm_r.text)/100)/12, float(self.pm_t.text)
            n = t * 12 if self.pm_u.text == "Years" else t
            res = p * (r * (1 + r)**n) / ((1 + r)**n - 1) if r > 0 else p/n
            self.display_text.text = f"${res:.2f}/mo"
            self.dialog.dismiss()
        except: self.display_text.text = "Error"

    def show_cagr_popup(self):
        self.cg_s, self.cg_e = self.create_textfield("Initial Value"), self.create_textfield("Final Value")
        t_layout, self.cg_t, self.cg_u = self.create_time_widget()
        self.create_popup("CAGR", [self.cg_s, self.cg_e, t_layout], self.run_cagr_calc)

    def run_cagr_calc(self, inst):
        if not self.validate_inputs([self.cg_s, self.cg_e, self.cg_t]): return
        try:
            s, e, t = float(self.cg_s.text), float(self.cg_e.text), float(self.cg_t.text)
            if self.cg_u.text == "Months": t /= 12.0
            res = ((e/s)**(1/t) - 1) * 100
            self.display_text.text = f"{res:.2f}%"
            self.dialog.dismiss()
        except: self.display_text.text = "Error"

    def show_npv_popup(self):
        self.nv_f, self.nv_r = self.create_textfield("Future Cash Flow"), self.create_textfield("Discount Rate %")
        t_layout, self.nv_t, self.nv_u = self.create_time_widget()
        self.create_popup("NPV (Present Value)", [self.nv_f, self.nv_r, t_layout], self.run_npv_calc)

    def run_npv_calc(self, inst):
        if not self.validate_inputs([self.nv_f, self.nv_r, self.nv_t]): return
        try:
            f, r, t = float(self.nv_f.text), float(self.nv_r.text)/100, float(self.nv_t.text)
            if self.nv_u.text == "Months": t /= 12.0
            res = f / (1 + r)**t
            self.display_text.text = f"${res:,.2f}"
            self.dialog.dismiss()
        except: self.display_text.text = "Error"