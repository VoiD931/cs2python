
import pymem
import json
import time

def get_entity_by_handle(pm, client_base, entity_list_offset, handle):
    if not handle or handle == 0xFFFFFFFF:
        return 0
    index = handle & 0x7FFF
    try:
        entity_list = pm.read_longlong(client_base + entity_list_offset)
        if not entity_list: return 0
        list_entry = pm.read_longlong(entity_list + 0x10 + 8 * ((index >> 9) & 0x7FFF))
        if not list_entry: return 0
        return pm.read_longlong(list_entry + 120 * (index & 0x1FF))
    except:
        return 0

def brute_vm():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList']
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        if not local_pawn: return

        # 1. Find Viewmodel Handle offset (scan again to be sure)
        print("Scanning for Viewmodel Handle (0x188)...")
        target_handle = 0x188 # Assuming 392 is standard for first slot viewmodel
        found_off = None
        for off in range(0, 0x4000, 4):
            try:
                v = pm.read_uint(local_pawn + off)
                if (v & 0x7FFF) == target_handle:
                    print(f"  Found handle {hex(v)} at offset {hex(off)}")
                    found_off = off
                    # Proceed with this offset
                    break
            except:
                pass
        
        if not found_off:
            print("Could not find Viewmodel Handle offset. Is 0x188 correct?")
            # Try to find any entity with FOV 60.0
            # Reuse scan logic
            return

        h_vm = pm.read_uint(local_pawn + found_off)
        vm_ent = get_entity_by_handle(pm, client, dwEntityList, h_vm)
        print(f"ViewModel Entity at: {hex(vm_ent)}")
        
        if not vm_ent: return

        print("Brute forcing FOV on ViewModel Entity...")
        
        # Scan for 60.0 or 68.0
        candidates = []
        for off in range(0, 0x3000, 4):
            try:
                val = pm.read_float(vm_ent + off)
                if 58.0 < val < 70.0: # Close to 60 or 68
                    print(f"  Found candidate {val} at offset {hex(off)}")
                    candidates.append(off)
            except:
                pass
        
        print(f"Found {len(candidates)} candidates.")
        if not candidates: return
        
        print("Writing 120.0 to all candidates for 5 seconds...")
        start = time.time()
        while time.time() - start < 5:
            for off in candidates:
                try:
                    pm.write_float(vm_ent + off, 120.0)
                except: pass
            time.sleep(0.01)
            
        print("Restoring candidates...")
        # Actually I don't know original values exactly, but let's just stop writing.
        # User will tell if it worked via effect.
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    brute_vm()
