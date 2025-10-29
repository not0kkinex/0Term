# terminal_core/executor.py
import subprocess
import os
from utils.helpers import get_dynamic_prompt

TUI_APPS = ["nano", "vi", "vim", "micro", "top", "htop", "less", "man"]

def execute_command_logic(command: str):
    """
    Verilen komutu işler ve bir sözlük (output, error, return_code, type) döndürür.
    I/O yönlendirme mantığını içerir.
    """
    
    parts = command.split()
    if not parts:
        return {"type": "empty"}
        
    cmd = parts[0].lower()
    
    # 1. Özel Terminal Uygulamaları
    if cmd in TUI_APPS:
        return {
            "type": "tui_error",
            "message": f"Hata: '{cmd}' bir Tam Ekran Terminal Uygulamasıdır (TUI). PTY desteği gereklidir."
        }
            
    # 2. Dahili Komutlar (cd)
    if cmd == "cd":
        target_dir = parts[1] if len(parts) > 1 else os.path.expanduser('~')
        try:
            os.chdir(target_dir)
            return {
                "type": "success",
                "output": f"Dizin değiştirildi: {os.getcwd()}"
            }
        except FileNotFoundError:
            return {
                "type": "error",
                "message": f"Hata: Dizin bulunamadı: {target_dir}"
            }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Hata: cd komutunda sorun: {e}"
            }

    # 3. Harici Komutlar (subprocess)
    
    # I/O Yönlendirme İşleme
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
            return {"type": "error", "message": "Hata: Yönlendirme için dosya adı eksik veya yanlış format."}
            
    elif '>>' in parts:
        try:
            redirect_index = parts.index('>>')
            redirect_type = 'append'
            command_to_run = " ".join(parts[:redirect_index])
            target_file = parts[redirect_index + 1]
        except (ValueError, IndexError):
            return {"type": "error", "message": "Hata: Yönlendirme için dosya adı eksik veya yanlış format."}

    # Komutu Çalıştır
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
        
        # Eğer I/O yönlendirme varsa, çıktıyı dosyaya yaz
        if target_file:
            mode = 'w' if redirect_type == 'write' else 'a'
            try:
                with open(target_file, mode, encoding='utf-8') as f:
                    f.write(output)
                
                terminal_output = f"Çıktı '{target_file}' dosyasına {'yazıldı' if mode == 'w' else 'eklendi'}."
                
            except Exception as e:
                return {"type": "error", "message": f"Dosya yazma hatası: {e}"}

            return {
                "type": "success",
                "output": terminal_output,
                "error": error 
            }
        
        # I/O yönlendirme yoksa, normal çıktı
        return {
            "type": "success",
            "output": output,
            "error": error
        }

    except FileNotFoundError:
        return {"type": "error", "message": f"Hata: Komut bulunamadı: {cmd}"}
    except Exception as e:
        return {"type": "error", "message": f"Beklenmedik Hata: {e}"}
