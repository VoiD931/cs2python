
import pymem
import json

def scan_ents_smart():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList']
        
        entity_list = pm.read_longlong(client + dwEntityList)
        if not entity_list: return

        print("Scanning entities for probable ViewModel (FOV ~60-68)...")
        
        candidates = []
        
        for i in range(1, 2048):
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
            if not list_entry: continue
            
            ent_ptr = pm.read_longlong(list_entry + 120 * idx)
            if not ent_ptr: continue
            
            # Check 9252
            try:
                fov = pm.read_float(ent_ptr + 9252)
                if 50.0 < fov < 80.0:
                    print(f"Index {i} ({hex(i)}): FOV {fov} at {hex(ent_ptr)}")
                    candidates.append((i, ent_ptr))
            except:
                pass
        
        if not candidates:
            print("No candidates found.")
            return

        print("\nCross-referencing candidates with Pawn memory handles...")
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        
        if not local_pawn: return
        
        for idx, ent_ptr in candidates:
            # Construct handle (simplified, assuming serial matches low bits or ignored for lookup)
            # Actually we just look for index in pawn memory
            target_handle_low = idx & 0x7FFF
            
            found = False
            for off in range(0, 0x5000, 4):
                val = pm.read_uint(local_pawn + off)
                if (val & 0x7FFF) == target_handle_low:
                    print(f"  [MATCH] Index {idx} found as handle {hex(val)} at Pawn+{hex(off)}")
                    found = True
            
            if not found:
                 print(f"  [NO REF] Index {idx} not found in Pawn memory.")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_ents_smart()
