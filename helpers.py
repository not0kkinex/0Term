# utils/helpers.py
import os
import getpass

# --- Tema Tanımlamaları ---
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
    }
}

# --- Prompt Oluşturucu ---
def get_dynamic_prompt():
    """Kullanıcı adı ve mevcut dizini içeren prompt'u oluşturur."""
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

# --- Tab Tamamlama Yardımcısı ---
def get_completions(partial_path):
    """
    Verilen kısmi yola (dosya/klasör) uyan tamamlama listesini döndürür.
    """
    if not partial_path:
        return os.listdir('.')

    directory, prefix = os.path.split(partial_path)
    if not directory:
        directory = '.'
    
    # Eğer dizin bir dosya değilse ve varsa
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
