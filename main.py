"""
CS2 External Cheat — Ana Giris Noktasi
========================================
"""

from gui import run_gui
from config import Config
from utils import Memory

if __name__ == "__main__":
    print("======================================")
    print("   RAVEN.CASH CS2 EXTERNAL            ")
    print("======================================")
    
    cfg = Config()
    mem = Memory(cfg.process_name)
    
    if mem.attach():
        print(f"[+] CS2 Bulundu. PID: {mem.pid}")
        client = mem.get_base("client.dll")
        if client:
            print(f"[+] client.dll Base: 0x{client:X}")
            
            # Kritik Offset Kontrolu
            lp = mem.read_ptr(client + cfg.client("dwLocalPlayerPawn"))
            el = mem.read_ptr(client + cfg.client("dwEntityList"))
            print(f"[?] LocalPlayerPawn: 0x{lp:X} (Offset: 0x{cfg.client('dwLocalPlayerPawn'):X})")
            print(f"[?] EntityList: 0x{el:X} (Offset: 0x{cfg.client('dwEntityList'):X})")
            
            if lp == 0:
                print("HATA: LocalPlayerPawn okunamadi! Offset yanlis olabilir.")
            if el == 0:
                print("HATA: EntityList okunamadi! Offset yanlis olabilir.")
        else:
            print("HATA: client.dll modulu bulunamadi!")
    else:
        print("HATA: CS2 bulunamadi/yonetici haklari gerekebilir.")
        
    print("======================================")
    run_gui()
