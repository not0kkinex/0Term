# gui/terminal_ui.py
import tkinter as tk
from tkinter import scrolledtext
import threading
import os

from terminal_core.executor import execute_command_logic
from utils.helpers import get_dynamic_prompt, get_completions, THEMES

class TerminalUI(tk.Tk):
    def __init__(self, theme_name="Dark"):
        super().__init__()
        self.title("0Term")
        self.geometry("800x500")
        
      
        self.current_theme = THEMES.get(theme_name, THEMES["Dark"])
        self.background_color = self.current_theme["bg"]
        self.text_color = self.current_theme["text"]
        self.error_color = self.current_theme["error"]
        self.cursor_color = self.current_theme["cursor"]
        self.font_family = "Consolas"
        self.font_size = 10
        
        self.configure(bg=self.background_color)

    
        self.command_history = []
        self.history_index = -1 

    
        self.terminal_area = scrolledtext.ScrolledText(
            self,
            bg=self.background_color,
            fg=self.text_color,
            insertbackground=self.cursor_color,
            font=(self.font_family, self.font_size),
            relief=tk.FLAT, border=0, padx=10, pady=10, wrap=tk.WORD
        )
        self.terminal_area.pack(fill=tk.BOTH, expand=True)
        

        self.terminal_area.bind("<Return>", self.handle_input)
        self.terminal_area.bind("<Tab>", self.handle_tab_completion) # Tab tamamlama
        self.terminal_area.bind("<Up>", self.navigate_history)       # Komut geçmişi
        self.terminal_area.bind("<Down>", self.navigate_history)     # Komut geçmişi
        self.terminal_area.bind("<Key>", self.prevent_deletion_before_prompt)
        self.terminal_area.bind("<Button-1>", self.restrict_cursor_placement)
        
    
        self.current_line_start_index = "1.0"
        self.print_initial_messages()

 

    def get_current_input_text(self):
        return self.terminal_area.get(self.current_line_start_index, "end-1c").strip()

    def print_text(self, text, color=None, new_line=True):
        tag_name = color if color else "default"
        if tag_name not in self.terminal_area.tag_names():
             self.terminal_area.tag_config(tag_name, foreground=color if color else self.text_color)
        
        self.terminal_area.insert(tk.END, text + ("\n" if new_line else ""), tag_name)
        self.terminal_area.see(tk.END)

    def print_prompt(self):
        prompt = get_dynamic_prompt()
        self.print_text(f"\n{prompt}", new_line=False)
        self.current_line_start_index = self.terminal_area.index("end-1c")

    def print_initial_messages(self):
        self.print_text("Gemini Terminal (Full Özellikli) Başlatıldı.")
        self.print_text("Kullanılabilir özellikler: Komut Geçmişi (Oklar), Tab Tamamlama, I/O Yönlendirme (>, >>).")
        self.print_prompt()

   
    
    def restrict_cursor_placement(self, event):
        clicked_index = self.terminal_area.index(f"@{event.x},{event.y}")
        if self.terminal_area.compare(clicked_index, "<", self.current_line_start_index):
            self.terminal_area.mark_set(tk.INSERT, self.current_line_start_index)
            return "break"

    def prevent_deletion_before_prompt(self, event):
        cursor_index = self.terminal_area.index(tk.INSERT)
        if event.keysym in ("BackSpace", "Delete"):
            if self.terminal_area.compare(cursor_index, "<=", self.current_line_start_index):
                 return "break"
        if event.keysym == "Left":
             if self.terminal_area.compare(cursor_index, "==", self.current_line_start_index):
                 return "break"

    def navigate_history(self, event):
        """Pressing the Up/Down keys scrolls through the command history."""
        
        self.terminal_area.mark_set(tk.INSERT, self.current_line_start_index)
        
        if event.keysym == "Up":
            self.history_index = max(0, self.history_index - 1)
        elif event.keysym == "Down":
            self.history_index = min(len(self.command_history), self.history_index + 1)

        self.terminal_area.delete(self.current_line_start_index, tk.END)

        if 0 <= self.history_index < len(self.command_history):
            cmd = self.command_history[self.history_index]
            self.terminal_area.insert(self.current_line_start_index, cmd)
            self.terminal_area.mark_set(tk.INSERT, self.current_line_start_index + f"+{len(cmd)}c")
        
        return "break"

    def handle_tab_completion(self, event):
        """Tab tuşuyla dosya/klasör tamamlama yapar."""
        current_input = self.get_current_input_text()
        
        if ' ' in current_input:
            cmd_parts = current_input.split(' ')
            partial_path = cmd_parts[-1]
        else:
            partial_path = current_input
        
        completions = get_completions(partial_path)
        
        self.terminal_area.delete(self.current_line_start_index, tk.END)

        if len(completions) == 1:
            full_path = completions[0]
            if os.path.isdir(full_path) and not full_path.endswith(os.sep):
                full_path += os.sep
            
            new_input = current_input[:-len(partial_path)] + full_path
            self.terminal_area.insert(self.current_line_start_index, new_input)
            
        elif len(completions) > 1:
            self.print_text("", new_line=True)
            display_names = [os.path.basename(c) for c in completions]
            self.print_text(" ".join(display_names))
            self.print_prompt()
            self.terminal_area.insert(self.current_line_start_index, current_input)
            
        else:
             self.terminal_area.insert(self.current_line_start_index, current_input) # Girdi aynı kalır
             
        self.terminal_area.see(tk.END)
        return "break"

    def handle_input(self, event):
        command = self.get_current_input_text()
        self.print_text("", new_line=True) 

        if not command:
            self.print_prompt()
            return "break"
        
   
        if command.strip() and (not self.command_history or self.command_history[-1] != command):
            self.command_history.append(command.strip())
        self.history_index = len(self.command_history) 

    
        if command.lower() in ("clear", "cls"):
            self.terminal_area.delete(1.0, tk.END)
            self.print_prompt()
            return "break"
        if command.lower() == "exit":
            self.quit()
            return "break"


        threading.Thread(target=self.run_command_and_display, args=(command,)).start()
        
        return "break"

    def run_command_and_display(self, command):
        """Processes the output from the executor and displays it on the screen."""
        
        result = execute_command_logic(command)
        
        if result["type"] == "success":
            if result.get("output"):
                self.print_text(result["output"].strip())
            if result.get("error"):
                self.print_text(result["error"].strip(), color=self.error_color)
        
        elif result["type"] == "error":
            self.print_text(result["message"], color=self.error_color)

        elif result["type"] == "tui_error":
            self.print_text(result["message"], color=self.error_color)
            self.print_text("This is an TUI app run this app at your default terminal app please.", color=self.error_color)
        
        self.print_prompt()
