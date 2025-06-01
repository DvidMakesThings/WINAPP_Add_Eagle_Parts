# gui/top_controls.py

import os
import tkinter as tk
import customtkinter as ctk

class TopControlsFrame(ctk.CTkFrame):
    """
    A single‐row frame containing:
      • “Eagle Library (.lbr or .xml) Path:” label
      • entry bound to `path_var`
      • “Browse” button
      • “Load Packages” button (enabled only when path_var points to a real file)
      • “New Device Set Name:” label + entry (bound to `device_name_var`)
      • “Prefix:” label + entry (bound to `prefix_var`)
      • “Value:” label + entry (bound to `value_var`)
    """
    def __init__(
        self,
        parent,
        path_var:      tk.StringVar,
        device_name_var: tk.StringVar,
        prefix_var:    tk.StringVar,
        value_var:     tk.StringVar,
        browse_command,
        load_command
    ):
        super().__init__(parent)

        self.path_var            = path_var
        self.device_name_var     = device_name_var
        self.prefix_var          = prefix_var
        self.value_var           = value_var
        self.browse_command      = browse_command
        self.load_command        = load_command

        # Watch path_var so that Load button state can update automatically
        self.path_var.trace_add("write", self._on_path_change)

        # ─── Layout everything in a single row ───
        # We will place widgets into columns 0..10 on row=0.
        self.grid_columnconfigure(0, weight=0)   # path label
        self.grid_columnconfigure(1, weight=1)   # path entry (expandable)
        self.grid_columnconfigure(2, weight=0)   # browse button
        self.grid_columnconfigure(3, weight=0)   # load button
        self.grid_columnconfigure(4, weight=0)   # spacer
        self.grid_columnconfigure(5, weight=0)   # "New Device Set Name:" label
        self.grid_columnconfigure(6, weight=1)   # device_name entry
        self.grid_columnconfigure(7, weight=0)   # "Prefix:" label
        self.grid_columnconfigure(8, weight=0)   # prefix entry
        self.grid_columnconfigure(9, weight=0)   # "Value:" label
        self.grid_columnconfigure(10, weight=0)  # value entry

        # Row 0, Col 0: Label for path
        lbl_path = ctk.CTkLabel(self, text="Eagle Library (.lbr or .xml) Path:")
        lbl_path.grid(row=0, column=0, sticky="w", padx=(5, 5))

        # Row 0, Col 1: Entry for path_var
        ent_path = ctk.CTkEntry(self, textvariable=self.path_var, width=300)
        ent_path.grid(row=0, column=1, sticky="we", padx=(5, 5))

        # Row 0, Col 2: “Browse” button
        btn_browse = ctk.CTkButton(
            self,
            text="Browse",
            command=self._on_browse_clicked,
            width=80
        )
        btn_browse.grid(row=0, column=2, padx=(5, 5), pady=5)

        # Row 0, Col 3: “Load Packages” button (initially disabled)
        self.btn_load = ctk.CTkButton(
            self,
            text="Load Packages",
            command=self.load_command,
            fg_color="green",
            hover_color="#006600",
            state="disabled",
            width=100
        )
        self.btn_load.grid(row=0, column=3, padx=(5, 20), pady=5)

        # ─── “New Device Set Name:” (row=0, col=5)
        lbl_name = ctk.CTkLabel(self, text="New Device Set Name:")
        lbl_name.grid(row=0, column=5, sticky="w", padx=(0, 5))

        ent_name = ctk.CTkEntry(self, textvariable=self.device_name_var, width=120)
        ent_name.grid(row=0, column=6, sticky="w", padx=(0, 10))

        # ─── “Prefix:” (row=0, col=7)
        lbl_prefix = ctk.CTkLabel(self, text="Prefix:")
        lbl_prefix.grid(row=0, column=7, sticky="w", padx=(0, 5))

        ent_prefix = ctk.CTkEntry(self, textvariable=self.prefix_var, width=60)
        ent_prefix.grid(row=0, column=8, sticky="w", padx=(0, 10))

        # ─── “Value:” (row=0, col=9)
        lbl_value = ctk.CTkLabel(self, text="Value:")
        lbl_value.grid(row=0, column=9, sticky="w", padx=(0, 5))

        ent_value = ctk.CTkEntry(self, textvariable=self.value_var, width=80)
        ent_value.grid(row=0, column=10, sticky="w", padx=(0, 5))

        # Finally, pack this entire TopControlsFrame at the top
        self.pack(fill="x", padx=20, pady=(15, 5))

    def _on_browse_clicked(self):
        """
        Called when “Browse” is clicked: delegate to the supplied browse_command.
        After browse_command returns (and presumably sets path_var), we trigger _on_path_change.
        """
        self.browse_command()
        # Note: if browse_command sets path_var to a valid file, the trace on path_var will enable Load.

    def _on_path_change(self, *_):
        """
        Whenever path_var changes, check if it's a real file path.
        If yes, enable the Load button; otherwise keep it disabled.
        """
        current = self.path_var.get().strip()
        if os.path.isfile(current):
            self.btn_load.configure(state="normal")
        else:
            self.btn_load.configure(state="disabled")

    def set_load_button_state(self, enabled: bool):
        """
        Explicit helper to enable/disable the Load button from outside.
        """
        self.btn_load.configure(state="normal" if enabled else "disabled")
