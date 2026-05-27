import ast
if not hasattr(ast, 'Str'):
    ast.Str = ast.Constant
    ast.Num = ast.Constant
    ast.Bytes = ast.Constant
    ast.NameConstant = ast.Constant
    ast.Constant.s = property(lambda self: self.value if isinstance(self.value, (str, bytes)) else '')
    ast.Constant.n = property(lambda self: self.value if isinstance(self.value, (int, float, complex)) else 0)

import collections
import math

import pint
from kivy.lang import Builder
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.graphics import Color, Line, Triangle

__all__ = ['CircularGauge']

ureg = pint.UnitRegistry()

_HALF_PI        = math.pi / 2
_BASE_ANGLE_RAD = math.radians(4)   # demi-angle de la base du triangle, précalculé

Builder.load_string('''
<CircularGauge>:
    BoxLayout:
        orientation: 'vertical'
        size_hint: None, None
        size: self.minimum_size
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        spacing: dp(5)

        Label:
            text: root.value_text
            font_size: min(root.size) * 0.15
            bold: True
            color: 1, 1, 1, 1
            size_hint: 1, None
            height: self.texture_size[1]
            halign: 'center'

        Label:
            text: root.unit_text
            font_size: min(root.size) * 0.1
            color: 0.7, 0.7, 0.7, 1
            size_hint: 1, None
            height: self.texture_size[1]
            halign: 'center'

        Label:
            text: root.mean_text
            font_size: min(root.size) * 0.05
            color: 0.1, 0.6, 0.8, 1
            size_hint: 1, None
            height: self.texture_size[1] + dp(5)
            halign: 'center'

        Label:
            text: "window: " + str(root.window_size_n)
            font_size: min(root.size) * 0.05
            color: 0.1, 0.6, 0.8, 1
            size_hint: 1, None
            height: self.texture_size[1] + dp(5)
            halign: 'center'
''')


class CircularGauge(RelativeLayout):
    """Jauge circulaire animée avec indicateur de moyenne mobile.

    Propriétés :
        min_value     — borne inférieure (pint.Quantity)
        max_value     — borne supérieure (pint.Quantity)
        window_size_n — taille de la fenêtre de la moyenne mobile

    Usage :
        gauge = CircularGauge(min_value=0*ureg.watt, max_value=50*ureg.watt)
        gauge.set_value(25 * ureg.watt)
    """

    min_value          = ObjectProperty(None)
    max_value          = ObjectProperty(None)
    current_value      = ObjectProperty(None)
    display_value      = NumericProperty(0)
    display_mean_value = NumericProperty(0)
    mean_value         = ObjectProperty(None)
    window_size_n      = NumericProperty(5)

    value_text = StringProperty("0.00")
    unit_text  = StringProperty("")
    mean_text  = StringProperty("")

    _ARC_START = -150
    _ARC_SPAN  =  300

    def __init__(self, min_value, max_value, window_size_n=5, **kwargs):
        super().__init__(**kwargs)
        self.min_value     = min_value
        self.max_value     = max_value
        self.window_size_n = window_size_n

        # Constantes dp (la densité d'écran ne change pas à l'exécution)
        self._dp30 = dp(30)
        self._dp15 = dp(15)

        # Cache géométrique — mis à jour dans _rebuild_geometry (resize uniquement)
        self._cx          = 0.0
        self._cy          = 0.0
        self._radius      = 0.0
        self._r_inner     = 0.0
        self._cos_boff    = 1.0   # cos(base_offset)
        self._sin_boff    = 0.0   # sin(base_offset)

        # Cache de la plage — valide tant que min/max ne changent pas
        self._total_range = (max_value - min_value).magnitude
        self._min_mag     = min_value.magnitude

        self._history = collections.deque(maxlen=window_size_n)
        for _ in range(window_size_n):
            self._history.append(min_value)

        self.current_value      = min_value
        self.display_value      = min_value.magnitude
        self.mean_value         = min_value
        self.display_mean_value = min_value.magnitude

        # L'unité ne change jamais : calculée une seule fois
        self.unit_text  = f"{min_value.units:~^P}"
        self.value_text = f"{min_value.magnitude:.2f}"
        self.mean_text  = f"Mean: {min_value:~^P.2f}"

        # Instructions canvas créées une fois, mises à jour in-place ensuite
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            self._bg_arc = Line(width=dp(8), cap='none')
            Color(0.1, 0.6, 0.8, 1)
            self._fg_arc = Line(width=dp(8), cap='none')
        with self.canvas:
            Color(1, 1, 1, 1)
            self._triangle_instr = Triangle(points=[0, 0, 0, 0, 0, 0])

        self.bind(pos=self._rebuild_geometry, size=self._rebuild_geometry)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def set_value(self, value):
        if not isinstance(value, ureg.Quantity):
            value = float(value) * ureg.meter

        if value < self.min_value:
            value = self.min_value
        elif value > self.max_value:
            value = self.max_value

        self.current_value = value
        self._history.append(value)

        mean_mag       = sum(q.magnitude for q in self._history) / len(self._history)
        self.mean_value = mean_mag * self.min_value.units
        self.value_text = f"{value.magnitude:.2f}"
        self.mean_text  = f"Mean: {self.mean_value:~^P.2f}"

        Animation.cancel_all(self)
        Animation(display_mean_value=mean_mag,       t='linear',   duration=0.5).start(self)
        Animation(display_value=value.magnitude,     t='out_quad', duration=0.2).start(self)

    # ------------------------------------------------------------------
    # Callbacks animation → mise à jour canvas directe
    # ------------------------------------------------------------------

    def on_display_value(self, instance, value):
        self._update_display()

    def on_display_mean_value(self, instance, value):
        self._update_display()

    # ------------------------------------------------------------------
    # Géométrie
    # ------------------------------------------------------------------

    def _rebuild_geometry(self, *_):
        """Appelée uniquement au resize : recalcule le cache et redessine l'arc fixe."""
        w, h = self.width, self.height
        self._cx     = w / 2
        self._cy     = h / 2
        self._radius = min(w, h) / 2 - self._dp30
        if self._radius <= 0:
            return

        self._r_inner = self._radius - self._dp15

        # Précalcul trigonométrique de l'offset de la base du triangle
        base_offset    = _BASE_ANGLE_RAD * 150 / self._radius
        self._cos_boff = math.cos(base_offset)
        self._sin_boff = math.sin(base_offset)

        self._bg_arc.circle = (self._cx, self._cy, self._radius, -150, 150)
        self._update_display()

    def _update_display(self):
        """Hot path : appelée à chaque tick d'animation.
        N'utilise que des valeurs mises en cache — aucun recalcul de géométrie.
        """
        if self._radius <= 0 or self._total_range <= 0:
            return

        cx, cy    = self._cx, self._cy
        radius    = self._radius
        r_inner   = self._r_inner
        cb, sb    = self._cos_boff, self._sin_boff
        inv_range = 1.0 / self._total_range
        min_mag   = self._min_mag

        # Arc avant
        val_norm = (self.display_value - min_mag) * inv_range
        self._fg_arc.circle = (cx, cy, radius, -150, self._ARC_START + val_norm * self._ARC_SPAN)

        # Triangle de la moyenne : 2 appels trig via formules d'addition d'angles
        mean_norm = (self.display_mean_value - min_mag) * inv_range
        rad       = _HALF_PI - math.radians(self._ARC_START + mean_norm * self._ARC_SPAN)
        cos_r, sin_r = math.cos(rad), math.sin(rad)

        self._triangle_instr.points = [
            cx + radius  * cos_r,                     cy + radius  * sin_r,
            cx + r_inner * (cos_r*cb + sin_r*sb),     cy + r_inner * (sin_r*cb - cos_r*sb),
            cx + r_inner * (cos_r*cb - sin_r*sb),     cy + r_inner * (sin_r*cb + cos_r*sb),
        ]


if __name__ == '__main__':
    import random
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.clock import Clock

    class TestApp(App):
        def build(self):
            root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))

            self.gauge = CircularGauge(
                min_value=0 * ureg.watt, max_value=50 * ureg.watt, window_size_n=10
            )
            root.add_widget(self.gauge)

            controls = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
            controls.add_widget(Button(
                text="Injecter mesure aléatoire",
                on_press=lambda x: self.gauge.set_value(random.uniform(0, 50) * ureg.watt),
            ))
            root.add_widget(controls)
            return root

        def on_start(self):
            self.gauge.set_value(25 * ureg.watt)
            self._clock_event = Clock.schedule_interval(
                lambda dt: self.gauge.set_value(
                    self.gauge.current_value + random.uniform(-5, 5) * ureg.watt
                ),
                1,
            )

    TestApp().run()
