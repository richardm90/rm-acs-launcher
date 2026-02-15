import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class SystemManagerDialog(Gtk.Dialog):
    """Manage systems: add/edit/remove systems, their users, and custom fields."""

    def __init__(self, parent, cfg):
        super().__init__(
            title="Manage Systems",
            transient_for=parent,
            modal=True,
        )
        self.cfg = cfg
        self.set_default_size(500, 400)
        self.add_button("Close", Gtk.ResponseType.CLOSE)

        box = self.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(8)

        # System list
        self.system_store = Gtk.ListStore(str, str)  # name, label
        self.system_tree = Gtk.TreeView(model=self.system_store)
        self.system_tree.append_column(
            Gtk.TreeViewColumn("Hostname", Gtk.CellRendererText(), text=0)
        )
        self.system_tree.append_column(
            Gtk.TreeViewColumn("Label", Gtk.CellRendererText(), text=1)
        )
        self.system_tree.get_selection().connect("changed", self._on_system_selected)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add(self.system_tree)
        box.pack_start(scroll, True, True, 0)

        # System buttons
        sys_btn_box = Gtk.Box(spacing=8)
        add_btn = Gtk.Button(label="Add System")
        add_btn.connect("clicked", self._on_add_system)
        sys_btn_box.pack_start(add_btn, False, False, 0)

        self.edit_btn = Gtk.Button(label="Edit System")
        self.edit_btn.connect("clicked", self._on_edit_system)
        self.edit_btn.set_sensitive(False)
        sys_btn_box.pack_start(self.edit_btn, False, False, 0)

        self.remove_btn = Gtk.Button(label="Remove System")
        self.remove_btn.connect("clicked", self._on_remove_system)
        self.remove_btn.set_sensitive(False)
        sys_btn_box.pack_start(self.remove_btn, False, False, 0)

        box.pack_start(sys_btn_box, False, False, 0)

        self._refresh_list()
        self.show_all()

    def _refresh_list(self):
        self.system_store.clear()
        for s in self.cfg["systems"]:
            self.system_store.append([s["name"], s.get("label", "")])

    def _on_system_selected(self, selection):
        model, tree_iter = selection.get_selected()
        has_sel = tree_iter is not None
        self.edit_btn.set_sensitive(has_sel)
        self.remove_btn.set_sensitive(has_sel)

    def _get_selected_index(self):
        selection = self.system_tree.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            return None
        return model.get_path(tree_iter).get_indices()[0]

    def _on_add_system(self, button):
        system = {"name": "", "label": "", "users": [], "fields": {}}
        dialog = SystemEditDialog(self, system, is_new=True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.apply(system)
            self.cfg["systems"].append(system)
            self._refresh_list()
        dialog.destroy()

    def _on_edit_system(self, button):
        idx = self._get_selected_index()
        if idx is None:
            return
        system = self.cfg["systems"][idx]
        dialog = SystemEditDialog(self, system, is_new=False)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.apply(system)
            self._refresh_list()
        dialog.destroy()

    def _on_remove_system(self, button):
        idx = self._get_selected_index()
        if idx is None:
            return
        system = self.cfg["systems"][idx]
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Remove system '{system.get('label', system['name'])}'?",
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.cfg["systems"].pop(idx)
            self._refresh_list()


class SystemEditDialog(Gtk.Dialog):
    """Add or edit a single system: hostname, label, users, and custom fields."""

    def __init__(self, parent, system, is_new=False):
        title = "Add System" if is_new else "Edit System"
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_default_size(450, 500)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(15)
        box.set_margin_end(15)
        box.set_margin_top(15)
        box.set_margin_bottom(10)

        # Hostname
        grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        box.pack_start(grid, False, False, 0)

        grid.attach(Gtk.Label(label="Hostname:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(system.get("name", ""))
        self.name_entry.set_hexpand(True)
        grid.attach(self.name_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Label:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.label_entry = Gtk.Entry()
        self.label_entry.set_text(system.get("label", ""))
        self.label_entry.set_hexpand(True)
        grid.attach(self.label_entry, 1, 1, 1, 1)

        # --- Users section ---
        box.pack_start(
            Gtk.Label(label="<b>Users</b>", use_markup=True, halign=Gtk.Align.START),
            False, False, 0,
        )

        self.user_store = Gtk.ListStore(str)
        for u in system.get("users", []):
            self.user_store.append([u])

        user_tree = Gtk.TreeView(model=self.user_store)
        renderer = Gtk.CellRendererText(editable=True)
        renderer.connect("edited", self._on_user_edited)
        user_tree.append_column(Gtk.TreeViewColumn("User", renderer, text=0))
        self.user_selection = user_tree.get_selection()

        user_scroll = Gtk.ScrolledWindow()
        user_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        user_scroll.set_min_content_height(80)
        user_scroll.add(user_tree)
        box.pack_start(user_scroll, True, True, 0)

        user_btn_box = Gtk.Box(spacing=8)
        add_user_btn = Gtk.Button(label="Add User")
        add_user_btn.connect("clicked", self._on_add_user)
        user_btn_box.pack_start(add_user_btn, False, False, 0)

        rm_user_btn = Gtk.Button(label="Remove User")
        rm_user_btn.connect("clicked", self._on_remove_user)
        user_btn_box.pack_start(rm_user_btn, False, False, 0)
        box.pack_start(user_btn_box, False, False, 0)

        # --- Custom fields section ---
        box.pack_start(
            Gtk.Label(
                label="<b>Custom Fields</b>",
                use_markup=True,
                halign=Gtk.Align.START,
            ),
            False, False, 0,
        )
        box.pack_start(
            Gtk.Label(
                label="Key/value pairs available as {key} placeholders in function commands",
                halign=Gtk.Align.START,
            ),
            False, False, 0,
        )

        self.fields_store = Gtk.ListStore(str, str)  # key, value
        for k, v in system.get("fields", {}).items():
            self.fields_store.append([k, v])

        fields_tree = Gtk.TreeView(model=self.fields_store)

        key_renderer = Gtk.CellRendererText(editable=True)
        key_renderer.connect("edited", self._on_field_key_edited)
        fields_tree.append_column(
            Gtk.TreeViewColumn("Key", key_renderer, text=0)
        )

        val_renderer = Gtk.CellRendererText(editable=True)
        val_renderer.connect("edited", self._on_field_value_edited)
        fields_tree.append_column(
            Gtk.TreeViewColumn("Value", val_renderer, text=1)
        )

        self.fields_selection = fields_tree.get_selection()

        fields_scroll = Gtk.ScrolledWindow()
        fields_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        fields_scroll.set_min_content_height(80)
        fields_scroll.add(fields_tree)
        box.pack_start(fields_scroll, True, True, 0)

        fields_btn_box = Gtk.Box(spacing=8)
        add_field_btn = Gtk.Button(label="Add Field")
        add_field_btn.connect("clicked", self._on_add_field)
        fields_btn_box.pack_start(add_field_btn, False, False, 0)

        rm_field_btn = Gtk.Button(label="Remove Field")
        rm_field_btn.connect("clicked", self._on_remove_field)
        fields_btn_box.pack_start(rm_field_btn, False, False, 0)
        box.pack_start(fields_btn_box, False, False, 0)

        self.show_all()

    # --- User callbacks ---

    def _on_user_edited(self, renderer, path, new_text):
        self.user_store[path][0] = new_text.strip()

    def _on_add_user(self, button):
        self.user_store.append(["new_user"])

    def _on_remove_user(self, button):
        model, tree_iter = self.user_selection.get_selected()
        if tree_iter:
            model.remove(tree_iter)

    # --- Field callbacks ---

    def _on_field_key_edited(self, renderer, path, new_text):
        self.fields_store[path][0] = new_text.strip()

    def _on_field_value_edited(self, renderer, path, new_text):
        self.fields_store[path][1] = new_text.strip()

    def _on_add_field(self, button):
        self.fields_store.append(["field_name", ""])

    def _on_remove_field(self, button):
        model, tree_iter = self.fields_selection.get_selected()
        if tree_iter:
            model.remove(tree_iter)

    # --- Apply ---

    def apply(self, system):
        system["name"] = self.name_entry.get_text().strip()
        system["label"] = self.label_entry.get_text().strip()
        system["users"] = [row[0] for row in self.user_store if row[0].strip()]
        system["fields"] = {}
        for row in self.fields_store:
            key = row[0].strip()
            value = row[1].strip()
            if key:
                system["fields"][key] = value
