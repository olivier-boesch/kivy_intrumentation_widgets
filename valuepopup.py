import pint
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty
from flatbutton import FlatButton, FlatToggleButton
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock

ureg = pint.UnitRegistry()

kv = '''
#:import FlatButton flatbutton
#:import FlatToggleButton flatbutton
<UnitNumberPopup>:
    title: self.title
    size_hint: 0.7, 0.7
    height: dp(400)
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(12)

        Label:
            id: display_label
            text: root.display_text
            font_size: '24sp'
            halign: 'right'
            text_size: self.width - dp(10), self.height
            size_hint_y: 0.15
            canvas.before:
                Color:
                    rgba: 0.2,0.6,0.8,0.3
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.2,0.6,0.8,1
                Line:
                    rectangle: self.x, self.y, self.width, self.height
                    width: dp(1.5)



        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.7
            spacing: dp(10)

            # Colonne 1 : Chiffres
            GridLayout:
                cols: 4
                spacing: dp(6)
                size_hint_x: 0.5

                FlatButton:
                    text: '7'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '8'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '9'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '⌫'
                    font_name: 'DejaVuSans'
                    on_release: root.press_key(self.text)

                FlatButton:
                    text: '4'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '5'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '6'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: 'Del'
                    on_release: root.press_key(self.text)

                FlatButton:
                    text: '1'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '2'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '3'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '-'
                    on_release: root.press_key(self.text)

                FlatButton:
                    text: '0'
                    on_release: root.press_key(self.text)
                FlatButton:
                    text: '.'
                    on_release: root.press_key(self.text)
                Widget:
                Widget:

            # Colonne 2 : Préfixes
            ScrollView:
                id: prefix_scrollview
                size_hint_x: 0.2
                bar_width: dp(6)
                BoxLayout:
                    id: prefixes_container
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(4)

            # Colonne 3 : Unités racines
            ScrollView:
                id: units_scrollview
                size_hint_x: 0.3
                bar_width: dp(6)
                BoxLayout:
                    id: units_container
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(4)

        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.15
            spacing: dp(12)
            FlatButton:
                text: "Cancel"
                on_release: root.dismiss()
            FlatButton:
                text: "Ok"
                bold: True
                on_release: root.validate()
'''

Builder.load_string(kv)


class UnitButton(FlatToggleButton):
    unit_obj = ObjectProperty(None)


class UnitNumberPopup(Popup):
    display_text = StringProperty("")
    input_numeric_str = StringProperty("")
    selected_prefix_str = StringProperty("")
    selected_unit_str = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.callback = None
        self.initial_value = None

    def open(self, current_value, callback, title, *args, **kwargs):
        self.callback = callback
        self.initial_value = current_value
        self.title = title
        
        self.input_numeric_str = str(current_value.magnitude)
        if self.input_numeric_str == '0':
            self.input_numeric_str = ''
        
        # Extraction du préfixe initial et de l'unité racine
        prefix, root_unit = self.extract_prefix_and_root(current_value.units)
        self.selected_prefix_str = prefix
        self.selected_unit_str = f"{root_unit:~}"
        
        self.update_display()
        self._populate_prefixes()
        self._populate_units(current_value)
        super().open(*args, **kwargs)

    def extract_prefix_and_root(self, unit_obj):
        """Sépare un objet unité Pint en son symbole de préfixe SI et son unité racine."""
        symbol = f"{unit_obj:~}"
        name = str(unit_obj)
        
        # Cas spécifique du kilogramme (unité de base SI avec préfixe)
        if name == 'kilogram' or symbol == 'kg':
            return 'k', ureg.Unit('gram')
            
        prefixes = [
            ('tera', 'T'), ('giga', 'G'), ('mega', 'M'), ('kilo', 'k'),
            ('hecto', 'h'), ('deca', 'da'), ('deci', 'd'), ('centi', 'c'),
            ('milli', 'm'), ('micro', 'µ'), ('nano', 'n'), ('pico', 'p')
        ]
        
        for long_p, short_p in prefixes:
            if name.startswith(long_p) and len(name) > len(long_p):
                root_name = name[len(long_p):]
                try:
                    return short_p, ureg.Unit(root_name)
                except Exception:
                    pass
        return '', unit_obj

    def _populate_prefixes(self):
        container = self.ids.prefixes_container
        container.clear_widgets()
        
        prefixes = [
            ('T', 'T (tera)'), ('G', 'G (giga)'), ('M', 'M (mega)'), 
            ('k', 'k (kilo)'), ('h', 'h (hecto)'), ('da', 'da (deca)'), 
            ('', '- (aucun)'),
            ('d', 'd (deci)'), ('c', 'c (centi)'), ('m', 'm (milli)'), 
            ('µ', 'µ (micro)'), ('n', 'n (nano)'), ('p', 'p (pico)')
        ]
        
        group = f'prefix_{id(self)}'
        selected_index = 0
        for i, (symbol, label) in enumerate(prefixes):
            btn = FlatToggleButton(text=label, size_hint_y=None, height=dp(40), group=group)
            if symbol == self.selected_prefix_str:
                btn.state = 'down'
                selected_index = i
            btn.bind(on_release=lambda instance, s=symbol: self.select_prefix(s))
            container.add_widget(btn)

        total = len(prefixes)
        scroll_y = 1 - selected_index / max(total - 1, 1)
        Clock.schedule_once(
            lambda _: setattr(self.ids.prefix_scrollview, 'scroll_y', scroll_y), 0.1)

    def _populate_units(self, current_value):
        container = self.ids.units_container
        container.clear_widgets()
        
        try:
            compatible_units = ureg.get_compatible_units(current_value)
            
            unique_roots = {}
            for u in compatible_units:
                _, root_obj = self.extract_prefix_and_root(u)
                root_symbol = f"{root_obj:~}"
                
                if root_symbol not in unique_roots:
                    try:
                        base_magnitude = ureg.Quantity(1, root_obj).to_base_units().magnitude
                    except Exception:
                        base_magnitude = 1.0
                    unique_roots[root_symbol] = (root_obj, base_magnitude)
            
            # Tri par ordre de magnitude de l'unité de base
            sorted_roots = sorted(unique_roots.values(), key=lambda x: (x[1], str(x[0])))

            group = f'unit_{id(self)}'
            selected_index = 0
            for i, (root_obj, _) in enumerate(sorted_roots):
                display_text = f"{root_obj:~} - {root_obj}"
                btn = UnitButton(
                    halign='center',
                    valign='center',
                    text=display_text,
                    size_hint_y=None,
                    height=dp(60),
                    unit_obj=root_obj,
                    group=group
                )
                if f"{root_obj:~}" == self.selected_unit_str:
                    btn.state = 'down'
                    selected_index = i
                btn.bind(on_release=self.select_unit)
                container.add_widget(btn)

            total = len(sorted_roots)
            scroll_y = 1 - selected_index / max(total - 1, 1)
            Clock.schedule_once(
                lambda _: setattr(self.ids.units_scrollview, 'scroll_y', scroll_y), 0.1)
                    
        except Exception as e:
            print(f"Error populating units: {e}")

    def press_key(self, key):
        if key in '0123456789':
            self.input_numeric_str += key
        elif key == '.':
            if '.' not in self.input_numeric_str:
                if self.input_numeric_str == "":
                    self.input_numeric_str = "0."
                else:
                    self.input_numeric_str += '.'
        elif key == '⌫':
            self.input_numeric_str = self.input_numeric_str[:-1]
        elif key == 'Del':
            self.input_numeric_str = ""
        elif key == '-':
            if self.input_numeric_str.startswith('-'):
                self.input_numeric_str = self.input_numeric_str[1:]
            else:
                self.input_numeric_str = '-' + self.input_numeric_str
            
        self.update_display()

    def select_prefix(self, prefix_str):
        self.selected_prefix_str = prefix_str
        self.update_display()

    def select_unit(self, instance):
        self.selected_unit_str = f"{instance.unit_obj:~}"
        self.update_display()

    def update_display(self):
        display_num = self.input_numeric_str if self.input_numeric_str else "0"
        self.display_text = f"{display_num} {self.selected_prefix_str}{self.selected_unit_str}"

    def validate(self):
        if self.callback:
            clean_str = self.input_numeric_str if (self.input_numeric_str and self.input_numeric_str != ".") else "0"
            full_unit_expr = f"{self.selected_prefix_str}{self.selected_unit_str}".strip()
            try:
                quantity = ureg.parse_expression(f"{clean_str} {full_unit_expr}")
                self.callback(quantity.to_base_units())
            except Exception as e:
                print(e)
                # Retourne la valeur initiale si la combinaison préfixe+unité est invalide pour Pint
                self.callback(self.initial_value)
        self.dismiss()


if __name__ == '__main__':
    class TestApp(App):
        def build(self):
            layout = BoxLayout(padding=dp(50))
            btn = FlatButton(text="Ouvrir Popup", size_hint=(None, None), size=(dp(200), dp(50)))
            btn.bind(on_release=self.launch_popup)
            layout.add_widget(btn)
            return layout

        def launch_popup(self, instance):
            valeur_initiale = ureg.Quantity(2, 'Hz')
            popup = UnitNumberPopup()
            popup.open(
                title='fréquence',
                current_value=valeur_initiale,
                callback=self.popup_callback
            )

        def popup_callback(self, new_value):
            print(f"Callback -> {new_value:~^P}")

    TestApp().run()
