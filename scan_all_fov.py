
import pymem
import json
import struct

def scan_all_fov():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList']
        
        entity_list = pm.read_longlong(client + dwEntityList)
        
        print("Scanning ALL entities for float 68.0...")
        
        for i in range(1, 2048):
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            try:
                list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
                if not list_entry: continue
                
                ent_ptr = pm.read_longlong(list_entry + 120 * idx)
                if not ent_ptr or ent_ptr < 0x10000 or ent_ptr > 0x7FFFFFFFFFFF: 
                    continue
                
                # Check known FOV offset first (9252 = 0x2424)
                try:
                    val = pm.read_float(ent_ptr + 9252)
                    if 50.0 < val < 80.0:
                         print(f"[MATCH 9252] Index {i}: {val} found at offset 9252! Entity {hex(ent_ptr)}")
                except: pass

                try:
                    buff = pm.read_bytes(ent_ptr, 0x3000)
                except: continue
                
                for j in range(0, 0x3000, 4):
                    try:
                        fval = struct.unpack('<f', buff[j:j+4])[0]
                        if abs(fval - 60.0) < 0.1:
                             print(f"Index {i}: Found ~60.0 ({fval}) at offset {hex(j)} (Entity {hex(ent_ptr)})")
                        elif abs(fval - 68.0) < 0.1:
                             print(f"Index {i}: Found ~68.0 ({fval}) at offset {hex(j)} (Entity {hex(ent_ptr)})")
                    except: pass
                
            except:
                pass

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_all_fov()
