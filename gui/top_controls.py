import os
import tkinter as tk
import customtkinter as ctk
import xml.etree.ElementTree as ET                   # ← add this line
from config import BUTTON_COLORS

class TopControlsFrame(ctk.CTkFrame):
    """
    The top‐row area containing:
      - Library path entry + Browse button + Load button
      - New deviceset name entry
      - Prefix entry
      - Global Value entry
      - Symbol dropdown (combobox)
    """

    def __init__(self,
                 parent,
                 path_var,
                 device_name_var,
                 prefix_var,
                 value_var,
                 symbol_var,
                 browse_command,
                 load_command,
                 symbol_list_provider):
        """
        symbol_var:          a StringVar() where the chosen symbol will be stored
        symbol_list_provider: a callable that returns the list of symbols (strings)
        """
        super().__init__(parent)
        self.path_var         = path_var
        self.device_name_var  = device_name_var
        self.prefix_var       = prefix_var
        self.value_var        = value_var
        self.symbol_var       = symbol_var
        self.browse_command   = browse_command
        self.load_command     = load_command
        self.symbol_provider  = symbol_list_provider

        self._build()
        self.path_var.trace_add("write", self._on_path_change)

    def _build(self):
        self.pack(fill="x", padx=20, pady=(15, 5))

        # ─── Row 0: Library path + Browse + Load ───
        ctk.CTkLabel(self, text="Eagle Library (.lbr or .xml) Path:").grid(
            row=0, column=0, columnspan=4, sticky="w"
        )

        ctk.CTkEntry(self, textvariable=self.path_var, width=300).grid(
            row=1, column=0, padx=(0, 5), pady=(5, 5), sticky="w"
        )
        ctk.CTkButton(self, text="Browse", command=self.browse_command, width=80).grid(
            row=1, column=1, padx=(5, 5), pady=(5, 5)
        )
        # “Load” button
        self.load_btn = ctk.CTkButton(
            self,
            text="Load",
            command=self.load_command,
            fg_color=BUTTON_COLORS["load"]["fg"],
            hover_color=BUTTON_COLORS["load"]["hover"],
            state="disabled",
        )
        self.load_btn.grid(row=1, column=2, padx=(5, 5), pady=(5, 5))

        # ─── Row 2: DeviceSet Name, Prefix, Value, Symbol ───
        ctk.CTkLabel(self, text="Device Set Name:").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ctk.CTkEntry(self, textvariable=self.device_name_var, width=200).grid(
            row=2, column=1, padx=(5, 5), pady=(10, 0), sticky="w"
        )

        ctk.CTkLabel(self, text="Prefix:").grid(
            row=2, column=2, sticky="w", pady=(10, 0)
        )
        ctk.CTkEntry(self, textvariable=self.prefix_var, width=80).grid(
            row=2, column=3, padx=(5, 5), pady=(10, 0), sticky="w"
        )

        ctk.CTkLabel(self, text="Value:").grid(
            row=2, column=4, sticky="w", pady=(10, 0)
        )
        ctk.CTkEntry(self, textvariable=self.value_var, width=120).grid(
            row=2, column=5, padx=(5, 5), pady=(10, 0), sticky="w"
        )

        ctk.CTkLabel(self, text="Symbol:").grid(
            row=2, column=6, sticky="w", pady=(10, 0)
        )
        # We will create a simple dropdown (CTkOptionMenu)
        self.symbol_menu = ctk.CTkOptionMenu(
            self,
            values=[],
            variable=self.symbol_var,
            width=140
        )
        self.symbol_menu.grid(
            row=2, column=7, padx=(5, 0), pady=(10, 0), sticky="w"
        )

    def _on_path_change(self, *_):
        """
        Whenever path_var changes:
         - If it's a real file, enable the Load button.
         - Attempt to parse the file immediately to populate the Symbol dropdown.
         - If parsing fails, clear the dropdown.
        """
        path = self.path_var.get().strip()
        if os.path.isfile(path):
            self.load_btn.configure(state="normal")
            try:
                tree = ET.parse(path)
                symbols = self.symbol_provider(tree)
                self.symbol_menu.configure(values=symbols)
                self.symbol_var.set("")  # clear any prior selection
            except Exception:
                # If parsing fails, leave dropdown empty
                self.symbol_menu.configure(values=[])
                self.symbol_var.set("")
        else:
            self.load_btn.configure(state="disabled")
            self.symbol_menu.configure(values=[])
            self.symbol_var.set("")
