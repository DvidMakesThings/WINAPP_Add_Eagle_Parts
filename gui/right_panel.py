import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from xml_handler import XMLHandler

class PackageSelectionPanel(ctk.CTkScrollableFrame):
    """
    A scrollable frame containing:
      • Row 0: header labels (“Select” | “Package” | “Description” | “LCSC Part#”)
      • Row 1…N: one package‐row each: [Checkbox] [pkg name] [desc entry] [lcsc entry]
    """

    def __init__(self, parent, width, height, package_data, pkg_toggle_callback,
                 package_list_provider):
        """
        package_list_provider: callable(tree) -> list of all package names
        """
        super().__init__(parent, width=width, height=height)
        self.package_data        = package_data
        self.pkg_toggle_callback = pkg_toggle_callback
        self.pkgs_provider       = package_list_provider

        # Configure columns:
        # col 0 = 40px (checkbox), col 1 = 80px (pkg),
        # col 2 = weight=3 (description), col 3 = weight=1 (LCSC)
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

    def load_all_packages(self, tree):
        """
        1) Clears rows > 0.
        2) Uses package_list_provider(tree) to get ALL package names under <packages>.
        3) Builds one grid row per package under row=1:
           [Checkbox] [pkg name] [desc Entry] [lcsc Entry]
        """
        # Clear any existing rows (row > 0)
        for child in self.winfo_children():
            info = child.grid_info()
            r = info.get("row", None)
            if r is not None and r > 0:
                child.destroy()
        self.package_data.clear()

        packages = []
        if tree is not None:
            packages = self.pkgs_provider(tree)

        row = 1
        for pkg_name in packages:
            bool_var = tk.BooleanVar(value=False)
            desc_var = tk.StringVar()
            lcsc_var = tk.StringVar()

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

            # Store references
            self.package_data[pkg_name] = {
                "var": bool_var,
                "desc_var": desc_var,
                "lcsc_var": lcsc_var,
                "desc_entry": desc_entry,
                "lcsc_entry": lcsc_entry,
            }
            row += 1

        # If no packages were found, do nothing special.
        # (Optional: show info if row == 1)
        # if row == 1:
        #     messagebox.showinfo("Info", "No packages found in library.")

    def load_packages_from_deviceset(self, ds_element):
        """
        Show _all_ packages in the right panel, but pre‐fill DESCRIPTION and LCSC only
        for those packages that already appear under ds_element/devices.

        Steps:
          1) Clear rows > 0.
          2) Get a list of _all_ package names (via XMLHandler.list_packages).
          3) Build one row per package (same as load_all_packages), but if that
             package name already exists as <device> in ds_element, fill in its
             DESCRIPTION / LCSC from the XML.
        """
        # Clear old rows
        for child in self.winfo_children():
            info = child.grid_info()
            r = info.get("row", None)
            if r is not None and r > 0:
                child.destroy()
        self.package_data.clear()

        # If no deviceset selected, do nothing
        if ds_element is None:
            return

        # 1) Build a quick lookup of packages already in this deviceset:
        existing_map = {}
        devs_parent = ds_element.find("devices")
        if devs_parent is not None:
            for dev in devs_parent.findall("device"):
                pkg_name = dev.get("name", "")
                # If <attribute name="DESCRIPTION"> and <attribute name="LCSC_PART"> exist, remember them
                tech = dev.find("./technologies/technology")
                existing_desc = ""
                existing_lcsc = ""
                if tech is not None:
                    for attr in tech.findall("attribute"):
                        if attr.get("name") == "DESCRIPTION":
                            existing_desc = attr.get("value", "")
                        elif attr.get("name") == "LCSC_PART":
                            existing_lcsc = attr.get("value", "")
                existing_map[pkg_name] = {
                    "DESCRIPTION": existing_desc,
                    "LCSC_PART": existing_lcsc
                }

        # 2) Get a sorted list of all packages in the library
        #    (We need the tree. We can grab it from the first <device> or pass it in—
        #     but the easiest is to call self.pkgs_provider on the original tree.)
        #    The calling code always did: package_list_provider = XMLHandler.list_packages
        packages = []
        try:
            # self.master is the parent frame, but your app stored the tree in a variable.
            # In practice, you can store the tree in this widget when load_all_packages was called.
            # For now, we assume `self.tree` was set by load_all_packages; if not, pass it in.
            packages = self.pkgs_provider(self.tree)
        except Exception:
            # Fallback: if we didn’t preserve the tree in this widget, just show existing_map keys
            packages = sorted(existing_map.keys(), key=lambda s: s.lower())

        row = 1
        for pkg_name in packages:
            bool_var = tk.BooleanVar(value=False)
            # Pre‐fill DESCRIPTION / LCSC from existing_map, or blank if not found
            existing_desc = existing_map.get(pkg_name, {}).get("DESCRIPTION", "")
            existing_lcsc = existing_map.get(pkg_name, {}).get("LCSC_PART", "")

            desc_var = tk.StringVar(value=existing_desc)
            lcsc_var = tk.StringVar(value=existing_lcsc)

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

            # COLUMN 2: Description entry
            desc_entry = ctk.CTkEntry(self, textvariable=desc_var)
            desc_entry.grid(row=row, column=2, padx=(5,5), pady=(2,2), sticky="we")
            # Disable by default; only enable when user checks the box
            desc_entry.configure(state="disabled")

            # COLUMN 3: LCSC Part# entry
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
