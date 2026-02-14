import json
import os

def check_file(filename):
    if not os.path.exists(filename):
        print(f"[!] {filename} bulunamadı.")
        return False
    try:
        with open(filename, 'r') as f:
            json.load(f)
        print(f"[+] {filename} geçerli.")
        return True
    except json.JSONDecodeError:
        print(f"[!] {filename} bozuk (JSON hatası).")
        return False

if __name__ == "__main__":
    print("--- Offset Dosya Kontrolü ---")
    check_file("offsets.json")
    check_file("client_dll.json")
    print("-----------------------------")
