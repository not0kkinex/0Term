# executor.py
import subprocess
import os
from utils.helpers import get_dynamic_prompt

TUI_APPS = ["nano", "vi", "vim", "micro", "top", "htop", "less", "man"]

def execute_command_logic(command: str):
    """
  It processes the given command and returns a dictionary (output, error, return_code, type).
  It contains I/O redirection logic.
    """
    
    parts = command.split()
    if not parts:
        return {"type": "empty"}
        
    cmd = parts[0].lower()
    

    if cmd in TUI_APPS:
        return {
            "type": "tui_error",
            "message": f"Error: '{cmd}' is a Full Screen Terminal Application (TUI). PTY support is required. Contains I/O redirection logic."
        }
            

    if cmd == "cd":
        target_dir = parts[1] if len(parts) > 1 else os.path.expanduser('~')
        try:
            os.chdir(target_dir)
            return {
                "type": "success",
                "output": f"Directory Changed: {os.getcwd()}"
            }
        except FileNotFoundError:
            return {
                "type": "error",
                "message": f"Error: Directory not found: {target_dir}"
            }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error: problem with cd command: {e}"
            }

    command_to_run = command
    target_file = None
    redirect_type = None

    if '>' in parts:
        try:
            redirect_index = parts.index('>')
            redirect_type = 'write'
            command_to_run = " ".join(parts[:redirect_index])
            target_file = parts[redirect_index + 1]
        except (ValueError, IndexError):
            return {"type": "error", "message": "Error: File name for redirect is missing or in incorrect format."}
            
    elif '>>' in parts:
        try:
            redirect_index = parts.index('>>')
            redirect_type = 'append'
            command_to_run = " ".join(parts[:redirect_index])
            target_file = parts[redirect_index + 1]
        except (ValueError, IndexError):
            return {"type": "error", "message": "Error: File name for redirect is missing or in incorrect format."}

    try:
        result = subprocess.run(
            command_to_run, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=False,
            encoding='utf-8'
        )
        
        output = result.stdout
        error = result.stderr

        if target_file:
            mode = 'w' if redirect_type == 'write' else 'a'
            try:
                with open(target_file, mode, encoding='utf-8') as f:
                    f.write(output)
                
                terminal_output = f"Output has been {'written to' if mode == 'w' else 'appended to'} the file '{target_file}'."
                
            except Exception as e:
                return {"type": "error", "message": f"Dosya yazma hatası: {e}"}

            return {
                "type": "success",
                "output": terminal_output,
                "error": error 
            }
        
        return {
            "type": "success",
            "output": output,
            "error": error
        }

    except FileNotFoundError:
        return {"type": "error", "message": f"Hata: Komut bulunamadı: {cmd}"}
    except Exception as e:
        return {"type": "error", "message": f"Beklenmedik Hata: {e}"}
