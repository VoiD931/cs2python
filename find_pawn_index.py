
import pymem
import json

def find_pawn_index():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
            
        dwEntityList = offs['client.dll']['dwEntityList']
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        print(f"Local Pawn Address: {hex(local_pawn)}")
        
        if not local_pawn: return

        entity_list = pm.read_longlong(client + dwEntityList)
        
        found_idx = -1
        
        for i in range(1, 1024):
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            try:
                list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
                if not list_entry: continue
                
                ent_ptr = pm.read_longlong(list_entry + 120 * idx)
                if ent_ptr == local_pawn:
                    print(f"Found Local Pawn at Index {i} ({hex(i)})")
                    found_idx = i
                    break
            except: pass
            
        if found_idx == -1:
            print("Local Pawn not found in Entity List (0-1024).")
            return
            
        # Now scan this pawn for Viewmodel Handle
        print(f"Scanning Pawn {hex(local_pawn)} for Viewmodel candidates...")
        # Search for handles in range
        for off in range(0, 0x4000, 4):
            val = pm.read_uint(local_pawn + off)
            idx = val & 0x7FFF
            if 0 < idx < 2048 and val != 0xFFFFFFFF:
                 # Check if this handle resolves to an entity
                 # ... (simplified)
                 pass
                 
        # Let's verify 0x3ECC again
        val_3ecc = pm.read_uint(local_pawn + 0x3ECC)
        print(f"Value at 0x3ECC: {hex(val_3ecc)} (Index {val_3ecc & 0x7FFF})")
        
        # Check indices 38 and 39
        # Assuming they are Viewmodel candidates
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_pawn_index()
