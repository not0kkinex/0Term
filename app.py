# main.py
from gui.terminal_ui import TerminalUI

if __name__ == "__main__":
    # Deneyebileceğin temalar: "Dark", "Light", "Dracula"
    app = TerminalUI(theme_name="Dracula") 
    app.mainloop()
