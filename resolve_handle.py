
import pymem
import json

def get_entity_by_handle(pm, client_base, entity_list_offset, handle):
    if not handle or handle == 0xFFFFFFFF:
        return 0
    index = handle & 0x7FFF
    try:
        entity_list = pm.read_longlong(client_base + entity_list_offset)
        if not entity_list:
            print("Entity list base is 0")
            return 0
        
        chunk_idx = (index >> 9) & 0x7FFF
        print(f"Chunk Index: {chunk_idx}")
        
        list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk_idx)
        print(f"List Entry (Chunk): {hex(list_entry)}")
        
        if not list_entry: return 0
        
        ent_idx_in_chunk = index & 0x1FF
        pawn_ptr_addr = list_entry + 120 * ent_idx_in_chunk
        print(f"Pawn Ptr Address: {hex(pawn_ptr_addr)}")
        
        pawn = pm.read_longlong(pawn_ptr_addr)
        print(f"Pawn: {hex(pawn)}")
        return pawn
    except Exception as e:
        print(f"Exception in get_entity: {e}")
        return 0

def resolve():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList'] # 38445272 = 0x24AA4D8
        
        # Candidate handles
        handles = [0x135004e, 0x970048]
        
        for h in handles:
            ent = get_entity_by_handle(pm, client, dwEntityList, h)
            print(f"Handle {hex(h)} -> Entity {hex(ent)}")
            
            if ent:
                # Check FOV at 9252
                try:
                    fov = pm.read_float(ent + 9252)
                    print(f"    FOV at 9252: {fov}")
                    
                    # Dump start of entity to see vtable
                    vt = pm.read_longlong(ent)
                    print(f"    VTable: {hex(vt)}")
                    
                except:
                    pass

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    resolve()
