
import pymem
import json

def scan_ents():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList']
        
        entity_list = pm.read_longlong(client + dwEntityList)
        if not entity_list: return

        print("Scanning entities for ViewModel FOV (approx 68.0)...")
        
        for i in range(1, 64): # Players usually
            pass # skip players
            
        for i in range(64, 1024):
            # Logic
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
            if not list_entry: continue
            
            pawn_ptr = pm.read_longlong(list_entry + 120 * idx)
            if not pawn_ptr: continue
            
            # Check 9252
            try:
                fov = pm.read_float(pawn_ptr + 9252)
                if 50.0 < fov < 130.0:
                    print(f"Index {i}: FOV {fov} at {hex(pawn_ptr)}")
                    
                    # Also check if we can identify it as a viewmodel
                    # C_BaseViewModel usually has m_hWeapon (handle)
                    # or m_hOwner (handle)
                    # Let's verify by checking if changing it changes game? 
                    # Use can't verify now, but I can note it.
            except:
                pass

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scan_ents()
