import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from xml_handler import XMLHandler

from config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_RESIZABLE,
    LEFT_PANEL_WIDTH,
    LEFT_PANEL_HEIGHT,
    RIGHT_PANEL_WIDTH,
    RIGHT_PANEL_HEIGHT,
)

from gui.top_controls    import TopControlsFrame
from gui.left_panel      import ExistingDevicesPanel
from gui.right_panel     import PackageSelectionPanel
from gui.action_buttons  import ActionButtonsFrame


class EagleLibraryGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Eagle Library Device Adder")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(*WINDOW_RESIZABLE)

        # Shared state variables
        self.path_var          = tk.StringVar()
        self.device_name_var   = tk.StringVar()
        self.package_data      = {}   # Populated by PackageSelectionPanel
        self.deviceset_widgets = {}

        # Will hold the currently loaded XML tree
        self.current_tree = None

        # Build all UI sections
        self._build_top_controls()
        self._build_main_frame()
        self._build_action_buttons()

    def _build_top_controls(self):
        """
        Top row: file‐path entry + Browse button + Load Packages button,
        plus the “New Device Set Name” entry.
        """
        self.top_controls = TopControlsFrame(
            self,
            path_var        = self.path_var,
            device_name_var = self.device_name_var,
            browse_command  = self._browse_file,
            load_command    = self._load_packages
        )

    def _build_main_frame(self):
        """
        Splits the main area into two panels side by side:
          - Left: ExistingDevicesPanel (collapsible existing devicesets).
          - Right: a header row (including “Select All”) and a
                   scrollable PackageSelectionPanel beneath it.
        """
        parent = ctk.CTkFrame(self)
        parent.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        # ─── Left panel ───
        self.left_panel = ExistingDevicesPanel(
            parent,
            width     = LEFT_PANEL_WIDTH,
            height    = LEFT_PANEL_HEIGHT,
            on_select = self._on_deviceset_selected
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=2)

        # ─── Right panel ───
        right_container = ctk.CTkFrame(parent)
        right_container.grid(row=0, column=1, sticky="nsew")

        # Configure five columns for header + data‐columns
        right_container.grid_columnconfigure(0, weight=0, minsize=40)   # checkbox column
        right_container.grid_columnconfigure(1, weight=0, minsize=80)   # Package
        right_container.grid_columnconfigure(2, weight=0, minsize=80)   # Value
        right_container.grid_columnconfigure(3, weight=3, minsize=150)  # Description
        right_container.grid_columnconfigure(4, weight=1, minsize=100)  # LCSC Part#

        # ─── HEADER ROW (row=0) ───
        # Column 0: “Select All” checkbox
        self.select_all_var = tk.BooleanVar(value=False)
        select_all_chk = ctk.CTkCheckBox(
            right_container,
            text="Select All",
            variable=self.select_all_var,
            command=self._toggle_select_all
        )
        select_all_chk.grid(
            row=0,
            column=0,
            padx=(5, 5),
            pady=(0, 5),
            sticky="w"
        )


        # ─── SCROLLABLE PACKAGE ROWS (row=1) ───
        self.right_panel = PackageSelectionPanel(
            right_container,
            width               = RIGHT_PANEL_WIDTH,
            height              = RIGHT_PANEL_HEIGHT,
            package_data        = self.package_data,
            pkg_toggle_callback = self._on_pkg_toggle
        )
        self.right_panel.grid(
            row        = 1,
            column     = 0,
            columnspan = 5,
            sticky     = "nsew",
            pady       = (0, 5)
        )
        right_container.grid_rowconfigure(1, weight=1)

    def _build_action_buttons(self):
        """
        Bottom row: “Add Device” (or “Update Device”) on the left,
        “Quit” on the right.
        """
        self.action_buttons = ActionButtonsFrame(
            self,
            add_command  = self._on_add_device,
            quit_command = self.destroy
        )

    def _browse_file(self):
        """
        Opens a file dialog for the user to pick an Eagle .lbr/.xml.
        Sets self.path_var if a valid file is chosen.
        """
        fn = tk.filedialog.askopenfilename(
            title="Select Eagle Library",
            filetypes=[("Eagle Library", "*.lbr"), ("XML Files", "*.xml"), ("All files", "*.*")],
        )
        if fn:
            self.path_var.set(fn)

    def _load_packages(self):
        """
        1) Parse the selected library into self.current_tree.
        2) Populate the left panel with all existing devicesets.
        3) Clear the right panel (no deviceset selected initially).
        """
        lib_path = self.path_var.get().strip()
        try:
            tree = XMLHandler.parse_library(lib_path)
            self.current_tree = tree

            # Populate left panel
            self.left_panel.load_devicesets(tree)

            # Clear right panel & uncheck “Select All”
            self.select_all_var.set(False)
            self.right_panel.load_packages_from_deviceset(None)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load library:\n{e}")

    def _on_deviceset_selected(self, ds_name):
        """
        Callback when a deviceset checkbox on the left is toggled:
         • If ds_name is not None, prefill the “New Device Set Name” entry
           and load that deviceset’s packages on the right.
         • If ds_name is None, clear the name entry, uncheck “Select All,”
           and clear the right panel.
        """
        if self.current_tree is None:
            return

        if ds_name is None:
            # User unchecked the currently selected deviceset
            self.device_name_var.set("")
            self.select_all_var.set(False)
            self.right_panel.load_packages_from_deviceset(None)
            return

        # Prefill the “New Device Set Name” entry:
        self.device_name_var.set(ds_name)

        existing_ds = XMLHandler.get_existing_deviceset(self.current_tree, ds_name)
        if existing_ds is None:
            messagebox.showerror("Error", f"Deviceset '{ds_name}' not found.")
            return

        # Load its packages (VALUE / DESCRIPTION / LCSC) into the right panel
        self.select_all_var.set(False)
        self.right_panel.load_packages_from_deviceset(existing_ds)

    def _toggle_select_all(self):
        """
        When “Select All” is checked, mark every package’s checkbox
        and enable its Value/Description/LCSC fields.
        When unchecked, uncheck all package checkboxes (leave text intact).
        """
        should_select = self.select_all_var.get()

        for pkg_name, data in self.package_data.items():
            if data["var"].get() != should_select:
                data["var"].set(should_select)
                # Call per‐row toggle logic to enable/disable fields
                self._on_pkg_toggle(pkg_name)

    def _on_pkg_toggle(self, pkg_name):
        """
        Enable or disable the VALUE, DESCRIPTION, and LCSC entry for pkg_name
        whenever its checkbox is toggled.
        """
        data = self.package_data.get(pkg_name)
        if not data:
            return

        if data["var"].get():
            data["value_entry"].configure(state="normal")
            data["desc_entry"].configure(state="normal")
            data["lcsc_entry"].configure(state="normal")
        else:
            data["value_entry"].configure(state="disabled")
            data["desc_entry"].configure(state="disabled")
            data["lcsc_entry"].configure(state="disabled")
            # We intentionally do NOT clear their text—just disable the field.

    def _on_add_device(self):
        """
        Called when “Add Device” is clicked:
         1) Gather the target deviceset name + all checked packages.
         2) For each checked package, read VALUE, DESCRIPTION, LCSC_PART.
            If any of VALUE/DESCRIPTION/LCSC_PART is empty, skip that package.
         3) If that deviceset already exists, merge into it; otherwise create new.
         4) Save library to disk and reload left panel to reflect changes.
         5) Clear all right‐side inputs (checkboxes + text fields).
        """
        lib_path = self.path_var.get().strip()
        new_name = self.device_name_var.get().strip()

        if not new_name:
            messagebox.showerror("Error", "You must enter a deviceset name (new or existing).")
            return

        chosen_pkgs = [pkg for pkg, d in self.package_data.items() if d["var"].get()]
        if not chosen_pkgs:
            messagebox.showerror("Error", "Select at least one package to update.")
            return

        valid_pkgs = {}
        skipped    = []
        for pkg in chosen_pkgs:
            value = self.package_data[pkg]["value_var"].get().strip()
            desc  = self.package_data[pkg]["desc_var"].get().strip()
            lcsc  = self.package_data[pkg]["lcsc_var"].get().strip()
            if value == "" or desc == "" or lcsc == "":
                skipped.append(pkg)
            else:
                valid_pkgs[pkg] = {"value": value, "desc": desc, "lcsc": lcsc}

        if not valid_pkgs:
            messagebox.showerror(
                "Error",
                "None of the selected packages have VALUE, DESCRIPTION, and LCSC Part# all filled. Nothing to save."
            )
            return

        try:
            tree         = self.current_tree
            template_ds  = XMLHandler.find_template_deviceset(tree)
            template_devs= XMLHandler.extract_template_devices(template_ds)
            existing_ds  = XMLHandler.get_existing_deviceset(tree, new_name)

            if existing_ds:
                updated, added = XMLHandler.merge_into_deviceset(
                    existing_ds,
                    list(valid_pkgs.keys()),
                    template_devs,
                    valid_pkgs
                )
                XMLHandler.save_library(tree, lib_path)
            else:
                XMLHandler.create_new_deviceset(
                    tree,
                    template_ds,
                    new_name,
                    list(valid_pkgs.keys()),
                    valid_pkgs
                )
                XMLHandler.save_library(tree, lib_path)

            # Reload left panel so the new/updated deviceset appears immediately
            self.left_panel.load_devicesets(tree)

            # Clear right‐side inputs
            self.device_name_var.set("")
            self.select_all_var.set(False)
            for pkg, data in self.package_data.items():
                data["var"].set(False)
                data["value_var"].set("")
                data["desc_var"].set("")
                data["lcsc_var"].set("")
                data["value_entry"].configure(state="disabled")
                data["desc_entry"].configure(state="disabled")
                data["lcsc_entry"].configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add/update device:\n{e}")
