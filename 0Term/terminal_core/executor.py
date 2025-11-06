# terminal_core/executor.py
import os
import pty
import subprocess
from utils.helpers import get_dynamic_prompt

def execute_command_logic(command: str):
    """
    Executes given shell command and returns a dict (type, output, error).
    Supports PTY (TUI apps), I/O redirection, and internal commands like 'cd'.
    """

    parts = command.strip().split()
    if not parts:
        return {"type": "empty"}

    cmd = parts[0].lower()

    # --- Internal Command: cd ---
    if cmd == "cd":
        target_dir = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        try:
            os.chdir(target_dir)
            return {"type": "success", "output": f"Directory changed to: {os.getcwd()}"}
        except FileNotFoundError:
            return {"type": "error", "message": f"Error: Directory not found: {target_dir}"}
        except Exception as e:
            return {"type": "error", "message": f"Error in cd: {e}"}

    # --- I/O Redirection (>, >>) ---
    target_file = None
    redirect_type = None
    command_to_run = command

    if ">" in parts or ">>" in parts:
        if ">>" in parts:
            redirect_type = "append"
            redirect_index = parts.index(">>")
        else:
            redirect_type = "write"
            redirect_index = parts.index(">")
        try:
            command_to_run = " ".join(parts[:redirect_index])
            target_file = parts[redirect_index + 1]
        except (ValueError, IndexError):
            return {"type": "error", "message": "Error: Missing filename for redirection."}

    # --- Detect if command needs PTY (TUI) ---
    tui_required = False
    TUI_APPS = ["nano", "vi", "vim", "micro", "top", "htop", "less", "man"]
    if cmd in TUI_APPS:
        tui_required = True

    # --- Run the command ---
    try:
        if tui_required:
            output = run_in_pty(command_to_run)
            return {"type": "success", "output": output}

        else:
            result = subprocess.run(
                command_to_run,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            output = result.stdout
            error = result.stderr

            # --- Write to file if redirection is used ---
            if target_file:
                mode = "w" if redirect_type == "write" else "a"
                try:
                    with open(target_file, mode, encoding="utf-8") as f:
                        f.write(output)
                    msg = f"Output {'written' if mode == 'w' else 'appended'} to '{target_file}'."
                    return {"type": "success", "output": msg, "error": error}
                except Exception as e:
                    return {"type": "error", "message": f"File write error: {e}"}

            return {"type": "success", "output": output, "error": error}

    except FileNotFoundError:
        return {"type": "error", "message": f"Error: Command not found: {cmd}"}
    except Exception as e:
        return {"type": "error", "message": f"Unexpected error: {e}"}


def run_in_pty(command: str) -> str:
    """
    Runs a command inside a pseudo-terminal (PTY) to support TUI applications.
    Returns the captured output as text.
    """
    output = b""
    pid, fd = pty.fork()

    if pid == 0:
        # Child process executes the command
        os.execvp("bash", ["bash", "-c", command])
    else:
        # Parent process reads PTY output
        try:
            while True:
                data = os.read(fd, 1024)
                if not data:
                    break
                output += data
        except OSError:
            pass
        finally:
            os.close(fd)

    return output.decode("utf-8", errors="ignore")
