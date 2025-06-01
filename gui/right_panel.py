# gui/right_panel.py

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from xml_handler import XMLHandler

class PackageSelectionPanel(ctk.CTkScrollableFrame):
    """
    A scrollable frame containing:
      • Row 0: header labels (“Select”, “Package”, “Description”, “LCSC Part#”)
      • Row 1…N: one package‐row each, with [Checkbox] [pkg label] [desc entry] [lcsc entry]
    All columns share identical grid_columnconfigure settings so the header and rows stay aligned:
      – Col 0 (Select): fixed 40px
      – Col 1 (Package): fixed 80px
      – Col 2 (Description): weight=3 (largest)
      – Col 3 (LCSC Part#): weight=1 (smaller)
    """

    def __init__(self, parent, width, height, package_data, pkg_toggle_callback):
        super().__init__(parent, width=width, height=height)
        self.package_data = package_data
        self.pkg_toggle_callback = pkg_toggle_callback

        # ── Configure columns for the header+rows ──
        self.grid_columnconfigure(0, weight=0, minsize=40)   # Checkbox column
        self.grid_columnconfigure(1, weight=0, minsize=80)   # Package name column
        self.grid_columnconfigure(2, weight=3, minsize=150)  # Description column
        self.grid_columnconfigure(3, weight=1, minsize=100)  # LCSC Part# column

        # ── Draw header at row=0 ──
        ctk.CTkLabel(self, text="Select").grid(
            row=0, column=0, sticky="w", padx=(5, 5), pady=(5, 2)
        )
        ctk.CTkLabel(self, text="Package").grid(
            row=0, column=1, sticky="w", padx=(5, 5), pady=(5, 2)
        )
        ctk.CTkLabel(self, text="Description").grid(
            row=0, column=2, sticky="w", padx=(5, 5), pady=(5, 2)
        )
        ctk.CTkLabel(self, text="LCSC Part#").grid(
            row=0, column=3, sticky="w", padx=(5, 5), pady=(5, 2)
        )

    def load_packages_from_template(self, tree):
        """
        1) Find the template <deviceset>.
        2) Extract and sort its <device> children by @name.
        3) Insert each package as one grid row, starting at row=1.
        """
        # ── Clear any existing rows (row>0) ──
        for child in self.winfo_children():
            info = child.grid_info()
            r = info.get("row", None)
            if r is not None and r > 0:
                child.destroy()
        self.package_data.clear()

        try:
            template_ds = XMLHandler.find_template_deviceset(tree)
        except Exception as e:
            messagebox.showerror("Error", f"Could not find template deviceset:\n{e}")
            return

        devs_parent = template_ds.find("devices")
        if devs_parent is None:
            messagebox.showinfo("Info", "Template deviceset has no <devices> section.")
            return

        dev_list = devs_parent.findall("device")
        dev_list_sorted = sorted(dev_list, key=lambda d: d.get("name") or "")

        # Start inserting rows at grid-row = 1 (row 0 is the header)
        row = 1
        for dev in dev_list_sorted:
            pkg_name = dev.get("name", "")
            bool_var = tk.BooleanVar(value=False)
            desc_var = tk.StringVar()
            lcsc_var = tk.StringVar()

            # COLUMN 0: Checkbox
            ctk.CTkCheckBox(
                self,
                text="",
                variable=bool_var,
                command=lambda p=pkg_name: self.pkg_toggle_callback(p)
            ).grid(
                row=row, column=0, padx=(5, 5), pady=(2, 2), sticky="w"
            )

            # COLUMN 1: Package label
            ctk.CTkLabel(
                self,
                text=pkg_name,
                anchor="w"
            ).grid(
                row=row, column=1, padx=(5, 5), pady=(2, 2), sticky="w"
            )

            # COLUMN 2: Description entry (disabled until checked)
            desc_entry = ctk.CTkEntry(self, textvariable=desc_var)
            desc_entry.grid(
                row=row, column=2, padx=(5, 5), pady=(2, 2), sticky="we"
            )
            desc_entry.configure(state="disabled")

            # COLUMN 3: LCSC Part# entry (disabled until checked)
            lcsc_entry = ctk.CTkEntry(self, textvariable=lcsc_var)
            lcsc_entry.grid(
                row=row, column=3, padx=(5, 5), pady=(2, 2), sticky="we"
            )
            lcsc_entry.configure(state="disabled")

            # Store references so the main GUI can enable/disable them later
            self.package_data[pkg_name] = {
                "var": bool_var,
                "desc_var": desc_var,
                "lcsc_var": lcsc_var,
                "desc_entry": desc_entry,
                "lcsc_entry": lcsc_entry,
            }

            row += 1

        if row == 1:
            messagebox.showinfo("Info", "No <device> entries found in the template deviceset.")
        else:
            # messagebox.showinfo("Info", f"Loaded {row - 1} package(s).")
            pass
