import customtkinter as ctk
from config import BUTTON_COLORS

class ActionButtonsFrame(ctk.CTkFrame):
    """
    The bottom area with two buttons:
      - “Add Device” (green)
      - “Quit” (red)
    """

    def __init__(self, parent, add_command, quit_command):
        super().__init__(parent)
        self.add_command = add_command
        self.quit_command = quit_command
        self._build()

    def _build(self):
        self.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            self,
            text="Add Device",
            command=self.add_command,
            fg_color=BUTTON_COLORS["add"]["fg"],
            hover_color=BUTTON_COLORS["add"]["hover"],
        ).pack(side="left", expand=True, padx=(0, 10))

        ctk.CTkButton(
            self,
            text="Quit",
            command=self.quit_command,
            fg_color=BUTTON_COLORS["quit"]["fg"],
            hover_color=BUTTON_COLORS["quit"]["hover"],
        ).pack(side="right", expand=True, padx=(10, 0))
