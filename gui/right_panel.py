# gui/right_panel.py

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from xml_handler import XMLHandler

class PackageSelectionPanel(ctk.CTkScrollableFrame):
    """
    A scrollable frame containing:
      • Row 0: header labels (“Select” | “Package” | “Value” | “Description” | “LCSC Part#”)
      • Row 1…N: one package‐row each: [Checkbox] [pkg name] [value entry] [desc entry] [lcsc entry]
    """

    def __init__(self, parent, width, height, package_data, pkg_toggle_callback):
        super().__init__(parent, width=width, height=height)
        self.package_data       = package_data
        self.pkg_toggle_callback = pkg_toggle_callback

        # Configure columns: 
        # col 0 = 40px (checkbox), col 1 = 80px (pkg), col 2 = 80px (value),
        # col 3 = weight=3 (description), col 4 = weight=1 (LCSC)
        self.grid_columnconfigure(0, weight=0, minsize=40)
        self.grid_columnconfigure(1, weight=0, minsize=80)
        self.grid_columnconfigure(2, weight=0, minsize=80)
        self.grid_columnconfigure(3, weight=3, minsize=150)
        self.grid_columnconfigure(4, weight=1, minsize=100)

        # Draw header at row=0
        ctk.CTkLabel(self, text="Select").grid(
            row=0, column=0, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="Package").grid(
            row=0, column=1, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="Value").grid(
            row=0, column=2, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="Description").grid(
            row=0, column=3, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="LCSC Part#").grid(
            row=0, column=4, sticky="w", padx=(5,5), pady=(5,2)
        )

    def load_packages_from_template(self, tree):
        """
        1) Clears rows>0.
        2) Finds template deviceset (name="DEVICE_NAME") or first if missing.
        3) Extracts its <device> children, sorted by @name.
        4) Builds one grid row per package under row=1:
           [Checkbox] [pkg name] [value Entry] [desc Entry] [lcsc Entry]
        """
        # Clear any existing rows (row > 0)
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

        row = 1
        for dev in dev_list_sorted:
            pkg_name = dev.get("name", "")
            bool_var  = tk.BooleanVar(value=False)
            value_var = tk.StringVar()
            desc_var  = tk.StringVar()
            lcsc_var  = tk.StringVar()

            # COLUMN 0: Checkbox
            ctk.CTkCheckBox(
                self,
                text="",
                variable=bool_var,
                command=lambda p=pkg_name: self.pkg_toggle_callback(p)
            ).grid(row=row, column=0, padx=(5,5), pady=(2,2), sticky="w")

            # COLUMN 1: Package label
            ctk.CTkLabel(self, text=pkg_name, anchor="w").grid(
                row=row, column=1, padx=(5,5), pady=(2,2), sticky="w"
            )

            # COLUMN 2: Value entry (disabled by default)
            value_entry = ctk.CTkEntry(self, textvariable=value_var)
            value_entry.grid(row=row, column=2, padx=(5,5), pady=(2,2), sticky="we")
            value_entry.configure(state="disabled")

            # COLUMN 3: Description entry (disabled by default)
            desc_entry = ctk.CTkEntry(self, textvariable=desc_var)
            desc_entry.grid(row=row, column=3, padx=(5,5), pady=(2,2), sticky="we")
            desc_entry.configure(state="disabled")

            # COLUMN 4: LCSC Part# entry (disabled by default)
            lcsc_entry = ctk.CTkEntry(self, textvariable=lcsc_var)
            lcsc_entry.grid(row=row, column=4, padx=(5,5), pady=(2,2), sticky="we")
            lcsc_entry.configure(state="disabled")

            self.package_data[pkg_name] = {
                "var": bool_var,
                "value_var": value_var,
                "desc_var": desc_var,
                "lcsc_var": lcsc_var,
                "value_entry": value_entry,
                "desc_entry": desc_entry,
                "lcsc_entry": lcsc_entry,
            }

            row += 1

        if row == 1:
            messagebox.showinfo("Info", "No <device> entries found in the template deviceset.")
        else:
            # messagebox.showinfo("Info", f"Loaded {row - 1} package(s).")
            pass

    def load_packages_from_deviceset(self, ds_element):
        """
        1) Clears rows>0.
        2) For each <device> under ds_element/devices (sorted by @name):
           – Read existing attributes: VALUE, DESCRIPTION, LCSC_PART (may be missing).
           – Build one grid row per package under row=1:
             [Checkbox] [pkg name] [value Entry] [desc Entry] [lcsc Entry]
           – Pre‐populate the Entry widgets with existing attribute values (or blank).
        """
        # Clear old rows
        for child in self.winfo_children():
            info = child.grid_info()
            r = info.get("row", None)
            if r is not None and r > 0:
                child.destroy()
        self.package_data.clear()

        if ds_element is None:
            # Nothing to load
            return

        devs_parent = ds_element.find("devices")
        if devs_parent is None:
            messagebox.showinfo("Info", f"Deviceset '{ds_element.get('name')}' has no <devices> section.")
            return

        dev_list = devs_parent.findall("device")
        dev_list_sorted = sorted(dev_list, key=lambda d: d.get("name") or "")

        row = 1
        for dev in dev_list_sorted:
            pkg_name = dev.get("name", "")
            bool_var  = tk.BooleanVar(value=False)

            # Fetch existing attributes in <technology>
            tech = dev.find("./technologies/technology")
            existing_value = ""
            existing_desc  = ""
            existing_lcsc  = ""
            if tech is not None:
                for attr in tech.findall("attribute"):
                    attr_name = attr.get("name")
                    if attr_name == "VALUE":
                        existing_value = attr.get("value", "")
                    elif attr_name == "DESCRIPTION":
                        existing_desc = attr.get("value", "")
                    elif attr_name == "LCSC_PART":
                        existing_lcsc = attr.get("value", "")

            value_var = tk.StringVar(value=existing_value)
            desc_var  = tk.StringVar(value=existing_desc)
            lcsc_var  = tk.StringVar(value=existing_lcsc)

            # COLUMN 0: Checkbox
            ctk.CTkCheckBox(
                self,
                text="",
                variable=bool_var,
                command=lambda p=pkg_name: self.pkg_toggle_callback(p)
            ).grid(row=row, column=0, padx=(5,5), pady=(2,2), sticky="w")

            # COLUMN 1: Package label
            ctk.CTkLabel(self, text=pkg_name, anchor="w").grid(
                row=row, column=1, padx=(5,5), pady=(2,2), sticky="w"
            )

            # COLUMN 2: Value entry (populate existing_value, disabled until checked)
            value_entry = ctk.CTkEntry(self, textvariable=value_var)
            value_entry.grid(row=row, column=2, padx=(5,5), pady=(2,2), sticky="we")
            value_entry.configure(state="disabled")

            # COLUMN 3: Description entry (populate existing_desc)
            desc_entry = ctk.CTkEntry(self, textvariable=desc_var)
            desc_entry.grid(row=row, column=3, padx=(5,5), pady=(2,2), sticky="we")
            desc_entry.configure(state="disabled")

            # COLUMN 4: LCSC Part# entry (populate existing_lcsc)
            lcsc_entry = ctk.CTkEntry(self, textvariable=lcsc_var)
            lcsc_entry.grid(row=row, column=4, padx=(5,5), pady=(2,2), sticky="we")
            lcsc_entry.configure(state="disabled")

            self.package_data[pkg_name] = {
                "var": bool_var,
                "value_var": value_var,
                "desc_var": desc_var,
                "lcsc_var": lcsc_var,
                "value_entry": value_entry,
                "desc_entry": desc_entry,
                "lcsc_entry": lcsc_entry,
            }

            row += 1

        if row == 1:
            messagebox.showinfo("Info", "No <device> entries found in that deviceset.")
        else:
            # messagebox.showinfo("Info", f"Loaded {row - 1} existing package(s).")
            pass
