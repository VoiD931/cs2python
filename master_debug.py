
import pymem
import json
import struct

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

def master_debug():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
            
        dwEntityList = offs['client.dll']['dwEntityList']
        dwLocalPlayerController = offs['client.dll']['dwLocalPlayerController']
        
        # 1. Get Controller
        controller = pm.read_longlong(client + dwLocalPlayerController)
        if not controller:
            print("No controller found. Game running?")
            return
            
        print(f"Controller: {hex(controller)}")
        
        # 2. Get Pawn Handle
        # m_hPlayerPawn offset is 0x90C (2316) from dump
        h_pawn = pm.read_uint(controller + 2316)
        print(f"Pawn Handle: {hex(h_pawn)}")
        
        if not h_pawn or h_pawn == 0xFFFFFFFF:
            print("Invalid pawn handle in controller.")
            return

        # 3. Resolve Pawn
        pawn = get_entity_by_handle(pm, client, dwEntityList, h_pawn)
        print(f"Resolved Pawn Address: {hex(pawn)}")
        
        if not pawn:
            print("Could not resolve pawn.")
            return

        # Verify readability
        try:
            pm.read_int(pawn)
            print("Pawn memory is readable.")
        except:
            print("Pawn memory NOT readable.")
            return

        # 4. Scan Pawn for Viewmodel Handle (0x188 or similar)
        # We don't know the exact handle, but viewmodel index is usually small (e.g. < 512).
        # We can look for handles that resolve to entities with "Viewmodel" properties?
        # Or look for handles near the end of Pawn structure.
        
        print("Scanning Pawn for potential Viewmodel Handles...")
        
        candidates = []
        for off in range(0, 0x4000, 4):
            try:
                val = pm.read_uint(pawn + off)
                # Check if it looks like a handle (index < 2048, serial > 0)
                idx = val & 0x7FFF
                if 0 < idx < 2048 and val != 0xFFFFFFFF:
                     # Check if it resolves to an entity
                     ent = get_entity_by_handle(pm, client, dwEntityList, val)
                     if ent:
                         # Check if this entity has FOV ~60-68
                         # Scan first 0x3000 bytes
                         try:
                             buff = pm.read_bytes(ent, 0x3000)
                             for j in range(0, 0x3000, 4):
                                 fval = struct.unpack('<f', buff[j:j+4])[0]
                                 if abs(fval - 60.0) < 0.1 or abs(fval - 68.0) < 0.1:
                                      print(f"  [MATCH] Offset {hex(off)} -> Handle {hex(val)} -> Entity {hex(ent)}")
                                      print(f"       -> Found FOV {fval} at Entity Offset {hex(j)}")
                                      candidates.append((off, val, ent, j, fval))
                                      # Don't break, find all
                         except: pass
            except:
                pass
                
        if not candidates:
            print("No candidates found.")
            # Alternative: Assume 0x3ECC is correct offset for handle, but handle value changed
            # Check 0x3ECC specifically
            try:
                h_at_3ecc = pm.read_uint(pawn + 0x3ECC)
                print(f"Value at Pawn+0x3ECC: {hex(h_at_3ecc)}")
                # Resume checking this handle if valid
            except:
                print("Could not read Pawn+0x3ECC")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    master_debug()
