# gui/terminal_ui.py
"""
0Term - GUI Terminal Panel with PTY support (English).

Features:
- PTY-backed TUI applications (nano, vim, top, htop, etc.) on Unix-like systems.
- Non-TUI commands executed via terminal_core.executor.execute_command_logic.
- Thread-safe updates to the Tkinter Text widget using .after.
- Command history (Up/Down), Tab completion, prompt protection (prevent editing before prompt).
- All user-visible messages are in English.

Save as gui/terminal_ui.py and run via your app entry (e.g. python app.py).
"""
import os
import sys
import threading
import pty
import select
import tkinter as tk
from tkinter import scrolledtext

from terminal_core.executor import execute_command_logic
from utils.helpers import get_dynamic_prompt, get_completions, THEMES

# TUI-capable programs (will be launched inside a PTY)
TUI_APPS = ["nano", "vi", "vim", "micro", "top", "htop", "less", "man"]

class TerminalUI(tk.Tk):
    def __init__(self, theme_name: str = "Dark"):
        super().__init__()
        self.title("0Term")
        self.geometry("900x600")

        # --- Theme ---
        self.current_theme = THEMES.get(theme_name, THEMES["Dark"])
        self.background_color = self.current_theme["bg"]
        self.text_color = self.current_theme["text"]
        self.error_color = self.current_theme["error"]
        self.cursor_color = self.current_theme["cursor"]

        self.font_family = "Consolas" if sys.platform.startswith("win") else "Monospace"
        self.font_size = 11

        self.configure(bg=self.background_color)

        # --- State ---
        self.command_history = []
        self.history_index = None  # None means not currently browsing history
        self.current_line_start_index = "1.0"

        # --- Terminal Text Widget ---
        self.terminal_area = scrolledtext.ScrolledText(
            self,
            bg=self.background_color,
            fg=self.text_color,
            insertbackground=self.cursor_color,
            font=(self.font_family, self.font_size),
            relief=tk.FLAT,
            border=0,
            padx=8,
            pady=8,
            wrap=tk.WORD
        )
        self.terminal_area.pack(fill=tk.BOTH, expand=True)

        # Initialize tags
        self._init_tags()

        # --- Bindings ---
        # Return "break" for keys we handle so default widget behavior doesn't interfere
        self.terminal_area.bind("<Return>", self.handle_input)
        self.terminal_area.bind("<Tab>", self.handle_tab_completion)
        self.terminal_area.bind("<Up>", self.navigate_history)
        self.terminal_area.bind("<Down>", self.navigate_history)
        self.terminal_area.bind("<Key>", self.prevent_deletion_before_prompt)
        self.terminal_area.bind("<Button-1>", self.restrict_cursor_placement)

        # Welcome and prompt
        self.print_initial_messages()

    # ---------------------------
    # Tag/Color helpers
    # ---------------------------
    def _init_tags(self):
        # default
        if "default" not in self.terminal_area.tag_names():
            self.terminal_area.tag_config("default", foreground=self.text_color)
        # error
        if "error" not in self.terminal_area.tag_names():
            self.terminal_area.tag_config("error", foreground=self.error_color)
        # info (optional)
        if "info" not in self.terminal_area.tag_names():
            self.terminal_area.tag_config("info", foreground=self.text_color)

    # ---------------------------
    # Thread-safe append functions
    # ---------------------------
    def _append_text_safe(self, text: str, tag: str = "default", newline: bool = True):
        """
        Schedule appending text on the main thread. Keep widget in NORMAL state so user can type.
        """
        if newline and text and not text.endswith("\n"):
            text = text + "\n"
        # Schedule insertion on main thread
        self.terminal_area.after(0, lambda: self._append_text_now(text, tag))

    def _append_text_now(self, text: str, tag: str = "default"):
        """
        Insert text at the end of the Text widget. Runs on main thread.
        """
        if tag not in self.terminal_area.tag_names():
            # fallback if someone passed a custom tag
            self.terminal_area.tag_config(tag, foreground=(self.error_color if tag == "error" else self.text_color))

        # Insert and keep view scrolled to end.
        try:
            # Ensure widget is writable (we keep it writable by design)
            self.terminal_area.insert(tk.END, text, tag)
            self.terminal_area.see(tk.END)
        except tk.TclError:
            # In very rare cases, widget may be destroyed — ignore
            pass

    # ---------------------------
    # Printing and prompt
    # ---------------------------
    def print_text(self, text: str, color: str = None, new_line: bool = True):
        """
        Public printing method. color: None or "error" (other tags allowed).
        """
        tag_name = "default" if not color else color
        self._append_text_safe(text, tag_name, newline=new_line)

    def print_prompt(self):
        """
        Print prompt and update current_line_start_index on the GUI thread.
        """
        prompt = get_dynamic_prompt()
        # Add newline + prompt (no automatic newline after prompt)
        self.print_text("\n" + prompt, new_line=False)
        # Update `current_line_start_index` after prompt is inserted
        self.terminal_area.after(0, self._update_current_line_start)

    def _update_current_line_start(self):
        """
        Called on the main thread to set where the user's input starts.
        Also set the insertion cursor to that position.
        """
        try:
            self.current_line_start_index = self.terminal_area.index("end-1c")
            self.terminal_area.mark_set(tk.INSERT, self.current_line_start_index)
        except tk.TclError:
            pass

    def print_initial_messages(self):
        self.print_text("0Term PTY Terminal started.", new_line=True)
        self.print_text("Features: command history (Up/Down), tab completion, PTY-supported TUI apps.", new_line=True)
        self.print_prompt()

    # ---------------------------
    # Input helpers
    # ---------------------------
    def get_current_input_text(self) -> str:
        """
        Return the text typed by the user after the current prompt (no trailing newline).
        """
        try:
            raw = self.terminal_area.get(self.current_line_start_index, "end-1c")
            return raw.rstrip("\n")
        except tk.TclError:
            return ""

    def restrict_cursor_placement(self, event):
        """
        Prevent placing the cursor before the prompt by mouse click.
        """
        try:
            clicked_index = self.terminal_area.index(f"@{event.x},{event.y}")
            if self.terminal_area.compare(clicked_index, "<", self.current_line_start_index):
                self.terminal_area.mark_set(tk.INSERT, self.current_line_start_index)
                return "break"
        except tk.TclError:
            pass

    def prevent_deletion_before_prompt(self, event):
        """
        Prevent Backspace/Delete/Left from moving cursor before prompt.
        Allow typing normally.
        """
        try:
            cursor_index = self.terminal_area.index(tk.INSERT)
        except tk.TclError:
            return None

        keys_to_block = ("BackSpace", "Delete", "Left")
        if event.keysym in keys_to_block:
            if self.terminal_area.compare(cursor_index, "<=", self.current_line_start_index):
                return "break"
        return None

    # ---------------------------
    # History navigation
    # ---------------------------
    def navigate_history(self, event):
        """
        Up/Down navigate through history. Keep history_index None when not browsing.
        """
        # Prevent default behavior
        self.terminal_area.mark_set(tk.INSERT, self.current_line_start_index)

        if not self.command_history:
            return "break"

        # initialize history_index if needed
        if self.history_index is None:
            self.history_index = len(self.command_history)

        if event.keysym == "Up":
            if self.history_index > 0:
                self.history_index -= 1
        elif event.keysym == "Down":
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
            else:
                # beyond last => clear input
                self.history_index = len(self.command_history)
                self.terminal_area.delete(self.current_line_start_index, tk.END)
                return "break"

        # Ensure bounds
        if self.history_index < 0:
            self.history_index = 0
        if self.history_index > len(self.command_history):
            self.history_index = len(self.command_history)

        # Replace current input with history item (if any)
        self.terminal_area.delete(self.current_line_start_index, tk.END)
        if 0 <= self.history_index < len(self.command_history):
            cmd = self.command_history[self.history_index]
            self.terminal_area.insert(self.current_line_start_index, cmd)
            # place cursor after inserted command
            self.terminal_area.mark_set(tk.INSERT, f"{self.current_line_start_index}+{len(cmd)}c")

        return "break"

    # ---------------------------
    # Tab completion
    # ---------------------------
    def handle_tab_completion(self, event):
        """
        File/directory auto-completion using get_completions(partial_path).
        """
        current_input = self.get_current_input_text()
        if ' ' in current_input:
            parts = current_input.split(' ')
            partial_path = parts[-1]
        else:
            partial_path = current_input

        try:
            completions = get_completions(partial_path)
        except Exception:
            completions = []

        # Remove current partial input
        self.terminal_area.delete(self.current_line_start_index, tk.END)

        if len(completions) == 1:
            full_path = completions[0]
            if os.path.isdir(full_path) and not full_path.endswith(os.sep):
                full_path += os.sep
            if ' ' in current_input:
                new_input = " ".join(current_input.split(' ')[:-1] + [full_path])
            else:
                new_input = full_path
            self.terminal_area.insert(self.current_line_start_index, new_input)
        elif len(completions) > 1:
            # display options, then show prompt again
            display_names = [os.path.basename(c) for c in completions]
            self.print_text("", new_line=True)
            self.print_text("  ".join(display_names))
            self.print_prompt()
            self.terminal_area.insert(self.current_line_start_index, current_input)
        else:
            # no completions: reinsert unchanged input
            self.terminal_area.insert(self.current_line_start_index, current_input)

        self.terminal_area.see(tk.END)
        return "break"

    # ---------------------------
    # Enter handling & execution
    # ---------------------------
    def handle_input(self, event):
        """
        Called when user presses Enter. Extract command and either handle built-ins
        or dispatch to executor or PTY-runner.
        """
        # Prevent default newline insertion
        command = self.get_current_input_text().strip()
        # Move to new line (visual)
        self.print_text("", new_line=True)

        if command == "":
            self.print_prompt()
            return "break"

        # Push to history (avoid duplicate consecutive entries)
        if not self.command_history or self.command_history[-1] != command:
            self.command_history.append(command)
        # reset history browsing
        self.history_index = None

        # Built-in commands
        lower = command.lower()
        if lower in ("clear", "cls"):
            # Clear all text
            try:
                self.terminal_area.delete("1.0", tk.END)
            except tk.TclError:
                pass
            self.print_prompt()
            return "break"
        if lower == "exit":
            self.quit()
            return "break"

        # Decide whether to run as PTY TUI app or regular command
        cmd_base = command.split()[0].lower()
        if cmd_base in TUI_APPS:
            # start PTY app in background thread
            threading.Thread(target=self._run_tui_app_thread, args=(command,), daemon=True).start()
        else:
            threading.Thread(target=self._run_command_thread, args=(command,), daemon=True).start()

        return "break"

    def _run_command_thread(self, command: str):
        """
        Execute non-TUI commands via execute_command_logic and print outputs.
        Runs in a background thread.
        """
        try:
            result = execute_command_logic(command)
        except Exception as e:
            self.print_text(f"Executor error: {e}", color="error")
            self.print_prompt()
            return

        rtype = result.get("type", "error")
        if rtype == "success":
            out = result.get("output", "")
            err = result.get("error", "")
            if out:
                self.print_text(out.rstrip("\n"))
            if err:
                self.print_text(err.rstrip("\n"), color="error")
        elif rtype == "tui_error":
            # executor indicates this is a TUI-only program
            self.print_text(result.get("message", "TUI application requires PTY."), color="error")
        else:
            self.print_text(result.get("message", "Command failed."), color="error")

        self.print_prompt()

    # ---------------------------
    # PTY-backed TUI runner
    # ---------------------------
    def _run_tui_app_thread(self, command: str):
        """
        Fork a PTY and run the requested TUI application. Read bytes from PTY and print them.
        Runs in a background thread.
        """
        # Check platform support
        if not hasattr(pty, "fork"):
            self.print_text("PTY is not available on this platform. Use a Unix-like system or WSL.", color="error")
            self.print_prompt()
            return

        def append_bytes(bs: bytes):
            try:
                decoded = bs.decode(errors="ignore")
            except Exception:
                decoded = str(bs)
            # print raw bytes content (no extra newline)
            self.print_text(decoded, new_line=False)

        try:
            pid, fd = pty.fork()
        except Exception as e:
            self.print_text(f"Failed to fork PTY: {e}", color="error")
            self.print_prompt()
            return

        if pid == 0:
            # Child: exec the command
            try:
                parts = command.split()
                os.execvp(parts[0], parts)
            except Exception as e:
                # If exec fails, write to stderr and exit child
                sys.stderr.write(f"Exec failed: {e}\n")
                os._exit(1)
        else:
            # Parent: read from fd until EOF
            try:
                while True:
                    r, _, _ = select.select([fd], [], [], 0.1)
                    if fd in r:
                        try:
                            data = os.read(fd, 4096)
                        except OSError:
                            break
                        if not data:
                            break
                        append_bytes(data)
                    # Non-blocking check if child exited (optional)
                    try:
                        wpid, status = os.waitpid(pid, os.WNOHANG)
                        if wpid == pid:
                            # child exited; continue to drain fd until EOF
                            pass
                    except ChildProcessError:
                        break
                # Try to reap if not already
                try:
                    os.waitpid(pid, 0)
                except Exception:
                    pass
            except Exception as e:
                self.print_text(f"PTY read error: {e}", color="error")

        # After TUI app exits, restore prompt
        self.print_prompt()

# If executed directly, run the UI
if __name__ == "__main__":
    # Example: choose theme "Dracula" or "Dark"
    app = TerminalUI(theme_name="Dracula")
    app.mainloop()
