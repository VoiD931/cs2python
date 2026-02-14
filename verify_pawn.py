
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

def scan_pawn():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        dwLocalPlayerController = offs['client.dll']['dwLocalPlayerController']
        dwEntityList = offs['client.dll']['dwEntityList']
        
        print(f"Client: {hex(client)}")
        
        # 1. Read via dwLocalPlayerPawn
        pawn1 = pm.read_longlong(client + dwLocalPlayerPawn)
        print(f"Pawn via dwLocalPlayerPawn: {hex(pawn1)}")
        
        # 2. Read via Controller
        controller = pm.read_longlong(client + dwLocalPlayerController)
        print(f"Controller: {hex(controller)}")
        
        if controller:
            h_pawn = pm.read_uint(controller + 0x90C) # m_hPlayerPawn (usually 0x60C or 0x90C? dump said 2316 = 0x90C)
            # dump_controller.py output: "m_hPlayerPawn": 2316
            print(f"Pawn Handle: {hex(h_pawn)}")
            
            pawn2 = get_entity_by_handle(pm, client, dwEntityList, h_pawn)
            print(f"Pawn via Controller: {hex(pawn2)}")
            
            if pawn1 != pawn2:
                print("MISMATCH! dwLocalPlayerPawn might be wrong.")
        
        target_pawn = pawn2 if (controller and pawn2) else pawn1
        
        if not target_pawn:
            print("No valid pawn found.")
            return

        print(f"Scanning target pawn: {hex(target_pawn)}")
        
        # Scan for ANY pointer-like values
        # We expect services to be pointers to heap memory.
        # Range 0 to 0x2000
        print("Offset | Value")
        for off in range(0, 0x2000, 8):
            val = pm.read_longlong(target_pawn + off)
            # Check if looks like a pointer (e.g. > 0x10000000000)
            if val > 0x10000000000 and val < 0x7FFFFFFFFFFF:
                print(f"{hex(off)} | {hex(val)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scan_pawn()
