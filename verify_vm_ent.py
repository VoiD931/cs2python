
import pymem
import json

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

def dump_vm():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList']
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        print(f"Local Pawn: {hex(local_pawn)}")

        # Get ViewModel Entity via 0x3ECC
        h_vm = pm.read_uint(local_pawn + 0x3ECC)
        print(f"ViewModel Handle: {hex(h_vm)}")
        
        vm_ent = get_entity_by_handle(pm, client, dwEntityList, h_vm)
        print(f"ViewModel Entity: {hex(vm_ent)}")
        
        if not vm_ent:
            print("Could not resolve ViewModel entity.")
            return

        # Dump first 0x4000 bytes
        # Look for float 60.0 (default FOV?) or 68.0?
        # 60.0 in float is approx 0x42700000
        # 68.0 is 0x42880000
        # 90.0 is 0x42b40000
        
        print("Scanning ViewModel Entity for FOV values (50.0 - 120.0)...")
        for off in range(0, 0x4000, 4):
            val = pm.read_float(vm_ent + off)
            if 50.0 < val < 130.0:
                print(f"Offset {hex(off)}: {val}")

        # Search for handles
        # Need to know local pawn handle and weapon handle
        # Local Pawn Handle
        # We can't easily get our own handle without reading it from controller or just knowing our index.
        # But we can check if any value matches `h_vm` (self reference) or similar.

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_vm()
