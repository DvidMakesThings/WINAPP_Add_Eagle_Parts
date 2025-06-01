import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from xml_handler import XMLHandler

class ExistingDevicesPanel(ctk.CTkScrollableFrame):
    """
    Left‐hand panel: shows all <deviceset> names as collapsible checkbuttons.
    Only one deviceset can be selected at a time. Selecting a new one will
    uncheck any previously selected deviceset.
    When the user checks a deviceset, we expand its package list and invoke
    on_select(deviceset_name). If it is unchecked, we call on_select(None).
    """

    def __init__(self, parent, width, height, on_select):
        """
        parent     - parent container
        width, height - size of this scrollable frame
        on_select  - callback(deviceset_name) when the user checks a deviceset;
                     or callback(None) when user unchecks the currently selected.
        """
        super().__init__(parent, width=width, height=height)
        self.on_select = on_select
        # will hold { ds_name: { "var": BooleanVar, "outer_frame": Frame, "inner_frame": Frame } }
        self.deviceset_widgets = {}

    def load_devicesets(self, tree):
        """
        1) Clears any existing entries.
        2) Finds all <deviceset> under library/devicesets.
        3) For each, create:
           • A checkbutton that both expands/collapses its package list
           • A hidden frame for its child <device> package names
        """
        # Clear any old widgets
        for child in self.winfo_children():
            child.destroy()
        self.deviceset_widgets.clear()

        root = tree.getroot()
        ds_parent = root.find("./drawing/library/devicesets")
        if ds_parent is None:
            messagebox.showerror("Error", "<devicesets> not found in library.")
            return

        for ds in ds_parent.findall("deviceset"):
            ds_name = ds.get("name", "<unnamed>")

            outer_frame = ctk.CTkFrame(self)
            outer_frame.pack(fill="x", pady=(2,2))

            var = tk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(
                outer_frame,
                text=ds_name,
                variable=var,
                command=lambda name=ds_name: self._on_deviceset_toggle(name)
            )
            chk.pack(anchor="w")

            inner_frame = ctk.CTkFrame(outer_frame)
            # Initially not packed (collapsed)

            # Populate inner_frame with this deviceset’s package names
            devs_parent = ds.find("devices")
            if devs_parent is not None:
                for dev in devs_parent.findall("device"):
                    pkg = dev.get("name")
                    if pkg:
                        lbl = ctk.CTkLabel(inner_frame, text=f"   └ {pkg}", anchor="w")
                        lbl.pack(fill="x", padx=(20,0), pady=(1,1))

            self.deviceset_widgets[ds_name] = {
                "var": var,
                "outer_frame": outer_frame,
                "inner_frame": inner_frame
            }

    def _on_deviceset_toggle(self, ds_name):
        """
        Called when the user checks/unchecks a deviceset:
         • If checked=True: uncheck every other deviceset, collapse them;
           then expand this one and call on_select(ds_name).
         • If checked=False: collapse this one and call on_select(None).
        """
        entry = self.deviceset_widgets.get(ds_name)
        if not entry:
            return

        # If user just checked this one:
        if entry["var"].get():
            # 1) Uncheck/collapse all others first
            for other_name, other_entry in self.deviceset_widgets.items():
                if other_name != ds_name:
                    if other_entry["var"].get():
                        other_entry["var"].set(False)
                        other_entry["inner_frame"].pack_forget()

            # 2) Expand this one
            entry["inner_frame"].pack(fill="x", padx=(0,10))
            # 3) Notify parent that this ds_name is selected
            self.on_select(ds_name)
        else:
            # User unchecked this same device: just collapse it
            entry["inner_frame"].pack_forget()
            # Notify parent that nothing is selected
            self.on_select(None)
