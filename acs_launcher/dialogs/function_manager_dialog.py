import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class FunctionManagerDialog(Gtk.Dialog):
    """Manage functions: add/edit/remove launch configurations."""

    def __init__(self, parent, cfg):
        super().__init__(
            title="Manage Functions",
            transient_for=parent,
            modal=True,
        )
        self.cfg = cfg
        self.set_default_size(550, 400)
        self.add_button("Close", Gtk.ResponseType.CLOSE)

        box = self.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(8)

        # Function list
        self.fn_store = Gtk.ListStore(str, str)  # id, label
        self.fn_tree = Gtk.TreeView(model=self.fn_store)
        self.fn_tree.append_column(
            Gtk.TreeViewColumn("ID", Gtk.CellRendererText(), text=0)
        )
        self.fn_tree.append_column(
            Gtk.TreeViewColumn("Label", Gtk.CellRendererText(), text=1)
        )
        self.fn_tree.get_selection().connect("changed", self._on_fn_selected)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add(self.fn_tree)
        box.pack_start(scroll, True, True, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=8)
        add_btn = Gtk.Button(label="Add Function")
        add_btn.connect("clicked", self._on_add)
        btn_box.pack_start(add_btn, False, False, 0)

        self.edit_btn = Gtk.Button(label="Edit Function")
        self.edit_btn.connect("clicked", self._on_edit)
        self.edit_btn.set_sensitive(False)
        btn_box.pack_start(self.edit_btn, False, False, 0)

        self.remove_btn = Gtk.Button(label="Remove Function")
        self.remove_btn.connect("clicked", self._on_remove)
        self.remove_btn.set_sensitive(False)
        btn_box.pack_start(self.remove_btn, False, False, 0)

        box.pack_start(btn_box, False, False, 0)

        self._refresh_list()
        self.show_all()

    def _refresh_list(self):
        self.fn_store.clear()
        for fn in self.cfg["functions"]:
            self.fn_store.append([fn["id"], fn["label"]])

    def _on_fn_selected(self, selection):
        model, tree_iter = selection.get_selected()
        has_sel = tree_iter is not None
        self.edit_btn.set_sensitive(has_sel)
        self.remove_btn.set_sensitive(has_sel)

    def _get_selected_index(self):
        selection = self.fn_tree.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            return None
        return model.get_path(tree_iter).get_indices()[0]

    def _on_add(self, button):
        fn = {
            "id": "",
            "label": "",
            "launch_cmd": "",
            "logon_cmd": None,
            "system_fields": [],
        }
        dialog = FunctionEditDialog(self, fn, is_new=True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.apply(fn)
            self.cfg["functions"].append(fn)
            self._refresh_list()
        dialog.destroy()

    def _on_edit(self, button):
        idx = self._get_selected_index()
        if idx is None:
            return
        fn = self.cfg["functions"][idx]
        dialog = FunctionEditDialog(self, fn, is_new=False)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.apply(fn)
            self._refresh_list()
        dialog.destroy()

    def _on_remove(self, button):
        idx = self._get_selected_index()
        if idx is None:
            return
        fn = self.cfg["functions"][idx]
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Remove function '{fn['label']}'?",
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.cfg["functions"].pop(idx)
            self._refresh_list()


class FunctionEditDialog(Gtk.Dialog):
    """Add or edit a single function."""

    def __init__(self, parent, fn, is_new=False):
        title = "Add Function" if is_new else "Edit Function"
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_default_size(550, 450)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(10)

        grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        box.pack_start(grid, False, False, 0)

        # ID
        grid.attach(Gtk.Label(label="ID:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.id_entry = Gtk.Entry()
        self.id_entry.set_text(fn.get("id", ""))
        self.id_entry.set_hexpand(True)
        grid.attach(self.id_entry, 1, 0, 1, 1)

        # Label
        grid.attach(Gtk.Label(label="Label:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.label_entry = Gtk.Entry()
        self.label_entry.set_text(fn.get("label", ""))
        self.label_entry.set_hexpand(True)
        grid.attach(self.label_entry, 1, 1, 1, 1)

        # Launch command
        grid.attach(
            Gtk.Label(label="Launch command:", halign=Gtk.Align.END, valign=Gtk.Align.START),
            0, 2, 1, 1,
        )
        self.launch_entry = Gtk.Entry()
        self.launch_entry.set_text(fn.get("launch_cmd", ""))
        self.launch_entry.set_hexpand(True)
        grid.attach(self.launch_entry, 1, 2, 1, 1)

        # Logon command
        grid.attach(
            Gtk.Label(label="Logon command:", halign=Gtk.Align.END, valign=Gtk.Align.START),
            0, 3, 1, 1,
        )
        logon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.logon_check = Gtk.CheckButton(label="Requires logon before launch")
        self.logon_check.connect("toggled", self._on_logon_toggled)
        logon_box.pack_start(self.logon_check, False, False, 0)

        self.logon_entry = Gtk.Entry()
        self.logon_entry.set_placeholder_text(
            "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth"
        )
        logon_box.pack_start(self.logon_entry, False, False, 0)
        grid.attach(logon_box, 1, 3, 1, 1)

        if fn.get("logon_cmd"):
            self.logon_check.set_active(True)
            self.logon_entry.set_text(fn["logon_cmd"])
        else:
            self.logon_check.set_active(False)
            self.logon_entry.set_sensitive(False)

        # Required system fields
        grid.attach(
            Gtk.Label(label="System fields:", halign=Gtk.Align.END, valign=Gtk.Align.START),
            0, 4, 1, 1,
        )
        fields_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.fields_entry = Gtk.Entry()
        self.fields_entry.set_text(", ".join(fn.get("system_fields", [])))
        self.fields_entry.set_placeholder_text("e.g. hod_file, lib")
        fields_box.pack_start(self.fields_entry, False, False, 0)
        fields_box.pack_start(
            Gtk.Label(
                label="Comma-separated list of custom fields required from each system",
                halign=Gtk.Align.START,
            ),
            False, False, 0,
        )
        grid.attach(fields_box, 1, 4, 1, 1)

        # Placeholder help
        help_label = Gtk.Label(
            label=(
                "<small><b>Available placeholders:</b> {system}, {user}, {password}, "
                "{acs_jar}, {java}, plus any system custom field names</small>"
            ),
            use_markup=True,
            halign=Gtk.Align.START,
            wrap=True,
        )
        box.pack_start(help_label, False, False, 5)

        self.show_all()

    def _on_logon_toggled(self, check):
        self.logon_entry.set_sensitive(check.get_active())

    def apply(self, fn):
        fn["id"] = self.id_entry.get_text().strip()
        fn["label"] = self.label_entry.get_text().strip()
        fn["launch_cmd"] = self.launch_entry.get_text().strip()
        if self.logon_check.get_active():
            logon_text = self.logon_entry.get_text().strip()
            if not logon_text:
                logon_text = self.logon_entry.get_placeholder_text()
            fn["logon_cmd"] = logon_text or None
        else:
            fn["logon_cmd"] = None
        fields_text = self.fields_entry.get_text().strip()
        if fields_text:
            fn["system_fields"] = [f.strip() for f in fields_text.split(",") if f.strip()]
        else:
            fn["system_fields"] = []
