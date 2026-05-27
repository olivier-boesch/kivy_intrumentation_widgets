import ast
if not hasattr(ast, 'Str'):
    ast.Str = ast.Constant
    ast.Num = ast.Constant
    ast.Bytes = ast.Constant
    ast.NameConstant = ast.Constant
    ast.Constant.s = property(lambda self: self.value if isinstance(self.value, (str, bytes)) else '')
    ast.Constant.n = property(lambda self: self.value if isinstance(self.value, (int, float, complex)) else 0)

import math
import time
import pint

from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, NumericProperty, StringProperty, ListProperty, BooleanProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Line, PushMatrix, PopMatrix, Rotate, InstructionGroup
from kivy.uix.accordion import Animation



__all__ = ['RotaryEncoderWidget', 'BorderWrapper']

ureg = pint.UnitRegistry()

_TICK_ANGLES_RAD = [math.radians(i * 22.5) for i in range(16)]

Builder.load_string("""
<RotaryEncoderWidget>:
    graphics_color: [0.2, 0.6, 0.8, 1]
    text_color: [1, 1, 1, 1]

    BoxLayout:
        orientation: 'vertical'
        size_hint: None, None
        size: root.width * 0.7, root.height * 0.7
        center_y: root.height / 2 + root.y
        center_x: root.width / 2 + root.x
        spacing: dp(2)

        Label:
            text: root.quantity_name
            color: root.text_color
            font_size: min(root.height, root.width) * 0.07
            halign: 'center'
            valign: 'middle'
            text_size: self.size
            size_hint_y: 0.3

        Label:
            text: root.value_text
            color: root.text_color
            font_size: min(root.height, root.width) * 0.15
            bold: True
            halign: 'center'
            valign: 'middle'
            text_size: self.size
            size_hint_y: 0.3

        Label:
            text: root.unit_text
            color: root.text_color
            font_size: min(root.height, root.width) * 0.07
            halign: 'center'
            valign: 'middle'
            text_size: self.size
            size_hint_y: 0.3

    Label:
        text: 'fin' if root.fine_mode else ''
        color: 1, 1, 1, 0.3
        font_size: min(root.height, root.width) * 0.05
        size: min(root.height, root.width) * 0.2, min(root.height, root.width) * 0.1
        center_x: root.center_x + min(root.height, root.width) * 0.25
        center_y: root.center_y
        halign: 'center'
        valign: 'middle'
        text_size: self.size
""")


class RotaryEncoderWidget(Widget):
    """Encodeur rotatif interactif avec réglage fin.

    Propriétés KV :
        min_value      (float) — valeur minimale
        max_value      (float) — valeur maximale
        unit           (str)   — unité Pint (ex. 'W', 'A', 'm/s')
        quantity_name  (str)   — libellé affiché au-dessus de la valeur
        step_min       (float) — pas en mode fin (molette / zone centrale)
        step_max       (float) — pas maximum en mode normal (haute vélocité)
        fine_deg_per_step (float) — degrés de rotation par step_min en mode fin
        granularity    (int)   — nombre de décimales affichées
        graphics_color (list)  — couleur RGBA du widget
        text_color     (list)  — couleur RGBA du texte

    Interactions :
        double-tap  — bascule en mode édition (clignotement orange)
        glisser     — modifie la valeur (vélocité angulaire → sensibilité)
        zone centrale (50 % du rayon) — mode fin : 1 step_min par demi-tour
        molette     — ±step_min en mode édition
        appui long (1 s) — annule les modifications
    """

    min_value  = NumericProperty(0)
    max_value  = NumericProperty(100)
    value      = ObjectProperty(None)
    unit       = ObjectProperty(None)

    step_min          = NumericProperty(0.01)
    step_max          = NumericProperty(0.2)
    fine_deg_per_step = NumericProperty(180.0)

    rotation_angle = NumericProperty(0)
    state          = StringProperty('idle')

    value_text    = StringProperty("")
    unit_text     = StringProperty("")
    quantity_name = StringProperty("")
    granularity   = NumericProperty(2)

    graphics_color = ListProperty([0.2, 0.6, 0.8, 1])
    text_color     = ListProperty([1, 1, 1, 1])
    fine_mode      = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_angle  = None
        self._last_time   = None
        self._updating    = False
        self._backup_value          = None
        self._backup_rotation_angle = 0
        self._long_press_event = None
        self._blink_event      = None
        self._fine_acc    = 0.0
        self._in_fine_mode = False
        self._unit    = None
        self._r_outer = 0.0
        self._r_fine  = 0.0

        with self.canvas:
            self._color_instr = Color(*self.graphics_color)
            PushMatrix()
            self._rotate_instr = Rotate(angle=0, axis=(0, 0, 1), origin=(0, 0))
            self._geom_group = InstructionGroup()
            PopMatrix()
            self._boundary_color = Color(*self.graphics_color)
            self._boundary_group = InstructionGroup()

        self.bind(
            value=self.update_text,
            unit=self._on_unit_change,
            pos=self._rebuild_geometry,
            size=self._rebuild_geometry,
            rotation_angle=self._update_rotation,
            graphics_color=self._update_color,
        )
        Clock.schedule_once(self._deferred_init, 0)

    # ------------------------------------------------------------------
    # Initialisation et mise à jour de l'unité
    # ------------------------------------------------------------------

    def _deferred_init(self, _):
        self._unit = ureg(self.unit)
        self.value = self.min_value * self._unit
        self.update_text()
        self._rebuild_geometry()

    def _on_unit_change(self, *_):
        if self.unit:
            self._unit = ureg(self.unit)
        self.update_text()

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------

    def _update_color(self, *_):
        self._color_instr.rgba = self.graphics_color
        self._boundary_color.rgba = [0.2, 0.6, 0.8, 0.2]

    def _rebuild_geometry(self, *_):
        cx, cy = self.center_x, self.center_y
        self._r_outer = min(self.width, self.height) * 0.4
        if self._r_outer <= 0:
            return
        self._r_fine  = self._r_outer * 0.5
        r_inner = self._r_outer - dp(15)
        tick_w  = dp(4)

        self._rotate_instr.origin = (cx, cy)
        self._geom_group.clear()
        self._geom_group.add(Line(circle=(cx, cy, self._r_outer), width=tick_w))
        for a in _TICK_ANGLES_RAD:
            ca, sa = math.cos(a), math.sin(a)
            self._geom_group.add(Line(
                points=[cx + self._r_outer * ca, cy + self._r_outer * sa,
                        cx + r_inner * ca,        cy + r_inner * sa],
                width=tick_w,
            ))

        self._boundary_color.rgba = [0.2, 0.6, 0.8, 0.2]
        self._boundary_group.clear()
        self._boundary_group.add(Line(circle=(cx, cy, self._r_fine), width=dp(1.5)))

    def _update_rotation(self, *_):
        self._rotate_instr.angle = self.rotation_angle

    # ------------------------------------------------------------------
    # Texte
    # ------------------------------------------------------------------

    def update_text(self, *_):
        if self._updating or self.value is None:
            return
        self.value_text = f"{self.value.magnitude:.{self.granularity}f}"
        self.unit_text  = f"{self.value.units:~^P}"

    def _blink_text(self, *_):
        self.text_color = [1, 1, 1, 0.3] if self.text_color == [1, 0.5, 0, 0.3] else [1, 0.5, 0, 0.3]

    def start_blinking(self):
        if not self._blink_event:
            self._blink_event = Clock.schedule_interval(self._blink_text, 0.5)
            self.text_color = [1, 0.5, 0, 0.3]

    def stop_blinking(self):
        if self._blink_event:
            self._blink_event.cancel()
            self._blink_event = None
            self.text_color = [1, 1, 1, 1]

    # ------------------------------------------------------------------
    # Touch
    # ------------------------------------------------------------------

    def _trigger_cancel(self, touch):
        self._updating = True
        self.value = self._backup_value
        Animation(rotation_angle=self._backup_rotation_angle, t='linear', d=0.2).start(self)
        self._updating = False
        self.state = 'idle'
        self.text_color = [1, 1, 1, 1]
        self.update_text()
        self._fine_acc = 0.0
        self._in_fine_mode = False
        self.fine_mode = False
        self.stop_blinking()
        touch.ungrab(self)

    def touch_distance(self, touch):
        return math.hypot(touch.x - self.center_x, touch.y - self.center_y)

    def is_touch_inside(self, touch):
        return self.touch_distance(touch) < self._r_outer

    def on_touch_down(self, touch):
        if not self.is_touch_inside(touch):
            return super().on_touch_down(touch)

        if hasattr(touch, 'button') and touch.button in ('scrollup', 'scrolldown'):
            if self.state == 'editing':
                direction = 1 if touch.button == 'scrollup' else -1
                new_magnitude = round(
                    max(self.min_value, min(self.max_value, self.value.magnitude + direction * self.step_min)),
                    self.granularity,
                )
                self.value = new_magnitude * self._unit
                self.update_text()
            return True

        if touch.is_double_tap:
            if self._long_press_event:
                self._long_press_event.cancel()
                self._long_press_event = None
            if self.state == 'idle':
                self.state = 'editing'
                self._backup_value = self.value
                self._backup_rotation_angle = self.rotation_angle
                self.text_color = [1, 0.5, 0, 1]
                self.start_blinking()
            elif self.state == 'editing':
                self.state = 'idle'
                self.text_color = [1, 1, 1, 1]
                self.stop_blinking()
            return True

        if self.state == 'editing':
            touch.grab(self)
            touch.ud['start_pos'] = touch.pos
            self._in_fine_mode = self.touch_distance(touch) < self._r_fine
            self.fine_mode = self._in_fine_mode
            self._last_angle = math.degrees(math.atan2(touch.y - self.center_y, touch.x - self.center_x))
            self._last_time  = time.time()
            self._long_press_event = Clock.schedule_once(lambda dt: self._trigger_cancel(touch), 1.0)
            return True

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        start_pos = touch.ud.get('start_pos', touch.pos)
        if math.hypot(touch.x - start_pos[0], touch.y - start_pos[1]) > 5:
            if self._long_press_event:
                self._long_press_event.cancel()
                self._long_press_event = None

        current_angle = math.degrees(math.atan2(touch.y - self.center_y, touch.x - self.center_x))
        current_time  = time.time()
        delta_angle   = current_angle - self._last_angle
        delta_time    = current_time  - self._last_time

        if delta_angle >  180: delta_angle -= 360
        elif delta_angle < -180: delta_angle += 360

        if abs(delta_angle) > 0.1 and delta_time > 0:
            self.rotation_angle += delta_angle

            if self._in_fine_mode:
                self._fine_acc -= delta_angle
                steps = int(self._fine_acc / self.fine_deg_per_step)
                self._fine_acc -= steps * self.fine_deg_per_step
                change = steps * self.step_min
            else:
                angular_velocity = abs(delta_angle) / delta_time
                sensitivity = self.step_min + (self.step_max - self.step_min) * min(angular_velocity / 1000.0, 1.0)
                change = -delta_angle * sensitivity

            if change:
                self._updating = True
                new_magnitude = round(
                    max(self.min_value, min(self.max_value, self.value.magnitude + change)),
                    self.granularity,
                )
                self.value = new_magnitude * self._unit
                self._updating = False
                self.update_text()

        self._last_angle = current_angle
        self._last_time  = current_time
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        if self._long_press_event:
            self._long_press_event.cancel()
            self._long_press_event = None
        self._in_fine_mode = False
        self.fine_mode = False
        touch.ungrab(self)
        return True


if __name__ == '__main__':
    from kivy.app import App
    from borderwrapper import BorderWrapper

    kv_app = """
BoxLayout:
    orientation: 'vertical'
    padding: dp(20)
    spacing: dp(10)

    Label:
        text: "Encodeur Interactif"
        font_size: dp(22)
        halign: 'center'
        size_hint_y: 0.15

    BoxLayout:
        BorderWrapper:
            title: "Puissance"
            padding: dp(20)
            radius: dp(20)
            RotaryEncoderWidget:
                min_value: 0
                max_value: 100
                step_min: 0.01
                step_max: 0.3
                unit: 'W'
                quantity_name: "Puissance"
            RotaryEncoderWidget:
                min_value: 0
                max_value: 100
                step_min: 0.01
                step_max: 0.2
                unit: 'A'
                quantity_name: "Courant"
"""

    class RotaryEncoderApp(App):
        def build(self):
            return Builder.load_string(kv_app)

    RotaryEncoderApp().run()
