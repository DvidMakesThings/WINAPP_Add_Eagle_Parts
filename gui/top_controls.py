import os
import tkinter as tk
import customtkinter as ctk
from config import BUTTON_COLORS

class TopControlsFrame(ctk.CTkFrame):
    """
    The top area containing:
      - Library path entry + Browse button
      - Load Packages button
      - New deviceset name entry
    """

    def __init__(self, parent, path_var, device_name_var, browse_command, load_command):
        super().__init__(parent)
        self.path_var = path_var
        self.device_name_var = device_name_var
        self.browse_command = browse_command
        self.load_command = load_command

        self._build()

        # Whenever path_var changes, toggle load button's state
        self.path_var.trace_add("write", self._on_path_change)

    def _build(self):
        self.pack(fill="x", padx=20, pady=(15, 5))

        # Label for path
        ctk.CTkLabel(self, text="Eagle Library (.lbr or .xml) Path:").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )

        # Entry for path
        ctk.CTkEntry(self, textvariable=self.path_var, width=300).grid(
            row=1, column=0, padx=(0, 5), pady=(5, 5), sticky="w"
        )

        # “Browse” button
        ctk.CTkButton(self, text="Browse", command=self.browse_command, width=80).grid(
            row=1, column=1, padx=(5, 5), pady=(5, 5)
        )

        # “Load Packages” (initially disabled)
        self.load_btn = ctk.CTkButton(
            self,
            text="Load Packages",
            command=self.load_command,
            fg_color=BUTTON_COLORS["load"]["fg"],
            hover_color=BUTTON_COLORS["load"]["hover"],
            state="disabled",
        )
        self.load_btn.grid(row=1, column=2, padx=(5, 0), pady=(5, 5))

        # Entry for new deviceset name
        ctk.CTkLabel(self, text="New Device Set Name:").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ctk.CTkEntry(self, textvariable=self.device_name_var, width=200).grid(
            row=2, column=1, columnspan=2, padx=(5, 0), pady=(10, 0), sticky="w"
        )

    def _on_path_change(self, *_):
        """
        Whenever path_var changes, check if it's a real file. If valid, enable Load; otherwise disable.
        """
        path = self.path_var.get().strip()
        if os.path.isfile(path):
            self.load_btn.configure(state="normal")
        else:
            self.load_btn.configure(state="disabled")
