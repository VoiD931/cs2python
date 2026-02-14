
import pymem
import json
import struct
import time

def force_fov():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
            
        dwEntityList = offs['client.dll']['dwEntityList']
        dwLocalPlayerController = offs['client.dll']['dwLocalPlayerController']
        
        controller = pm.read_longlong(client + dwLocalPlayerController)
        if not controller: return

        # 1. Get Pawn Handle
        h_pawn_full = pm.read_uint(controller + 2316) # 0x90C
        if not h_pawn_full or h_pawn_full == 0xFFFFFFFF:
             print("Invalid pawn handle.")
             return
             
        # 2. Find entities referencing this pawn
        entity_list = pm.read_longlong(client + dwEntityList)
        
        targets = []
        for i in range(1, 2048):
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            try:
                list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
                if not list_entry: continue
                ent_ptr = pm.read_longlong(list_entry + 120 * idx)
                if not ent_ptr or ent_ptr < 0x10000 or ent_ptr > 0x7FFFFFFFFFFF: 
                    continue
                
                # Check first 0x200 bytes for handle
                buff = pm.read_bytes(ent_ptr, 0x200)
                handle_bytes = struct.pack('<I', h_pawn_full)
                if buff.find(handle_bytes) != -1:
                    print(f"Adding target: Entity {hex(ent_ptr)} (Index {i})")
                    targets.append(ent_ptr)
            except: pass
            
        if not targets:
            print("No targets found.")
            return
            
        print(f"Writing 120.0 to offset 9252 on {len(targets)} targets for 10 seconds...")
        start = time.time()
        while time.time() - start < 10:
            for t in targets:
                try:
                    pm.write_float(t + 9252, 120.0)
                except: pass
            time.sleep(0.01)
            
        print("Done.")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    force_fov()
