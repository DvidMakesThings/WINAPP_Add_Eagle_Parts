# gui/app.py

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
        self.prefix_var        = tk.StringVar()
        self.value_var         = tk.StringVar()
        self.symbol_var        = tk.StringVar()
        self.package_data      = {}    # Populated by PackageSelectionPanel
        self.deviceset_widgets = {}

        # Will hold the currently loaded XML tree
        self.current_tree = None

        # Build UI sections
        self._build_top_controls()
        self._build_main_frame()
        self._build_action_buttons()

    def _build_top_controls(self):
        """
        Top row: file‐path entry + Browse + Load Packages,
        plus DeviceSet Name / Prefix / Value / Symbol dropdown.
        """
        self.top_controls = TopControlsFrame(
            self,
            path_var            = self.path_var,
            device_name_var     = self.device_name_var,
            prefix_var          = self.prefix_var,
            value_var           = self.value_var,
            symbol_var          = self.symbol_var,
            browse_command      = self._browse_file,
            load_command        = self._load_packages,
            symbol_list_provider= XMLHandler.list_symbols
        )

    def _build_main_frame(self):
        """
        Splits the main area into two panels side by side:
          - Left: ExistingDevicesPanel (collapsible existing devicesets).
          - Right: header row ("Select All") + scrollable PackageSelectionPanel below.
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

        # Configure columns for header + data‐columns
        right_container.grid_columnconfigure(0, weight=0, minsize=40)   # checkbox
        right_container.grid_columnconfigure(1, weight=0, minsize=80)   # Package
        right_container.grid_columnconfigure(2, weight=3, minsize=150)  # Description
        right_container.grid_columnconfigure(3, weight=1, minsize=100)  # LCSC Part#

        # ─── HEADER ROW (row=0) ───
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
            width                 = RIGHT_PANEL_WIDTH,
            height                = RIGHT_PANEL_HEIGHT,
            package_data          = self.package_data,
            pkg_toggle_callback   = self._on_pkg_toggle,
            package_list_provider = XMLHandler.list_packages
        )
        self.right_panel.grid(
            row        = 1,
            column     = 0,
            columnspan = 4,
            sticky     = "nsew",
            pady       = (0, 5)
        )
        right_container.grid_rowconfigure(1, weight=1)

    def _build_action_buttons(self):
        """
        Bottom row: "Add Device" (left) and "Quit" (right).
        """
        self.action_buttons = ActionButtonsFrame(
            self,
            add_command  = self._on_add_device,
            quit_command = self.destroy
        )

    def _browse_file(self):
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
        3) Populate right panel with ALL available packages (empty template).
        4) Clear top fields (Name / Prefix / Value / Symbol).
        """
        lib_path = self.path_var.get().strip()
        try:
            tree = XMLHandler.parse_library(lib_path)
            self.current_tree = tree

            # Populate left panel
            self.left_panel.load_devicesets(tree)

            # Populate right panel with ALL packages (empty template form)
            self.select_all_var.set(False)
            self.right_panel.load_all_packages(tree)

            # Clear top fields
            self.device_name_var.set("")
            self.prefix_var.set("")
            self.value_var.set("")
            self.symbol_var.set("")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load library:\n{e}")

    def _on_deviceset_selected(self, ds_name):
        """
        When the user clicks on an existing deviceset on the left:
         • If ds_name is None: clear everything.
         • Otherwise: prefill top‐fields (Name, Prefix, Value, Symbol) 
           and call load_packages_from_deviceset() so the right side shows ALL packages.
        """
        if self.current_tree is None:
            return

        if ds_name is None:
            # No deviceset selected (user unchecked). Clear top‐fields and right panel.
            self.device_name_var.set("")
            self.prefix_var.set("")
            self.value_var.set("")   # Clear value
            self.symbol_var.set("")
            self.select_all_var.set(False)
            self.right_panel.load_packages_from_deviceset(None)
            return

        # 1) Prefill “Device Set Name” and “Prefix”
        self.device_name_var.set(ds_name)
        existing_ds = XMLHandler.get_existing_deviceset(self.current_tree, ds_name)
        if existing_ds is None:
            messagebox.showerror("Error", f"Deviceset '{ds_name}' not found.")
            return

        prefix_attr = existing_ds.get("prefix", "")
        self.prefix_var.set(prefix_attr)

        # 2) Read “Symbol” from <gates><gate symbol="…">
        gates_parent = existing_ds.find("gates")
        if gates_parent is not None:
            gate = gates_parent.find("gate")
            if gate is not None and gate.get("symbol"):
                self.symbol_var.set(gate.get("symbol"))
            else:
                self.symbol_var.set("")
        else:
            self.symbol_var.set("")

        # 3) Read “Value” from the first <device>/<technologies>/<technology>/<attribute name="VALUE">
        #    We assume all devices in this deviceset share the same VALUE, so we grab the first one.
        value_str = ""
        devs_parent = existing_ds.find("devices")
        if devs_parent is not None:
            first_device = devs_parent.find("device")
            if first_device is not None:
                tech = first_device.find("./technologies/technology")
                if tech is not None:
                    for attr in tech.findall("attribute"):
                        if attr.get("name") == "VALUE":
                            value_str = attr.get("value", "")
                            break
        self.value_var.set(value_str)

        # 4) Now load the right panel _with all packages_, pre‐filling DESC+LCSC for the ones that exist
        self.select_all_var.set(False)
        # Pass self.current_tree into the panel so it can call XMLHandler.list_packages(tree)
        self.right_panel.tree = self.current_tree
        self.right_panel.load_packages_from_deviceset(existing_ds)

    def _toggle_select_all(self):
        """
        When “Select All” is checked, mark every package’s checkbox
        and enable its Description/LCSC fields. When unchecked, uncheck all.
        """
        should_select = self.select_all_var.get()
        for pkg_name, data in self.package_data.items():
            if data["var"].get() != should_select:
                data["var"].set(should_select)
                self._on_pkg_toggle(pkg_name)

    def _on_pkg_toggle(self, pkg_name):
        """
        Enable/disable the DESCRIPTION and LCSC entry whenever its checkbox toggles.
        """
        data = self.package_data.get(pkg_name)
        if not data:
            return

        if data["var"].get():
            data["desc_entry"].configure(state="normal")
            data["lcsc_entry"].configure(state="normal")
        else:
            data["desc_entry"].configure(state="disabled")
            data["lcsc_entry"].configure(state="disabled")

    def _on_add_device(self):
        """
        Called when the user clicks “Add Device”:
         1) Gather DeviceSet name, prefix, symbol, global value, and checked packages.
         2) Skip any package missing DESCRIPTION or LCSC.
         3) If that deviceset already exists, merge into it; otherwise create new.
         4) Save and reload left panel.
         5) Clear top fields + right panel.
        """
        lib_path   = self.path_var.get().strip()
        new_name   = self.device_name_var.get().strip()
        new_prefix = self.prefix_var.get().strip()
        new_value  = self.value_var.get().strip()
        new_symbol = self.symbol_var.get().strip()

        if not new_name:
            messagebox.showerror("Error", "You must enter a deviceset name (new or existing).")
            return
        if not new_prefix:
            messagebox.showerror("Error", "You must enter a prefix (e.g. R, C, U).")
            return
        if not new_symbol:
            messagebox.showerror("Error", "You must select a symbol.")
            return
        if not new_value:
            messagebox.showerror("Error", "You must enter a value for the device.")
            return

        chosen_pkgs = [pkg for pkg, d in self.package_data.items() if d["var"].get()]
        if not chosen_pkgs:
            messagebox.showerror("Error", "Select at least one package to update.")
            return

        valid_pkgs = {}
        skipped    = []
        for pkg in chosen_pkgs:
            desc = self.package_data[pkg]["desc_var"].get().strip()
            lcsc = self.package_data[pkg]["lcsc_var"].get().strip()
            if desc == "" or lcsc == "":
                skipped.append(pkg)
            else:
                valid_pkgs[pkg] = {"value": new_value, "desc": desc, "lcsc": lcsc}

        if not valid_pkgs:
            messagebox.showerror(
                "Error",
                "None of the selected packages have both DESCRIPTION and LCSC Part# filled. Nothing to save."
            )
            return

        try:
            tree          = self.current_tree
            template_ds   = XMLHandler.find_template_deviceset(tree)
            template_devs = XMLHandler.extract_template_devices(template_ds)
            existing_ds   = XMLHandler.get_existing_deviceset(tree, new_name)

            if existing_ds:
                # Overwrite prefix/uservalue on existing <deviceset>
                existing_ds.set("prefix", new_prefix)
                existing_ds.set("uservalue", "yes")
                # Merge with the given symbol_name
                updated, added = XMLHandler.merge_into_deviceset(
                    existing_ds,
                    list(valid_pkgs.keys()),
                    template_devs,
                    valid_pkgs,
                    symbol_name=new_symbol
                )
                XMLHandler.save_library(tree, lib_path)

            else:
                # Create brand‐new <deviceset> (name, prefix, uservalue="yes")
                new_ds = XMLHandler.create_new_deviceset(
                    tree,
                    template_ds,
                    new_name,
                    list(valid_pkgs.keys()),
                    valid_pkgs,
                    symbol_name=new_symbol
                )
                new_ds.set("prefix", new_prefix)
                new_ds.set("uservalue", "yes")
                XMLHandler.save_library(tree, lib_path)

            # Reload left panel so changes appear immediately
            self.left_panel.load_devicesets(tree)

            # Clear everything
            self.device_name_var.set("")
            self.prefix_var.set("")
            self.value_var.set("")
            self.symbol_var.set("")
            self.select_all_var.set(False)
            for pkg, data in self.package_data.items():
                data["var"].set(False)
                data["desc_var"].set("")
                data["lcsc_var"].set("")
                data["desc_entry"].configure(state="disabled")
                data["lcsc_entry"].configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add/update device:\n{e}")
