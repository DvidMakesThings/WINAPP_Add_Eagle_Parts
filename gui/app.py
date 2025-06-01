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

        # Shared variables
        self.path_var          = tk.StringVar()
        self.device_name_var   = tk.StringVar()
        self.package_data      = {}
        self.deviceset_widgets = {}

        # Build UI
        self._build_top_controls()
        self._build_main_frame()
        self._build_action_buttons()

    def _build_top_controls(self):
        """
        Top row: file‐browse, Load Packages button, and new deviceset name entry.
        """
        self.top_controls = TopControlsFrame(
            self,
            path_var         = self.path_var,
            device_name_var  = self.device_name_var,
            browse_command   = self._browse_file,
            load_command     = self._load_packages
        )

    def _build_main_frame(self):
        """
        Main area: two side‐by‐side panels.
          • Left: ExistingDevicesPanel (collapsible list of devicesets + their packages)
          • Right: PackageSelectionPanel (header + scrollable package rows)
        """
        parent = ctk.CTkFrame(self)
        parent.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        # ─── Left panel ───
        self.left_panel = ExistingDevicesPanel(
            parent,
            width  = LEFT_PANEL_WIDTH,
            height = LEFT_PANEL_HEIGHT
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        parent.grid_columnconfigure(0, weight=1)

        # ─── Right panel ───
        right_container = ctk.CTkFrame(parent)
        right_container.grid(row=0, column=1, sticky="nsew")
        parent.grid_columnconfigure(1, weight=2)

        self.right_panel = PackageSelectionPanel(
            right_container,
            width               = RIGHT_PANEL_WIDTH,
            height              = RIGHT_PANEL_HEIGHT,
            package_data        = self.package_data,
            pkg_toggle_callback = self._on_pkg_toggle
        )
        self.right_panel.pack(fill="both", expand=True)

    def _build_action_buttons(self):
        """
        Bottom row: Add Device and Quit buttons.
        """
        self.action_buttons = ActionButtonsFrame(
            self,
            add_command  = self._on_add_device,
            quit_command = self.destroy
        )

    def _browse_file(self):
        """
        Show a file‐open dialog to select an Eagle .lbr/.xml file.
        """
        fn = tk.filedialog.askopenfilename(
            title="Select Eagle Library",
            filetypes=[("Eagle Library", "*.lbr"), ("XML Files", "*.xml"), ("All files", "*.*")],
        )
        if fn:
            self.path_var.set(fn)

    def _load_packages(self):
        """
        1) Parse the selected library.
        2) Populate the left panel (existing devicesets).
        3) Populate the right panel (template packages).
        """
        lib_path = self.path_var.get().strip()
        try:
            tree = XMLHandler.parse_library(lib_path)

            # Left: show all devicesets currently in the library
            self.left_panel.load_devicesets(tree)

            # Right: show template <deviceset>’s packages
            self.right_panel.load_packages_from_template(tree)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load library:\n{e}")

    def _on_pkg_toggle(self, pkg_name):
        """
        Enable or disable DESCRIPTION + LCSC entry when its checkbox is toggled.
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
            data["desc_var"].set("")
            data["lcsc_var"].set("")

    def _on_add_device(self):
        """
        1) Collect new deviceset name + checked packages.
        2) Filter valid packages (both fields filled) vs skipped.
        3) Parse library again, then either merge into existing deviceset or create new.
        4) Save library, show summary, and reload left panel so the new deviceset appears immediately.
        5) Clear right‐panel inputs for next operation.
        """
        lib_path = self.path_var.get().strip()
        new_name = self.device_name_var.get().strip()

        if not new_name:
            messagebox.showerror("Error", "You must enter a new deviceset name.")
            return

        chosen_pkgs = [pkg for pkg, d in self.package_data.items() if d["var"].get()]
        if not chosen_pkgs:
            messagebox.showerror("Error", "Select at least one package.")
            return

        valid_pkgs = {}
        skipped = []
        for pkg in chosen_pkgs:
            desc = self.package_data[pkg]["desc_var"].get().strip()
            lcsc = self.package_data[pkg]["lcsc_var"].get().strip()
            if desc == "" or lcsc == "":
                skipped.append(pkg)
            else:
                valid_pkgs[pkg] = {"desc": desc, "lcsc": lcsc}

        if not valid_pkgs:
            messagebox.showerror(
                "Error",
                "No selected packages have both DESCRIPTION and LCSC Part# filled. Nothing to save."
            )
            return

        try:
            # Re‐parse the library so we have the latest in-memory tree
            tree = XMLHandler.parse_library(lib_path)
            template_ds   = XMLHandler.find_template_deviceset(tree)
            template_devs = XMLHandler.extract_template_devices(template_ds)
            existing_ds   = XMLHandler.get_existing_deviceset(tree, new_name)

            if existing_ds:
                # Merge into the existing deviceset
                updated, added = XMLHandler.merge_into_deviceset(
                    existing_ds,
                    list(valid_pkgs.keys()),
                    template_devs,
                    valid_pkgs
                )
                XMLHandler.save_library(tree, lib_path)

                msg = f"Deviceset '{new_name}' already exists.\n→ {updated} updated, {added} added."
                if skipped:
                    msg += "\nSkipped (missing fields): " + ", ".join(skipped)
                messagebox.showinfo("Success", msg)

            else:
                # Create a brand new deviceset
                XMLHandler.create_new_deviceset(
                    tree,
                    template_ds,
                    new_name,
                    list(valid_pkgs.keys()),
                    valid_pkgs
                )
                XMLHandler.save_library(tree, lib_path)

                msg = f"Created deviceset '{new_name}' with {len(valid_pkgs)} package(s)."
                if skipped:
                    msg += "\nSkipped (missing fields): " + ", ".join(skipped)
                messagebox.showinfo("Success", msg)

            # ── Reload left panel so the new/updated deviceset appears immediately ──
            self.left_panel.load_devicesets(tree)

            # ── Clear right‐panel inputs for next addition ──
            self.device_name_var.set("")
            for pkg, data in self.package_data.items():
                data["var"].set(False)
                data["desc_var"].set("")
                data["lcsc_var"].set("")
                data["desc_entry"].configure(state="disabled")
                data["lcsc_entry"].configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add/update device:\n{e}")


if __name__ == "__main__":
    app = EagleLibraryGUI()
    app.mainloop()
