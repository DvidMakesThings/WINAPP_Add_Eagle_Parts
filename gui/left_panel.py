import customtkinter as ctk
import tkinter as tk

class ExistingDevicesPanel(ctk.CTkScrollableFrame):
    """
    A scrollable panel that lists all existing <deviceset> names in a vertical,
    collapsible “folder‐style” view. Each deviceset has a CheckBox; when checked,
    its package names appear indented underneath.
    """

    def __init__(self, parent, width, height):
        super().__init__(parent, width=width, height=height)
        self.deviceset_widgets = {}  # name → { "var":BooleanVar, "outer_frame":Frame, "inner_frame":Frame }

    def load_devicesets(self, tree):
        """
        Clear any existing widgets, then populate with the content of:
         /drawing/library/devicesets/deviceset
        Each deviceset→new CheckBox. Its packages go into an inner frame under it.
        """
        # Clear old
        for child in self.winfo_children():
            child.destroy()
        self.deviceset_widgets.clear()

        devicesets_node = tree.getroot().find("./drawing/library/devicesets")
        if devicesets_node is None:
            return  # nothing to show

        for ds in devicesets_node.findall("deviceset"):
            ds_name = ds.get("name", "<unnamed>")

            outer_frame = ctk.CTkFrame(self)
            outer_frame.pack(fill="x", pady=(2, 2))

            var = tk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(
                outer_frame,
                text=ds_name,
                variable=var,
                command=lambda name=ds_name: self._toggle(name)
            )
            chk.pack(anchor="w")

            inner_frame = ctk.CTkFrame(outer_frame)

            devs = ds.find("devices")
            if devs is not None:
                for dev in devs.findall("device"):
                    pkg = dev.get("package")
                    if pkg:
                        lbl = ctk.CTkLabel(inner_frame, text=f"   └ {pkg}", anchor="w")
                        lbl.pack(fill="x", padx=(20, 0), pady=(0, 2))

            self.deviceset_widgets[ds_name] = {
                "var": var,
                "outer_frame": outer_frame,
                "inner_frame": inner_frame
            }

    def _toggle(self, ds_name):
        """
        When a deviceset CheckBox is toggled, show/hide its inner_frame (package names).
        """
        entry = self.deviceset_widgets.get(ds_name)
        if not entry:
            return
        if entry["var"].get():
            entry["inner_frame"].pack(fill="x", padx=(0, 10))
        else:
            entry["inner_frame"].pack_forget()
