#!/usr/bin/env python
import argparse
import os
import runpy

from kivy.config import Config

Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'show_cursor', '0')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from PIL import Image

Window.clearcolor = (0, 0, 0, 1)


def _flatten_black_background(path):
    try:
        img = Image.open(path)
    except Exception:
        return
    if img.mode in ('RGBA', 'LA') or img.info.get('transparency'):
        bg = Image.new('RGBA', img.size, (0, 0, 0, 255))
        if img.mode == 'RGBA':
            bg.paste(img, mask=img.split()[3])
        else:
            bg.paste(img)
        bg.convert('RGB').save(path)
    else:
        img.save(path)


def main():
    parser = argparse.ArgumentParser(description='Generate Kivy screenshots for demo apps.')
    parser.add_argument('path', help='Path to the demo script file (.py)')
    parser.add_argument('output', help='Output image file path')
    args = parser.parse_args()

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    orig_run = App.run

    def patched_run(self, *run_args, **run_kwargs):
        def take_screenshot(*_):
            if getattr(self, 'root', None) is not None and self.root.width > 0 and self.root.height > 0:
                try:
                    self.root.export_to_png(output_path)
                    _flatten_black_background(output_path)
                except Exception:
                    Window.screenshot(name=output_path)
                Clock.schedule_once(lambda dt: self.stop(), 0.2)
            else:
                # retry until the root widget is rendered
                Clock.schedule_once(take_screenshot, 0.2)

        def start_capture(*_):
            Clock.schedule_once(take_screenshot, 1.2)

        self.bind(on_start=start_capture)
        return orig_run(self, *run_args, **run_kwargs)

    App.run = patched_run
    runpy.run_path(args.path, run_name='__main__')


if __name__ == '__main__':
    main()
