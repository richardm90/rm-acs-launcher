#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

from acs_launcher import __version__
from acs_launcher.window import MainWindow

ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rm-acs-launcher.png")


class ACSLauncherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.github.richard.acslauncher")

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = MainWindow(application=self)
            if os.path.exists(ICON_PATH):
                win.set_icon(GdkPixbuf.Pixbuf.new_from_file(ICON_PATH))
        win.present()


def main():
    app = ACSLauncherApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
