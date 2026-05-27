from kivy.app import App
from kivy.lang import Builder
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.button import Button
from datetime import timedelta

# Définition de l'interface graphique du widget
KV = '''
<CircularTimer>:
    canvas.before:
        # Cercle d'arrière-plan (gris)
        Color:
            rgba: 0.2, 0.2, 0.2, 1
        Line:
            circle: (self.width / 2, self.height / 2, min(self.width, self.height) / 2 - dp(15), 0, 360)
            width: dp(8)
            
        # Cercle de progression dynamique (bleu)
        Color:
            rgba: (0.1, 0.6, 0.8, 1) if root.angle > 0 else (0, 0, 0, 0)  # Affiche uniquement si l'angle est supérieur à 0
        Line:
            circle: (self.width / 2, self.height / 2, min(self.width, self.height) / 2 - dp(15), 0, root.angle)
            width: dp(8)
            cap: 'none'

    Label:
        text: root.time_text
        font_size: self.height * 0.2
        font_name: 'Roboto'
        bold: True
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
'''

class CircularTimer(RelativeLayout):
    angle = NumericProperty(360)
    time_text = StringProperty("00:00")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_seconds = 0.0
        self.seconds_left = 0.0
        self._clock_event = None

    def start(self, duration: timedelta = None):
        """
        Démarre le chronomètre avec la durée spécifiée. 
        Si aucune durée n'est fournie, reprend le chronomètre là où il s'est arrêté.
        """
        if duration is not None:
            self.total_seconds = duration.total_seconds()
            self.seconds_left = self.total_seconds

        if self.seconds_left > 0 and not self._clock_event:
            self._update_ui()
            # Mise à jour à intervalle régulier (20 FPS pour la fluidité visuelle)
            self._clock_event = Clock.schedule_interval(self._tick, 0.05)

    def pause(self):
        """Suspend le compte à rebours sans réinitialiser le temps restant."""
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None

    def stop(self):
        """Arrête le chronomètre et réinitialise les valeurs à zéro."""
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None
        self.seconds_left = 0.0
        self.total_seconds = 0.0
        self._update_ui()

    def _tick(self, dt):
        self.seconds_left -= dt
        if self.seconds_left <= 0:
            self.seconds_left = 0.0
            self.stop()
            return
        self._update_ui()

    def _update_ui(self):
        # Formatage du texte MM:SS
        mins, secs = divmod(int(self.seconds_left), 60)
        self.time_text = f"{mins:02d}:{secs:02d}"

        # Calcul de l'arc de cercle (proportionnel au temps restant)
        if self.total_seconds > 0:
            self.angle = (self.seconds_left / self.total_seconds) * 360
        else:
            self.angle = 0


class TestApp(App):
    def build(self):
        Builder.load_string(KV)
        root = BoxLayout(orientation='vertical', padding=20, spacing=20)

        # Instance du widget personnalisé
        self.timer = CircularTimer(size_hint=(1, 0.7))
        root.add_widget(self.timer)

        # Boutons de contrôle
        controls = BoxLayout(size_hint=(1, 0.3), spacing=10)
        btn_start = Button(text="Start (1 min)", on_press=lambda x: self.timer.start(timedelta(minutes=1)))
        btn_resume = Button(text="Resume", on_press=lambda x: self.timer.start())
        btn_pause = Button(text="Pause", on_press=lambda x: self.timer.pause())
        btn_stop = Button(text="Stop", on_press=lambda x: self.timer.stop())
        
        controls.add_widget(btn_start)
        controls.add_widget(btn_resume)
        controls.add_widget(btn_pause)
        controls.add_widget(btn_stop)
        
        root.add_widget(controls)
        return root

if __name__ == '__main__':
    TestApp().run()