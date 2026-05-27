import ast
if not hasattr(ast, 'Str'):
    ast.Str = ast.Constant
    ast.Num = ast.Constant
    ast.Bytes = ast.Constant
    ast.NameConstant = ast.Constant
    ast.Constant.s = property(lambda self: self.value if isinstance(self.value, (str, bytes)) else '')
    ast.Constant.n = property(lambda self: self.value if isinstance(self.value, (int, float, complex)) else 0)

__all__ = ['FlatButton', 'FlatToggleButton']

from kivy.uix.behaviors import ButtonBehavior, ToggleButtonBehavior
from kivy.uix.label import Label
from kivy.properties import ListProperty, NumericProperty
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp


class _FlatBase(Label):
    button_color = ListProperty([0.2, 0.6, 0.8, 1])
    radius       = NumericProperty(8)
    border_width = NumericProperty(1.5)

    def __init__(self, **kwargs):
        kwargs.setdefault('color',  [1, 1, 1, 1])
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        super().__init__(**kwargs)
        bc = self.button_color
        with self.canvas.before:
            self._fill_color         = Color(bc[0], bc[1], bc[2], 0.15)
            self._fill_rect          = RoundedRectangle(pos=self.pos, size=self.size)
            self._border_color_instr = Color(bc[0], bc[1], bc[2], 1.0)
            self._border_line        = Line(width=dp(self.border_width))
        self._dp_r = dp(self.radius)
        self.bind(
            pos=self._on_pos,
            size=self._on_size,
            state=self._on_state,
            button_color=self._on_button_color,
            radius=self._on_radius,
        )

    def _on_pos(self, *_):
        self._fill_rect.pos = self.pos
        self._border_line.rounded_rectangle = (*self.pos, *self.size, self._dp_r)

    def _on_size(self, *_):
        self.text_size = self.size
        self._fill_rect.size   = self.size
        self._fill_rect.radius = [self._dp_r]
        self._border_line.rounded_rectangle = (*self.pos, *self.size, self._dp_r)

    def _on_radius(self, *_):
        self._dp_r = dp(self.radius)
        self._fill_rect.radius = [self._dp_r]
        self._border_line.rounded_rectangle = (*self.pos, *self.size, self._dp_r)

    def _on_state(self, *_):
        self._fill_color.a = 1.0 if self.state == 'down' else 0.15

    def _on_button_color(self, *_):
        bc = self.button_color
        self._fill_color.rgb         = bc[:3]
        self._border_color_instr.rgb = bc[:3]


class FlatButton(ButtonBehavior, _FlatBase):
    pass


class FlatToggleButton(ToggleButtonBehavior, _FlatBase):
    pass


if __name__ == '__main__':
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout

    class FlatButtonApp(App):
        def build(self):
            root = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(20))

            row1 = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(15))
            row1.add_widget(FlatButton(text="Valider"))
            row1.add_widget(FlatButton(text="Annuler"))
            row1.add_widget(FlatButton(text="Paramètres", button_color=[0.5, 0.5, 0.5, 1]))
            root.add_widget(row1)

            row2 = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(15))
            row2.add_widget(FlatToggleButton(text="Option A", group="opts"))
            row2.add_widget(FlatToggleButton(text="Option B", group="opts"))
            row2.add_widget(FlatToggleButton(text="Option C", group="opts"))
            root.add_widget(row2)

            return root

    FlatButtonApp().run()
