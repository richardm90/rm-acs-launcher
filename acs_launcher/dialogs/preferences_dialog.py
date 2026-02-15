import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class PreferencesDialog(Gtk.Dialog):
    """Configure ACS jar path, Java path, and Java options."""

    def __init__(self, parent, cfg):
        super().__init__(
            title="Preferences",
            transient_for=parent,
            modal=True,
        )
        self.cfg = cfg
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(15)
        box.set_margin_bottom(10)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        box.pack_start(grid, False, False, 0)

        # ACS executable path
        grid.attach(
            Gtk.Label(label="ACS executable:", halign=Gtk.Align.END), 0, 0, 1, 1
        )
        exe_box = Gtk.Box(spacing=6)
        self.exe_entry = Gtk.Entry()
        self.exe_entry.set_text(cfg.get("acs_exe_path", ""))
        self.exe_entry.set_hexpand(True)
        exe_box.pack_start(self.exe_entry, True, True, 0)

        exe_browse = Gtk.Button(label="Browse")
        exe_browse.connect("clicked", self._on_browse_exe)
        exe_box.pack_start(exe_browse, False, False, 0)
        grid.attach(exe_box, 1, 0, 1, 1)

        # ACS jar path
        grid.attach(
            Gtk.Label(label="ACS jar path:", halign=Gtk.Align.END), 0, 1, 1, 1
        )
        jar_box = Gtk.Box(spacing=6)
        self.jar_entry = Gtk.Entry()
        self.jar_entry.set_text(cfg.get("acs_jar_path", ""))
        self.jar_entry.set_hexpand(True)
        jar_box.pack_start(self.jar_entry, True, True, 0)

        jar_browse = Gtk.Button(label="Browse")
        jar_browse.connect("clicked", self._on_browse_jar)
        jar_box.pack_start(jar_browse, False, False, 0)
        grid.attach(jar_box, 1, 1, 1, 1)

        # Java path
        grid.attach(
            Gtk.Label(label="Java path:", halign=Gtk.Align.END), 0, 2, 1, 1
        )
        java_box = Gtk.Box(spacing=6)
        self.java_entry = Gtk.Entry()
        self.java_entry.set_text(cfg.get("java_path", ""))
        self.java_entry.set_hexpand(True)
        java_box.pack_start(self.java_entry, True, True, 0)

        java_browse = Gtk.Button(label="Browse")
        java_browse.connect("clicked", self._on_browse_java)
        java_box.pack_start(java_browse, False, False, 0)
        grid.attach(java_box, 1, 2, 1, 1)

        # Java options
        grid.attach(
            Gtk.Label(label="Java options:", halign=Gtk.Align.END), 0, 3, 1, 1
        )
        self.opts_entry = Gtk.Entry()
        self.opts_entry.set_text(cfg.get("java_opts", ""))
        self.opts_entry.set_hexpand(True)
        grid.attach(self.opts_entry, 1, 3, 1, 1)

        # Logon command
        grid.attach(
            Gtk.Label(label="Logon command:", halign=Gtk.Align.END), 0, 4, 1, 1
        )
        self.logon_entry = Gtk.Entry()
        self.logon_entry.set_text(cfg.get("logon_cmd", ""))
        self.logon_entry.set_hexpand(True)
        grid.attach(self.logon_entry, 1, 4, 1, 1)

        self.show_all()

    def _on_browse_exe(self, button):
        path = self._file_chooser("Select ACS executable")
        if path:
            self.exe_entry.set_text(path)

    def _on_browse_jar(self, button):
        path = self._file_chooser("Select ACS jar file", "*.jar")
        if path:
            self.jar_entry.set_text(path)

    def _on_browse_java(self, button):
        path = self._file_chooser("Select Java executable")
        if path:
            self.java_entry.set_text(path)

    def _file_chooser(self, title, pattern=None):
        dialog = Gtk.FileChooserDialog(
            title=title,
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Open", Gtk.ResponseType.OK)

        if pattern:
            filt = Gtk.FileFilter()
            filt.set_name(pattern)
            filt.add_pattern(pattern)
            dialog.add_filter(filt)
            all_filt = Gtk.FileFilter()
            all_filt.set_name("All files")
            all_filt.add_pattern("*")
            dialog.add_filter(all_filt)

        response = dialog.run()
        path = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return path

    def apply(self):
        self.cfg["acs_exe_path"] = self.exe_entry.get_text().strip()
        self.cfg["acs_jar_path"] = self.jar_entry.get_text().strip()
        self.cfg["java_path"] = self.java_entry.get_text().strip()
        self.cfg["java_opts"] = self.opts_entry.get_text().strip()
        self.cfg["logon_cmd"] = self.logon_entry.get_text().strip()
