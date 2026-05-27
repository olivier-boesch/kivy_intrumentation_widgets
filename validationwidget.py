from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.lang import Builder
from kivy.animation import Animation
from kivy.metrics import dp

kv = '''
<ValidationWidget>:
    orientation: 'horizontal'
    padding: dp(10)
    spacing: dp(10)

    SwipeArea:
        id: swipe_area
        size_hint_x: None
        width: self.parent.width -self.parent.height - dp(5)
        text: root.slider_text if self.progress < 0.9 else root.slider_text_armed
        on_progress: root.check_progress(self.progress)

    ActionCircle:
        id: action_circle
        size_hint_x: None
        width: self.parent.height
        text: root.button_text
        is_active: root.is_validated
        on_button_pressed: root.dispatch('on_press')

<SwipeArea>:
    thumb_width: '120dp'
    canvas.before:
        Color:
            rgba: (0.5, 0.5, 0.5, 1-self.progress/0.9) if self.progress < 0.90 else (0.0, 0.0, 0.0, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]
    canvas:
        Color:
            rgba: (0.2, 0.4, 0.6, 1) if self.progress < 0.90 else (0.0, 0.0, 0.0, 0)
        RoundedRectangle:
            pos: self.x + self.progress * (self.width - self.thumb_width), self.y
            size: self.thumb_width, self.height
            radius: [dp(8)]

    Label:
        text: root.text
        pos: root.x + root.progress * (root.width - root.thumb_width), root.y
        size: root.thumb_width, root.height
        color: 1, 1, 1, 1
        bold: True
        font_size: root.height * 0.3

<ActionCircle>:
    canvas.before:
        Color:
            rgba: (0.2, 0.4, 0.6, root.signal_alpha) if self.is_active else (0,0,0,0)
        Line:
            circle: (self.center_x, self.center_y, root.signal_radius)
            width: dp(2)
        
        Color:
            rgba: (0.2, 0.4, 0.6, 1) if self.is_active else (0.8, 0.8, 0.8, 0.1)
        Ellipse:
            pos: self.center_x - min(self.width, self.height)*0.5, self.center_y - min(self.width, self.height) * 0.5
            size: min(self.width, self.height), min(self.width, self.height)
        

    Label:
        text: root.text
        center: root.center
        color: (1, 1, 1, 1) if root.is_active else (1, 1, 1, 0.2)
        bold: True
        font_size: root.height * 0.3
'''

Builder.load_string(kv)


class SwipeArea(Widget):
    progress = NumericProperty(0)
    text = StringProperty("")
    thumb_width = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_dragging = False
        self._touch_offset = 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            thumb_x = self.x + self.progress * (self.width - self.thumb_width)
            if thumb_x <= touch.x <= thumb_x + self.thumb_width:
                self._is_dragging = True
                self._touch_offset = touch.x - thumb_x
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._is_dragging:
            new_x = touch.x - self._touch_offset
            max_x = self.width - self.thumb_width
            if max_x > 0:
                raw_progress = (new_x - self.x) / max_x
                self.progress = max(0.0, min(1.0, raw_progress))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._is_dragging:
            self._is_dragging = False
            if self.progress < 0.9:
                Animation(progress=0, t='out_bounce', duration=0.7).start(self)
            else:
                Animation(progress=1, t='linear', duration=0.1).start(self)
            return True
        return super().on_touch_up(touch)


class ActionCircle(Widget):
    text = StringProperty("")
    is_active = BooleanProperty(False)
    signal_radius = NumericProperty(0)
    signal_alpha = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_button_pressed')

    def on_button_pressed(self):
        pass

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.is_active:
            self.dispatch('on_button_pressed')
            self._trigger_signal_animation()
            return True
        return super().on_touch_down(touch)

    def _trigger_signal_animation(self):
        start_radius = min(self.width, self.height) * 0.4
        end_radius = start_radius * 2.5
        
        self.signal_radius = start_radius
        self.signal_alpha = 1.0
        
        anim = Animation(signal_radius=end_radius, signal_alpha=0.0, t='out_quad', duration=0.6)
        anim.start(self)


class ValidationWidget(BoxLayout):
    slider_text = StringProperty("")
    slider_text_armed = StringProperty("")
    button_text = StringProperty("")
    is_validated = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_press')

    def on_press(self):
        pass

    def check_progress(self, value):
        self.is_validated = (value >= 0.99)



if __name__ == '__main__':
    from kivy.app import App


    kv_string = '''
BoxLayout:
    padding: dp(50)
    spacing: dp(10)
    orientation: 'vertical'
    Label:
        text: "Glissez le curseur pour valider la fin du monde, puis appuyez sur le bouton."
        height: dp(50)
        font_size: dp(18)
    ValidationWidget:
        slider_text: "Arm >"
        slider_text_armed: "< Cancel"
        button_text: "OK"
        size_hint: (1, None)
        height: dp(100)
        on_press: app.ma_fonction_callback(self)
    '''

    class TestApp(App):
        def build(self):
            return Builder.load_string(kv_string)

        def ma_fonction_callback(self, instance):
            print("Signal reçu : Le bouton droit a été activé puis pressé.")
    TestApp().run()
