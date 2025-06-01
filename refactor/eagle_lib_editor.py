import os
import xml.etree.ElementTree as ET
import copy
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# ------------------ CUSTOMTKINTER DARK MODE ------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class EagleLibraryEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Eagle Library Device Adder")
        self.geometry("650x650")
        self.resizable(True, True)

        # Path to the .lbr/.xml file
        self.path_var = tk.StringVar()
        self.path_var.trace_add('write', self._on_path_change)

        # New deviceset name (e.g. "0R")
        self.device_name_var = tk.StringVar()

        # Hold one row of data per package under DEVICE_NAME
        self.package_data = {}

        # Build UI
        self._build_top_controls()
        self._build_package_list_frame()
        self._build_action_buttons()

    def _build_top_controls(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=(15, 5))

        # File picker label
        ctk.CTkLabel(frame, text="Eagle Library (.lbr or .xml) Path:").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )

        # Entry for path
        ctk.CTkEntry(frame, textvariable=self.path_var, width=300).grid(
            row=1, column=0, padx=(0, 5), pady=(5, 5), sticky="w"
        )

        # Browse button
        ctk.CTkButton(frame, text="Browse", command=self._browse_file, width=80).grid(
            row=1, column=1, padx=(5, 5), pady=(5, 5)
        )

        # Load packages button: starts disabled
        self.load_btn = ctk.CTkButton(
            frame,
            text="Load Packages",
            command=self._load_packages,
            fg_color="green",
            hover_color="#006600",
            state="disabled"
        )
        self.load_btn.grid(row=1, column=2, padx=(5, 0), pady=(5, 5))

        # New deviceset name
        ctk.CTkLabel(frame, text="New Device Set Name:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ctk.CTkEntry(frame, textvariable=self.device_name_var, width=200).grid(
            row=2, column=1, columnspan=2, padx=(5, 0), pady=(10, 0), sticky="w"
        )

    def _on_path_change(self, *_):
        path = self.path_var.get().strip()
        if os.path.isfile(path):
            self.load_btn.configure(state="normal")
        else:
            self.load_btn.configure(state="disabled")

    def _build_package_list_frame(self):
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(header, text="Select", width=60).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Package", width=80).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(header, text="Description", width=200).grid(row=0, column=2, sticky="w")
        ctk.CTkLabel(header, text="LCSC Part#", width=120).grid(row=0, column=3, sticky="w")

        self.pkg_frame = ctk.CTkScrollableFrame(self, height=300, width=600)
        self.pkg_frame.pack(fill="both", padx=20, pady=(5, 10))

    def _build_action_buttons(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            frame,
            text="Add Device",
            command=self._on_add_device,
            fg_color="green",
            hover_color="#006600",
        ).pack(side="left", expand=True, padx=(0, 10))

        ctk.CTkButton(
            frame,
            text="Quit",
            command=self.destroy,
            fg_color="red",
            hover_color="#990000",
        ).pack(side="right", expand=True, padx=(10, 0))

    def _browse_file(self):
        fn = filedialog.askopenfilename(
            title="Select Eagle Library",
            filetypes=[("Eagle Library", "*.lbr"), ("XML Files", "*.xml"), ("All files", "*.*")],
        )
        if fn:
            self.path_var.set(fn)

    def _load_packages(self):
        lib_path = self.path_var.get().strip()
        if not os.path.isfile(lib_path):
            messagebox.showerror("Error", "Library file not found or invalid path.")
            return

        try:
            tree = ET.parse(lib_path)
            root = tree.getroot()
            devicesets = root.find("./drawing/library/devicesets")
            if devicesets is None:
                raise RuntimeError("<devicesets> not found in the library.")

            template = next(
                (ds for ds in devicesets.findall("deviceset") if ds.get("name") == "DEVICE_NAME"),
                None,
            )
            if template is None:
                raise RuntimeError("Template deviceset 'DEVICE_NAME' not found.")

            for child in self.pkg_frame.winfo_children():
                child.destroy()
            self.package_data.clear()

            devs_parent = template.find("devices")
            if devs_parent is None:
                raise RuntimeError("Template <devices> block is missing.")

            row = 0
            for dev in devs_parent.findall("device"):
                pkg_name = dev.get("name")
                bool_var = tk.BooleanVar(value=False)
                desc_var = tk.StringVar()
                lcsc_var = tk.StringVar()

                ctk.CTkCheckBox(
                    self.pkg_frame,
                    text="",
                    variable=bool_var,
                    command=lambda p=pkg_name: self._on_pkg_toggle(p),
                ).grid(row=row, column=0, padx=(0, 5), pady=2, sticky="w")

                ctk.CTkLabel(self.pkg_frame, text=pkg_name, width=80, anchor="w").grid(
                    row=row, column=1, padx=(0, 5), pady=2, sticky="w"
                )

                desc_entry = ctk.CTkEntry(self.pkg_frame, textvariable=desc_var, width=200)
                desc_entry.grid(row=row, column=2, padx=(0, 5), pady=2, sticky="w")
                desc_entry.configure(state="disabled")

                lcsc_entry = ctk.CTkEntry(self.pkg_frame, textvariable=lcsc_var, width=120)
                lcsc_entry.grid(row=row, column=3, padx=(0, 5), pady=2, sticky="w")
                lcsc_entry.configure(state="disabled")

                self.package_data[pkg_name] = {
                    "var": bool_var,
                    "desc_var": desc_var,
                    "lcsc_var": lcsc_var,
                    "desc_entry": desc_entry,
                    "lcsc_entry": lcsc_entry,
                }

                row += 1

            if row == 0:
                messagebox.showinfo("Info", "No <device> entries found under the DEVICE_NAME template.")
            else:
                # messagebox.showinfo("Info", f"Loaded {row} package(s) from template.")
                pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load packages:\n{e}")

    def _on_pkg_toggle(self, pkg_name):
        data = self.package_data[pkg_name]
        if data["var"].get():
            data["desc_entry"].configure(state="normal")
            data["lcsc_entry"].configure(state="normal")
        else:
            data["desc_entry"].configure(state="disabled")
            data["lcsc_entry"].configure(state="disabled")
            data["desc_var"].set("")
            data["lcsc_var"].set("")

    def _on_add_device(self):
        lib_path = self.path_var.get().strip()
        new_name = self.device_name_var.get().strip()

        if not os.path.isfile(lib_path):
            messagebox.showerror("Error", "Library file not found.")
            return
        if not new_name:
            messagebox.showerror("Error", "You must enter a new deviceset name.")
            return

        chosen_pkgs = [pkg for pkg, d in self.package_data.items() if d["var"].get()]
        if not chosen_pkgs:
            messagebox.showerror("Error", "Select at least one package to include.")
            return

        valid_pkgs = []
        skipped_pkgs = []
        for pkg in chosen_pkgs:
            desc = self.package_data[pkg]["desc_var"].get().strip()
            lcsc = self.package_data[pkg]["lcsc_var"].get().strip()
            if desc == "" or lcsc == "":
                skipped_pkgs.append(pkg)
            else:
                valid_pkgs.append(pkg)

        if not valid_pkgs:
            messagebox.showerror("Error", "No selected packages have both DESCRIPTION and LCSC Part# filled. Nothing to save.")
            return

        try:
            tree = ET.parse(lib_path)
            root = tree.getroot()
            devicesets = root.find("./drawing/library/devicesets")
            if devicesets is None:
                raise RuntimeError("<devicesets> not found in the library.")

            template = next(
                (ds for ds in devicesets.findall("deviceset") if ds.get("name") == "DEVICE_NAME"),
                None,
            )
            if template is None:
                raise RuntimeError("Template deviceset 'DEVICE_NAME' not found.")

            template_devs = {}
            devs_parent_template = template.find("devices")
            if devs_parent_template is None:
                raise RuntimeError("Template <devices> block is missing.")
            for dev in devs_parent_template.findall("device"):
                pkg = dev.get("name")
                template_devs[pkg] = copy.deepcopy(dev)

            existing_ds = next(
                (ds for ds in devicesets.findall("deviceset") if ds.get("name") == new_name),
                None,
            )

            if existing_ds is not None:
                devs_parent_existing = existing_ds.find("devices")
                if devs_parent_existing is None:
                    raise RuntimeError(f"Existing deviceset '{new_name}' missing <devices> block.")

                added = updated = 0
                for pkg in valid_pkgs:
                    found_dev = devs_parent_existing.find(f"device[@name='{pkg}']")
                    if found_dev is not None:
                        tech = found_dev.find("technologies/technology")
                        if tech is not None:
                            for attr in tech.findall("attribute"):
                                nm = attr.get("name")
                                if nm == "DESCRIPTION":
                                    val = self.package_data[pkg]["desc_var"].get().strip()
                                    attr.set("value", val)
                                elif nm == "LCSC_PART":
                                    val = self.package_data[pkg]["lcsc_var"].get().strip()
                                    attr.set("value", val)
                        updated += 1
                    else:
                        if pkg not in template_devs:
                            messagebox.showwarning("Warning", f"Package '{pkg}' not in template; skipping.")
                            continue
                        new_node = copy.deepcopy(template_devs[pkg])
                        tech = new_node.find("technologies/technology")
                        if tech is not None:
                            for attr in tech.findall("attribute"):
                                nm = attr.get("name")
                                if nm == "DESCRIPTION":
                                    val = self.package_data[pkg]["desc_var"].get().strip()
                                    attr.set("value", val)
                                elif nm == "LCSC_PART":
                                    val = self.package_data[pkg]["lcsc_var"].get().strip()
                                    attr.set("value", val)
                        devs_parent_existing.append(new_node)
                        added += 1

                tree.write(lib_path, encoding="utf-8", xml_declaration=True)
                msg = f"Deviceset '{new_name}' already exists.\n→ {updated} updated, {added} added."
                if skipped_pkgs:
                    msg += "\nSkipped (missing fields): " + ", ".join(skipped_pkgs)
                # messagebox.showinfo("Success", msg)

            else:
                new_ds = copy.deepcopy(template)
                new_ds.set("name", new_name)
                devs_parent_new = new_ds.find("devices")
                if devs_parent_new is None:
                    raise RuntimeError("Template malformed: missing <devices> block.")

                for dev in list(devs_parent_new.findall("device")):
                    pkg = dev.get("name")
                    if pkg not in valid_pkgs:
                        devs_parent_new.remove(dev)
                    else:
                        tech = dev.find("technologies/technology")
                        if tech is not None:
                            for attr in tech.findall("attribute"):
                                nm = attr.get("name")
                                if nm == "DESCRIPTION":
                                    val = self.package_data[pkg]["desc_var"].get().strip()
                                    attr.set("value", val)
                                elif nm == "LCSC_PART":
                                    val = self.package_data[pkg]["lcsc_var"].get().strip()
                                    attr.set("value", val)

                devicesets.append(new_ds)
                tree.write(lib_path, encoding="utf-8", xml_declaration=True)

                msg = f"Created new deviceset '{new_name}' with {len(valid_pkgs)} package(s)."
                if skipped_pkgs:
                    msg += "\nSkipped (missing fields): " + ", ".join(skipped_pkgs)
                # messagebox.showinfo("Success", msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add/update device:\n{e}")


if __name__ == "__main__":
    app = EagleLibraryEditor()
    app.mainloop()
