import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

from acs_launcher import __version__, config, passwords, launcher
from acs_launcher.dialogs.password_dialog import PasswordDialog
from acs_launcher.dialogs.system_manager_dialog import SystemManagerDialog
from acs_launcher.dialogs.function_manager_dialog import FunctionManagerDialog
from acs_launcher.dialogs.preferences_dialog import PreferencesDialog

import os

ACS_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "icons", "acs-logo.png",
)


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(
            title="RM ACS Launcher",
            default_width=450,
            default_height=350,
            **kwargs,
        )
        self._apply_css()
        self.cfg = config.load_config()
        self._launching = False
        self._logged_on = None  # (system_name, user) of last successful logon
        self._build_ui()
        self._populate_combos()
        self._restore_last_selections()
        self._update_launch_sensitivity()

    def _apply_css(self):
        css = b"""
        .error-status label {
            color: #cc0000;
            font-weight: bold;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # --- Selection area ---
        grid = Gtk.Grid(
            column_spacing=12,
            row_spacing=12,
            margin_top=20,
            margin_bottom=10,
            margin_start=20,
            margin_end=20,
        )
        vbox.pack_start(grid, False, False, 0)

        # System
        grid.attach(Gtk.Label(label="System:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.system_combo = Gtk.ComboBoxText()
        self.system_combo.set_hexpand(True)
        self.system_combo.connect("changed", self._on_system_changed)
        grid.attach(self.system_combo, 1, 0, 1, 1)

        # User
        grid.attach(Gtk.Label(label="User:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.user_combo = Gtk.ComboBoxText()
        self.user_combo.set_hexpand(True)
        self.user_combo.connect("changed", self._on_selection_changed)
        grid.attach(self.user_combo, 1, 1, 1, 1)

        # Function
        grid.attach(Gtk.Label(label="Function:", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.function_combo = Gtk.ComboBoxText()
        self.function_combo.set_hexpand(True)
        self.function_combo.connect("changed", self._on_selection_changed)
        grid.attach(self.function_combo, 1, 2, 1, 1)

        # --- Launch row: Launch button + separator + favourites + ACS icon ---
        self.launch_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=10,
            margin_bottom=10,
            margin_start=20,
            margin_end=20,
        )
        vbox.pack_start(self.launch_row, False, False, 0)

        # ACS default launcher icon
        if os.path.exists(ACS_LOGO_PATH):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                ACS_LOGO_PATH, 28, 28, True
            )
            acs_image = Gtk.Image.new_from_pixbuf(pixbuf)
            acs_btn = Gtk.Button()
            acs_btn.set_image(acs_image)
            acs_btn.set_relief(Gtk.ReliefStyle.NONE)
            acs_btn.set_tooltip_text("IBM ACS Launcher")
            acs_btn.connect("clicked", self._on_launch_acs)
            self.launch_row.pack_start(acs_btn, False, False, 0)

        # Favourites container (rebuilt dynamically)
        self._favourites_box = Gtk.Box(spacing=4)
        self.launch_row.pack_start(self._favourites_box, False, False, 0)

        # Separator + Launch button on the right
        self.launch_row.pack_start(Gtk.Box(), True, True, 0)  # spacer

        self._favourites_separator = Gtk.Separator(
            orientation=Gtk.Orientation.VERTICAL
        )
        self.launch_row.pack_start(self._favourites_separator, False, False, 4)

        self.launch_button = Gtk.Button(label="Launch")
        self.launch_button.set_size_request(120, -1)
        self.launch_button.get_style_context().add_class("suggested-action")
        self.launch_button.connect("clicked", self._on_launch)
        self.launch_row.pack_start(self.launch_button, False, False, 0)

        self._build_favourites()

        # --- Bottom buttons ---
        button_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_start=20,
            margin_end=20,
            margin_bottom=10,
        )
        vbox.pack_start(button_box, False, False, 0)

        passwords_btn = Gtk.Button(label="Password")
        passwords_btn.connect("clicked", self._on_manage_passwords)
        button_box.pack_start(passwords_btn, True, True, 0)

        systems_btn = Gtk.Button(label="Systems")
        systems_btn.connect("clicked", self._on_manage_systems)
        button_box.pack_start(systems_btn, True, True, 0)

        functions_btn = Gtk.Button(label="Functions")
        functions_btn.connect("clicked", self._on_manage_functions)
        button_box.pack_start(functions_btn, True, True, 0)

        prefs_btn = Gtk.Button(label="Preferences")
        prefs_btn.connect("clicked", self._on_preferences)
        button_box.pack_start(prefs_btn, True, True, 0)

        # --- Status bar ---
        self.statusbar = Gtk.Statusbar()
        self.statusbar.push(0, f"Ready — v{__version__}")
        vbox.pack_end(self.statusbar, False, False, 0)

        self.show_all()

    # ---- Combo population ----

    def _populate_combos(self):
        self.system_combo.remove_all()
        for s in self.cfg["systems"]:
            label = s.get("label") or s["name"]
            self.system_combo.append(s["name"], label)

        self.function_combo.remove_all()
        for fn in self.cfg["functions"]:
            self.function_combo.append(fn["id"], fn["label"])

    def _populate_users(self):
        self.user_combo.remove_all()
        system_name = self.system_combo.get_active_id()
        if not system_name:
            return
        system = config.get_system(self.cfg, system_name)
        if not system:
            return
        for user in system.get("users", []):
            self.user_combo.append(user, user)

    def _restore_last_selections(self):
        last_sys = self.cfg.get("last_system", "")
        if last_sys:
            self.system_combo.set_active_id(last_sys)
        last_user = self.cfg.get("last_user", "")
        if last_user:
            self.user_combo.set_active_id(last_user)
        last_fn = self.cfg.get("last_function", "")
        if last_fn:
            self.function_combo.set_active_id(last_fn)

    # ---- Signal handlers ----

    def _on_system_changed(self, combo):
        self._populate_users()
        # Try to restore last user if switching back to a previously used system
        last_user = self.cfg.get("last_user", "")
        if last_user:
            self.user_combo.set_active_id(last_user)
        self._update_launch_sensitivity()

    def _on_selection_changed(self, combo):
        self._update_launch_sensitivity()

    def _update_launch_sensitivity(self):
        if self._launching:
            self.launch_button.set_sensitive(False)
            return

        system_name = self.system_combo.get_active_id()
        user = self.user_combo.get_active_id()
        fn_id = self.function_combo.get_active_id()

        if not all([system_name, user, fn_id]):
            self.launch_button.set_sensitive(False)
            return

        # Check that the system has the required fields for this function
        system = config.get_system(self.cfg, system_name)
        fn = config.get_function(self.cfg, fn_id)
        if not system or not fn:
            self.launch_button.set_sensitive(False)
            return

        if not config.system_has_required_fields(system, fn):
            self.launch_button.set_sensitive(False)
            self._set_status(
                f"System '{system.get('label', system['name'])}' is missing "
                f"required fields: {', '.join(fn.get('system_fields', []))}"
            )
            return

        self.launch_button.set_sensitive(True)

    def _set_status(self, message):
        self.statusbar.get_style_context().remove_class("error-status")
        self.statusbar.pop(0)
        self.statusbar.push(0, message)

    def _set_error_status(self, message):
        self.statusbar.pop(0)
        self.statusbar.push(0, message)
        self.statusbar.get_style_context().add_class("error-status")

    # ---- Favourites ----

    def _build_favourites(self):
        for child in self._favourites_box.get_children():
            child.destroy()
        has_favourites = False
        for fn in self.cfg["functions"]:
            if not fn.get("is_favourite", False):
                continue
            icon_path = config.resolve_icon_path(fn.get("icon_path", ""), fn["id"])
            if not icon_path or not os.path.exists(icon_path):
                icon_path = ACS_LOGO_PATH
            if not os.path.exists(icon_path):
                continue
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 28, 28, True
                )
            except Exception:
                continue
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            btn = Gtk.Button()
            btn.set_image(image)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_tooltip_text(fn["label"])
            fn_id = fn["id"]
            btn.connect("clicked", lambda b, fid=fn_id: self._on_favourite_launch(fid))
            self._favourites_box.pack_start(btn, False, False, 0)
            has_favourites = True
        self._favourites_separator.set_visible(has_favourites)
        self._favourites_box.show_all()

    def _on_favourite_launch(self, fn_id):
        system_name = self.system_combo.get_active_id()
        user = self.user_combo.get_active_id()
        if not system_name or not user:
            self._set_error_status("Select a system and user first")
            return
        fn = config.get_function(self.cfg, fn_id)
        if not fn:
            self._set_error_status(f"Function '{fn_id}' not found")
            return
        system = config.get_system(self.cfg, system_name)
        if not system:
            return
        if not config.system_has_required_fields(system, fn):
            self._set_error_status(
                f"System is missing required fields: {', '.join(fn.get('system_fields', []))}"
            )
            return
        # Save last selections
        self.cfg["last_system"] = system_name
        self.cfg["last_user"] = user
        self.cfg["last_function"] = fn_id
        config.save_config(self.cfg)
        self._do_launch(system_name, user, system, fn)

    # ---- Launch flow ----

    def _on_launch(self, button):
        system_name = self.system_combo.get_active_id()
        user = self.user_combo.get_active_id()
        fn_id = self.function_combo.get_active_id()
        system = config.get_system(self.cfg, system_name)
        fn = config.get_function(self.cfg, fn_id)

        # Save last selections
        self.cfg["last_system"] = system_name
        self.cfg["last_user"] = user
        self.cfg["last_function"] = fn_id
        config.save_config(self.cfg)

        self._do_launch(system_name, user, system, fn)

    def _do_launch(self, system_name, user, system, fn):
        # Check if we need a password
        needs_password = fn.get("requires_logon", False)
        if not needs_password and "{password}" in fn.get("launch_cmd", ""):
            needs_password = True

        password = None
        if needs_password:
            password = passwords.lookup(system_name, user)
            if password is None:
                dialog = PasswordDialog(self, system_name, user)
                response = dialog.run()
                if response == Gtk.ResponseType.OK:
                    password = dialog.get_password()
                    if dialog.get_save_to_keyring():
                        passwords.store(system_name, user, password)
                dialog.destroy()
                if password is None:
                    self._set_status("Launch cancelled - no password")
                    return

        self._launching = True
        self.launch_button.set_label("Launching...")
        self._update_launch_sensitivity()
        self._set_status("Launching...")

        thread = threading.Thread(
            target=self._launch_thread,
            args=(system, user, password, fn),
            daemon=True,
        )
        thread.start()

    def _launch_thread(self, system, user, password, fn):
        try:
            placeholders = launcher.build_placeholders(
                self.cfg, system, user, password
            )

            # Run logon command if required (skip if already logged on for this system/user)
            logon_key = (system["name"], user)
            if fn.get("requires_logon", False) and self._logged_on != logon_key:
                logon_cmd = self.cfg.get("logon_cmd", "")
                GLib.idle_add(self._set_status, "Authenticating...")
                try:
                    cmd = launcher.substitute(logon_cmd, placeholders)
                except KeyError as e:
                    GLib.idle_add(
                        self._set_error_status, f"Missing placeholder: {e}"
                    )
                    GLib.idle_add(self._launch_finished)
                    return

                ok, msg = launcher.run_logon(cmd)
                if ok:
                    self._logged_on = logon_key
                else:
                    GLib.idle_add(self._set_error_status, msg)
                    GLib.idle_add(self._launch_finished)
                    return

            # Run launch command
            GLib.idle_add(self._set_status, "Launching...")
            try:
                cmd = launcher.substitute(fn["launch_cmd"], placeholders)
            except KeyError as e:
                GLib.idle_add(
                    self._set_status, f"Missing placeholder: {e}"
                )
                GLib.idle_add(self._launch_finished)
                return

            ok, msg = launcher.launch(cmd)
            if ok:
                GLib.idle_add(self._set_status, msg)
            else:
                GLib.idle_add(self._set_error_status, msg)
        except Exception as e:
            GLib.idle_add(self._set_error_status, f"Error: {e}")
        finally:
            GLib.idle_add(self._launch_finished)

    def _launch_finished(self):
        self._launching = False
        self.launch_button.set_label("Launch")
        self._update_launch_sensitivity()

    # ---- ACS default launcher ----

    def _on_launch_acs(self, button):
        acs_exe = self.cfg.get("acs_exe_path", "")
        if not acs_exe:
            self._set_error_status("ACS executable not configured — check Preferences")
            return
        self._set_status("Launching ACS...")
        ok, msg = launcher.launch(acs_exe)
        if ok:
            self._set_status(msg)
        else:
            self._set_error_status(msg)

    # ---- Dialog handlers ----

    def _on_manage_passwords(self, button):
        system_name = self.system_combo.get_active_id()
        user = self.user_combo.get_active_id()

        if not system_name or not user:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Select a system and user first",
            )
            dialog.run()
            dialog.destroy()
            return

        has_pw = passwords.has_password(system_name, user)
        if has_pw:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=f"Password for {user}@{system_name}",
            )
            dialog.format_secondary_text(
                "A password is stored in the keyring. What would you like to do?"
            )
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Remove", Gtk.ResponseType.REJECT)
            dialog.add_button("Update", Gtk.ResponseType.OK)
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.REJECT:
                passwords.clear(system_name, user)
                self._set_status(f"Password removed for {user}@{system_name}")
            elif response == Gtk.ResponseType.OK:
                pw_dialog = PasswordDialog(self, system_name, user)
                resp = pw_dialog.run()
                if resp == Gtk.ResponseType.OK:
                    passwords.store(system_name, user, pw_dialog.get_password())
                    self._set_status(
                        f"Password updated for {user}@{system_name}"
                    )
                pw_dialog.destroy()
        else:
            pw_dialog = PasswordDialog(self, system_name, user)
            resp = pw_dialog.run()
            if resp == Gtk.ResponseType.OK:
                passwords.store(system_name, user, pw_dialog.get_password())
                self._set_status(f"Password saved for {user}@{system_name}")
            pw_dialog.destroy()

    def _on_manage_systems(self, button):
        dialog = SystemManagerDialog(self, self.cfg)
        dialog.run()
        dialog.destroy()
        config.save_config(self.cfg)
        self._populate_combos()
        self._restore_last_selections()
        self._update_launch_sensitivity()

    def _on_manage_functions(self, button):
        dialog = FunctionManagerDialog(self, self.cfg)
        dialog.run()
        dialog.destroy()
        config.save_config(self.cfg)
        self._populate_combos()
        self._restore_last_selections()
        self._update_launch_sensitivity()
        self._build_favourites()

    def _on_preferences(self, button):
        dialog = PreferencesDialog(self, self.cfg)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.apply()
            config.save_config(self.cfg)
            self._set_status("Preferences saved")
        dialog.destroy()
