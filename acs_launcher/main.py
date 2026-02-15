#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from acs_launcher.window import MainWindow


class ACSLauncherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.github.richard.acslauncher")

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = MainWindow(application=self)
        win.present()


def main():
    app = ACSLauncherApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
