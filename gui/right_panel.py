import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from xml_handler import XMLHandler

class PackageSelectionPanel(ctk.CTkScrollableFrame):
    """
    A scrollable frame containing:
      • Row 0: header labels (“Select” | “Package” | “Description” | “LCSC Part#”)
      • Row 1…N: one package-row each: [Checkbox] [pkg name] [desc Entry] [lcsc Entry]
    """

    def __init__(self, parent, width, height, package_data, pkg_toggle_callback):
        super().__init__(parent, width=width, height=height)
        self.package_data        = package_data
        self.pkg_toggle_callback = pkg_toggle_callback

        # Configure exactly four columns:
        #   col 0 = 40px (checkbox)
        #   col 1 = 80px (package name)
        #   col 2 = weight=3 (Description)
        #   col 3 = weight=1 (LCSC Part#)
        self.grid_columnconfigure(0, weight=0, minsize=40)
        self.grid_columnconfigure(1, weight=0, minsize=80)
        self.grid_columnconfigure(2, weight=3, minsize=150)
        self.grid_columnconfigure(3, weight=1, minsize=100)

        # Draw header at row=0
        ctk.CTkLabel(self, text="Select").grid(
            row=0, column=0, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="Package").grid(
            row=0, column=1, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="Description").grid(
            row=0, column=2, sticky="w", padx=(5,5), pady=(5,2)
        )
        ctk.CTkLabel(self, text="LCSC Part#").grid(
            row=0, column=3, sticky="w", padx=(5,5), pady=(5,2)
        )

    def load_packages_from_template(self, tree):
        """
        1) Clears rows>0.
        2) Finds template deviceset (“DEVICE_NAME” or first).
        3) Extracts <device> children, sorted by @name.
        4) Builds one grid row per package under row=1:
           [Checkbox] [pkg name] [desc Entry] [lcsc Entry]
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

            # COLUMN 2: Description entry (disabled by default)
            desc_entry = ctk.CTkEntry(self, textvariable=desc_var)
            desc_entry.grid(row=row, column=2, padx=(5,5), pady=(2,2), sticky="we")
            desc_entry.configure(state="disabled")

            # COLUMN 3: LCSC Part# entry (disabled by default)
            lcsc_entry = ctk.CTkEntry(self, textvariable=lcsc_var)
            lcsc_entry.grid(row=row, column=3, padx=(5,5), pady=(2,2), sticky="we")
            lcsc_entry.configure(state="disabled")

            # Store references so EagleLibraryGUI can read/update them
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
        # else: silently succeed (no popup)

    def load_packages_from_deviceset(self, ds_element):
        """
        1) Clears rows>0.
        2) For each <device> under ds_element/devices (sorted by @name):
           – Read existing attributes: DESCRIPTION, LCSC_PART
           – Build one grid row per package under row=1:
             [Checkbox] [pkg name] [desc Entry] [lcsc Entry]
           – Pre-populate the Entry widgets with existing attribute values.
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

            # Fetch existing DESCRIPTION and LCSC_PART from <technologies>/<technology>/<attribute>
            existing_desc = ""
            existing_lcsc = ""
            tech = dev.find("./technologies/technology")
            if tech is not None:
                for attr in tech.findall("attribute"):
                    if attr.get("name") == "DESCRIPTION":
                        existing_desc = attr.get("value", "")
                    elif attr.get("name") == "LCSC_PART":
                        existing_lcsc = attr.get("value", "")

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

            # COLUMN 2: Description entry (populate existing_desc, disabled until checked)
            desc_entry = ctk.CTkEntry(self, textvariable=desc_var)
            desc_entry.grid(row=row, column=2, padx=(5,5), pady=(2,2), sticky="we")
            desc_entry.configure(state="disabled")

            # COLUMN 3: LCSC Part# entry (populate existing_lcsc, disabled until checked)
            lcsc_entry = ctk.CTkEntry(self, textvariable=lcsc_var)
            lcsc_entry.grid(row=row, column=3, padx=(5,5), pady=(2,2), sticky="we")
            lcsc_entry.configure(state="disabled")

            self.package_data[pkg_name] = {
                "var": bool_var,
                "desc_var": desc_var,
                "lcsc_var": lcsc_var,
                "desc_entry": desc_entry,
                "lcsc_entry": lcsc_entry,
            }

            row += 1

        if row == 1:
            messagebox.showinfo("Info", "No <device> entries found in that deviceset.")
        # else: silently succeed
