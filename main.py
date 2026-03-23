import os
import json
import threading
import base64
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from plyer import filechooser

# 🎯 النواة العسكرية لاستخراج البيانات
SYSTEM_PROMPT = """
"ROLE": "You are HCG-TRADER V18 Mobile Core. Analyze the chart and extract precise technical data."
"TASK": "Read indicators and output trading signal strictly in JSON. No text."
"JSON_SCHEMA": {
  "asset_data": {"symbol": "string", "current_price": "float"},
  "technical_indicators": {"atr_value": "float", "adx_value": "float", "rsi_value": "float"},
  "action_plan": {"signal": "BUY or SELL or WAIT", "entry_price": "float", "stop_loss": "float", "take_profit_1": "float"},
  "system_diagnostics": {"confidence_score": "integer", "veto_warning": "string"}
}
"""

class SetupScreen(Screen):
    def __init__(self, **kwargs):
        super(SetupScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        
        layout.add_widget(Label(text="[ HCG-TRADER V18: SECURITY VAULT ]", font_size='22sp', color=(1, 0, 0, 1), size_hint=(1, 0.2)))
        layout.add_widget(Label(text="Enter Gemini API Key:", size_hint=(1, 0.1)))
        
        self.api_input = TextInput(multiline=False, password=True, hint_text="AIzaSy...")
        layout.add_widget(self.api_input)
        
        save_btn = Button(text="SAVE & INITIALIZE CORE", background_color=(0, 0.8, 0, 1), size_hint=(1, 0.3))
        save_btn.bind(on_press=self.save_key)
        layout.add_widget(save_btn)
        
        self.add_widget(layout)

    def save_key(self, instance):
        key = self.api_input.text.strip()
        if key:
            App.get_running_app().store.put('credentials', api_key=key)
            App.get_running_app().api_key = key
            self.manager.current = 'main'

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.selected_image_path = None
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # شريط التحكم
        top_bar = BoxLayout(orientation='horizontal', size_hint=(1, 0.1))
        self.status_label = Label(text="[ STANDBY ]", color=(0, 1, 0, 1))
        settings_btn = Button(text="⚙️ Key", size_hint=(0.3, 1), background_color=(0.5, 0.5, 0.5, 1))
        settings_btn.bind(on_press=self.go_to_settings)
        top_bar.add_widget(self.status_label)
        top_bar.add_widget(settings_btn)
        layout.add_widget(top_bar)
        
        # شاشة عرض الشارت
        self.img_preview = KivyImage(source='')
        layout.add_widget(self.img_preview)
        
        # أزرار الأوامر
        btn_select = Button(text="1. LOAD CHART", size_hint=(1, 0.15), background_color=(0.2, 0.6, 1, 1))
        btn_select.bind(on_press=self.open_file_chooser)
        layout.add_widget(btn_select)
        
        btn_analyze = Button(text="2. EXECUTE SCAN", size_hint=(1, 0.15), background_color=(1, 0, 0, 1))
        btn_analyze.bind(on_press=self.start_analysis_thread)
        layout.add_widget(btn_analyze)
        
        self.add_widget(layout)

    def go_to_settings(self, instance):
        self.manager.current = 'setup'

    def open_file_chooser(self, instance):
        try:
            filechooser.open_file(on_selection=self.handle_selection)
        except Exception as e:
            self.status_label.text = "[ STORAGE PERMISSION DENIED ]"

    def handle_selection(self, selection):
        if selection:
            self.selected_image_path = selection[0]
            self.img_preview.source = self.selected_image_path
            self.status_label.text = "[ CHART LOADED ]"

    def start_analysis_thread(self, instance):
        if not self.selected_image_path:
            self.status_label.text = "[ NO CHART SELECTED ]"
            return
        
        self.status_label.text = "[ SCANNING BATTLEFIELD... ]"
        self.status_label.color = (1, 1, 0, 1) # أصفر
        threading.Thread(target=self.analyze_chart_logic).start()

    def analyze_chart_logic(self):
        try:
            # 1. تشفير الصورة إلى Base64
            with open(self.selected_image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            api_key = App.get_running_app().api_key
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            # 2. تجهيز الحمولة (Payload)
            payload = {
                "contents": [{
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"inline_data": {"mime_type": "image/jpeg", "data": encoded_string}}
                    ]
                }]
            }
            headers = {'Content-Type': 'application/json'}

            # 3. إطلاق الرصاصة (REST API Call)
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # 4. تفكيك الرد
            res_json = response.json()
            result_text = res_json['candidates'][0]['content']['parts'][0]['text']
            
            # تنظيف الـ JSON
            clean_json = result_text.replace('```json', '').replace('```', '').strip()
            parsed_data = json.loads(clean_json)
            
            signal = parsed_data['action_plan']['signal']
            sl = parsed_data['action_plan']['stop_loss']
            veto = parsed_data['system_diagnostics']['veto_warning']
            
            if signal == "WAIT":
                final_text = f"🛑 {signal} | VETO: {veto}"
                color = (1, 0, 0, 1)
            else:
                final_text = f"🟢 {signal} | SL: {sl}"
                color = (0, 1, 0, 1)
                
            Clock.schedule_once(lambda dt: self.update_ui(final_text, color))
            
        except requests.exceptions.HTTPError as err:
            Clock.schedule_once(lambda dt: self.update_ui("[ API KEY ERROR / NETWORK ]", (1, 0, 0, 1)))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.update_ui("[ SYSTEM ERROR / INVALID JSON ]", (1, 0, 0, 1)))
            print(e)

    def update_ui(self, text, color):
        self.status_label.text = text
        self.status_label.color = color

class HCGTraderApp(App):
    def build(self):
        self.store = JsonStore('hcg_vault.json')
        self.api_key = None
        
        sm = ScreenManager()
        sm.add_widget(SetupScreen(name='setup'))
        sm.add_widget(MainScreen(name='main'))
        
        if self.store.exists('credentials'):
            self.api_key = self.store.get('credentials')['api_key']
            sm.current = 'main'
        else:
            sm.current = 'setup'
            
        return sm

if __name__ == '__main__':
    HCGTraderApp().run()
