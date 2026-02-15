import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class PasswordDialog(Gtk.Dialog):
    def __init__(self, parent, system, user):
        super().__init__(
            title="Enter Password",
            transient_for=parent,
            modal=True,
        )
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(15)
        box.set_margin_bottom(10)

        label = Gtk.Label(
            label=f"Password for <b>{user}</b> on <b>{system}</b>:",
            use_markup=True,
            halign=Gtk.Align.START,
        )
        box.pack_start(label, False, False, 0)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        box.pack_start(self.password_entry, False, False, 0)

        self.show_check = Gtk.CheckButton(label="Show password")
        self.show_check.connect("toggled", self._on_show_toggled)
        box.pack_start(self.show_check, False, False, 0)

        self.save_check = Gtk.CheckButton(label="Save to keyring")
        self.save_check.set_active(True)
        box.pack_start(self.save_check, False, False, 0)

        self.show_all()

    def _on_show_toggled(self, check):
        self.password_entry.set_visibility(check.get_active())

    def get_password(self):
        return self.password_entry.get_text()

    def get_save_to_keyring(self):
        return self.save_check.get_active()
