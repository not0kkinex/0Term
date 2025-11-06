# helpers.py
import os
import getpass

# --- Theme Definitions ---
THEMES = {
    "Dark": {
        "bg": "#1E1E1E",       
        "text": "#00FF00",     
        "error": "#FF4500",     
        "cursor": "#FFFFFF",
    },
    "Light": {
        "bg": "#FFFFFF",       
        "text": "#000000",     
        "error": "#FF0000",     
        "cursor": "#000000",
    },
    "Dracula": {
        "bg": "#282A36",       
        "text": "#F8F8F2",     
        "error": "#FF6E6E",     
        "cursor": "#F8F8F2",
    },
    "0kki":{     
        "bg": "#212133",
        "text": "#72F1B8",
        "error":"#FF6B6B",
        "cursor":"#F9D71C",
    }
}

# --- Prompt Oluşturucu ---
def get_dynamic_prompt():
    """Creates a prompt containing the username and current directory."""
    try:
        user = getpass.getuser()
        cwd_path = os.getcwd()
        cwd_display = os.path.basename(cwd_path)
        
        if cwd_path == os.path.expanduser('~'):
            cwd_display = "~"
        elif cwd_path == '/':
            cwd_display = "/"

        return f"{user} @ {cwd_display} : $ "
        
    except Exception:
        return "$ "

def get_completions(partial_path):
    """
    The completion list that matches the given partial path (file/folder) ends.
    """
    if not partial_path:
        return os.listdir('.')

    directory, prefix = os.path.split(partial_path)
    if not directory:
        directory = '.'
    
    if not os.path.isdir(directory) and directory != '.':
        return []

    try:
        all_entries = os.listdir(directory)
        
        matches = [
            os.path.join(directory, entry)
            for entry in all_entries
            if entry.startswith(prefix)
        ]
        
        return matches
    except Exception:
        return []
