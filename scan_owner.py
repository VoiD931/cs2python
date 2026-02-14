
import pymem
import json
import struct

def scan_owner():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
            
        dwEntityList = offs['client.dll']['dwEntityList']
        dwLocalPlayerController = offs['client.dll']['dwLocalPlayerController']
        
        controller = pm.read_longlong(client + dwLocalPlayerController)
        if not controller:
            print("No controller found.")
            return

        # m_hPlayerPawn is at offset 0x??? 
        # Dump controller said 2316 (0x90C).
        h_pawn_full = pm.read_uint(controller + 2316)
        print(f"Local Pawn Handle: {hex(h_pawn_full)}")
        
        if not h_pawn_full or h_pawn_full == 0xFFFFFFFF:
             print("Invalid pawn handle.")
             return
             
        # Also get dwLocalPlayerPawn address for double check
        # But we need the handle value as stored in other entities.
        
        entity_list = pm.read_longlong(client + dwEntityList)
        print("Scanning entities for Owner Handle...")
        
        matches = []

        for i in range(1, 2048):
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
            if not list_entry: continue
            
            ent_ptr = pm.read_longlong(list_entry + 120 * idx)
            if not ent_ptr or ent_ptr < 0x10000 or ent_ptr > 0x7FFFFFFFFFFF: 
                continue
            
            # Scan first 0x500 bytes for handle
            try:
                buff = pm.read_bytes(ent_ptr, 0x500)
            except:
                continue
            
            # Search for handle bytes
            import ctypes
            # handle is uint32
            handle_bytes = struct.pack('<I', h_pawn_full)
            
            off = buff.find(handle_bytes)
            if off != -1:
                print(f"Index {i}: Found Pawn Handle at offset {hex(off)} in Entity {hex(ent_ptr)}")
                
                # Check for FOV candidates in this entity
                # Scan a much larger buffer
                # 0x0 to 0x5000
                large_buff = pm.read_bytes(ent_ptr, 0x5000)
                
                for j in range(0, 0x5000, 4):
                    try:
                        fval = struct.unpack('<f', large_buff[j:j+4])[0]
                        if 58.0 < fval < 70.0:
                             print(f"    -> Float {fval} at offset {hex(j)}")
                    except: pass
                    
                matches.append(ent_ptr)

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_owner()
