import ast
if not hasattr(ast, 'Str'):
    ast.Str = ast.Constant
    ast.Num = ast.Constant
    ast.Bytes = ast.Constant
    ast.NameConstant = ast.Constant
    ast.Constant.s = property(lambda self: self.value if isinstance(self.value, (str, bytes)) else '')
    ast.Constant.n = property(lambda self: self.value if isinstance(self.value, (int, float, complex)) else 0)

__all__ = ['RollingChart']

import collections

import pint
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import NumericProperty, ListProperty
from kivy.graphics import Color, Line, Rectangle
from kivy.core.text import Label as CoreLabel
from kivy.metrics import dp

ureg = pint.UnitRegistry()

_N_Y_TICKS = 5
_N_X_TICKS = 3


class RollingChart(RelativeLayout):
    """Graphique en courbe avec fenêtre glissante et auto-échelle Y.

    Propriétés :
        line_color — couleur RGBA de la courbe
        x_window   — nombre de points affichés simultanément

    Usage :
        chart = RollingChart(
            y_unit   = 0 * ureg.watt,
            x_step   = 1 * ureg.second,   # optionnel
            x_window = 60,
        )
        chart.push(12.4 * ureg.watt)
    """

    line_color = ListProperty([0.1, 0.6, 0.8, 1])
    x_window   = NumericProperty(60)

    def __init__(self, y_unit, x_window=60, x_step=None, **kwargs):
        super().__init__(**kwargs)

        self._x_window    = x_window
        self._y_ref_unit  = y_unit.units
        self._y_unit_str  = f"{y_unit.units:~^P}"
        self._x_step_mag  = x_step.magnitude if x_step else 1
        self._x_unit_str  = f"{x_step.units:~^P}" if x_step else ""

        self._history  = collections.deque(maxlen=x_window)
        self._data_min = 0.0
        self._data_max = 1.0
        self._y_min    = -0.05
        self._y_max    =  1.05

        # Géométrie cache (coords locales RelativeLayout)
        self._x0     = 0.0
        self._y0     = 0.0
        self._plot_w = 0.0
        self._plot_h = 0.0
        self._dx     = 1.0
        self._dy     = 1.0

        # Constantes dp — calculées une fois
        self._ml      = dp(56)
        self._mb      = dp(26)
        self._mt      = dp(10)
        self._mr      = dp(8)
        self._font_sz      = dp(10)
        self._font_sz_unit = dp(13)
        self._dp4          = dp(4)
        self._dp5          = dp(5)
        self._w            = 0.0
        self._h            = 0.0

        # Buffer pré-alloué pour les points de la courbe
        self._pts = [0.0] * (2 * x_window)

        with self.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            self._bg = Rectangle()
            Color(0.22, 0.22, 0.22, 1)
            # Une Line par rangée — évite le zigzag d'une polyline unique
            self._grid_lines = []
            for _ in range(_N_Y_TICKS):
                self._grid_lines.append(Line())
            Color(0.50, 0.50, 0.50, 1)
            self._axes = Line()

        with self.canvas:
            self._lc   = Color(*self.line_color)
            self._data = Line(width=dp(1.5), cap='none')

        with self.canvas.after:
            # Color(1,1,1,1) = multiplicateur identité : la couleur est portée
            # par le CoreLabel uniquement (sinon double atténuation)
            self._ytick_rects = []
            for _ in range(_N_Y_TICKS):
                Color(1, 1, 1, 1)
                self._ytick_rects.append(Rectangle(size=(0, 0)))

            self._xtick_rects = []
            for _ in range(_N_X_TICKS):
                Color(1, 1, 1, 1)
                self._xtick_rects.append(Rectangle(size=(0, 0)))

            Color(1, 1, 1, 1)
            self._yunit_rect = Rectangle(size=(0, 0))
            Color(1, 1, 1, 1)
            self._xunit_rect = Rectangle(size=(0, 0))

        self.bind(
            pos=self._rebuild_geometry,
            size=self._rebuild_geometry,
            line_color=lambda *_: setattr(self._lc, 'rgba', self.line_color),
        )

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def push(self, value):
        """Ajoute une mesure (pint.Quantity) et met à jour l'affichage."""
        mag = value.to(self._y_ref_unit).magnitude
        self._history.append(mag)

        data_min = min(self._history)
        data_max = max(self._history)
        rescaled = False
        if data_min != self._data_min or data_max != self._data_max:
            self._data_min = data_min
            self._data_max = data_max
            pad = max((data_max - data_min) * 0.05, 0.5)
            self._y_min = data_min - pad
            self._y_max = data_max + pad
            rng = self._y_max - self._y_min
            self._dy = self._plot_h / rng if rng > 0 else 1.0
            rescaled = True

        self._update_data_line()
        if rescaled:
            self._rebuild_y_ticks()

    def clear(self):
        self._history.clear()
        self._data.points = []

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------

    def _rebuild_geometry(self, *_):
        w, h = self.width, self.height
        if w <= 0 or h <= 0:
            return

        self._x0     = self._ml
        self._y0     = self._mb
        x1           = w - self._mr
        y1           = h - self._mt
        self._plot_w = x1 - self._x0
        self._plot_h = y1 - self._y0

        self._dx = self._plot_w / max(self._x_window - 1, 1)
        rng      = self._y_max - self._y_min
        self._dy = self._plot_h / rng if rng > 0 else 1.0

        self._w = w
        self._h = h

        self._bg.pos  = (0, 0)
        self._bg.size = (w, h)

        for j, line in enumerate(self._grid_lines):
            gy = self._y0 + j * self._plot_h / (_N_Y_TICKS - 1)
            line.points = [self._x0, gy, x1, gy]

        self._axes.points = [self._x0, y1, self._x0, self._y0, x1, self._y0]

        self._rebuild_y_ticks()
        self._rebuild_x_ticks()
        self._rebuild_unit_labels()
        self._update_data_line()

    def _update_data_line(self):
        """Hot path : boucle minimale, pas d'allocation hors du slice final."""
        n = len(self._history)
        if n < 1 or self._plot_w <= 0:
            return

        pts   = self._pts
        x0    = self._x0
        y0    = self._y0
        dx    = self._dx
        dy    = self._dy
        y_min = self._y_min

        for i, v in enumerate(self._history):
            pts[2 * i]     = x0 + i * dx
            pts[2 * i + 1] = y0 + (v - y_min) * dy

        self._data.points = pts[:2 * n]

    def _rebuild_y_ticks(self):
        x0    = self._x0
        y0    = self._y0
        ph    = self._plot_h
        y_min = self._y_min
        y_rng = self._y_max - self._y_min
        fs    = self._font_sz
        d4    = self._dp4

        for j, rect in enumerate(self._ytick_rects):
            frac = j / (_N_Y_TICKS - 1)
            val  = y_min + frac * y_rng
            ty   = y0 + frac * ph
            lbl  = CoreLabel(text=f"{val:.2g}", font_size=fs,
                             color=[0.70, 0.70, 0.70, 1])
            lbl.refresh()
            tx           = lbl.texture
            rect.texture = tx
            rect.size    = tx.size
            rect.pos     = (x0 - tx.width - d4, ty - tx.height / 2)

    def _rebuild_x_ticks(self):
        x0 = self._x0
        pw = self._plot_w
        n  = self._x_window
        fs = self._font_sz
        d5 = self._dp5

        for k, rect in enumerate(self._xtick_rects):
            frac          = k / (_N_X_TICKS - 1)
            px            = x0 + frac * pw
            sample_offset = int(frac * (n - 1)) - (n - 1)   # -(n-1) … 0
            val           = sample_offset * self._x_step_mag
            text          = f"{val:.0f}" if self._x_unit_str else str(sample_offset)
            lbl  = CoreLabel(text=text, font_size=fs,
                             color=[0.60, 0.60, 0.60, 1])
            lbl.refresh()
            tx           = lbl.texture
            rect.texture = tx
            rect.size    = tx.size
            rect.pos     = (px - tx.width / 2, d5)

    def _rebuild_unit_labels(self):
        fs = self._font_sz_unit
        d4 = self._dp4
        d5 = self._dp5

        if self._y_unit_str:
            lbl = CoreLabel(text=self._y_unit_str, font_size=fs,
                            color=[0.65, 0.65, 0.65, 1])
            lbl.refresh()
            tx = lbl.texture
            self._yunit_rect.texture = tx
            self._yunit_rect.size    = tx.size
            self._yunit_rect.pos     = (d4, self._h - tx.height - d4)

        if self._x_unit_str:
            lbl = CoreLabel(text=self._x_unit_str, font_size=fs,
                            color=[0.65, 0.65, 0.65, 1])
            lbl.refresh()
            tx = lbl.texture
            self._xunit_rect.texture = tx
            self._xunit_rect.size    = tx.size
            self._xunit_rect.pos     = (self._w - tx.width - d4, d5)


if __name__ == '__main__':
    import random
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.clock import Clock

    class RollingChartApp(App):
        def build(self):
            root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

            self.chart = RollingChart(
                y_unit   = 0 * ureg.watt,
                x_step   = 1 * ureg.second,
                x_window = 60,
            )
            root.add_widget(self.chart)

            btn = Button(
                text='Injecter mesure aléatoire',
                size_hint_y=None, height=dp(44),
                on_press=lambda _: self.chart.push(random.uniform(0, 100) * ureg.watt),
            )
            root.add_widget(btn)
            return root

        def on_start(self):
            self._val = 50.0
            def tick(dt):
                self._val = max(0, min(100, self._val + random.uniform(-3, 3)))
                self.chart.push(self._val * ureg.watt)
            Clock.schedule_interval(tick, 1 / 10)

    RollingChartApp().run()
