import customtkinter as ctk
from gui.app import EagleLibraryGUI

if __name__ == "__main__":
    # Optional: set a default appearance/theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = EagleLibraryGUI()
    app.mainloop()
