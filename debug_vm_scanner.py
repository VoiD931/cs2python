
import pymem
import pymem.process
import struct
import json

def read_ptr(pm, addr):
    try:
        return pm.read_longlong(addr)
    except:
        return 0

def read_uint(pm, addr):
    try:
        return pm.read_uint(addr)
    except:
        return 0

def read_float(pm, addr):
    try:
        return pm.read_float(addr)
    except:
        return 0

def get_entity_by_handle(pm, client_base, entity_list_offset, handle):
    if not handle or handle == 0xFFFFFFFF:
        return 0
    
    index = handle & 0x7FFF
    try:
        entity_list = read_ptr(pm, client_base + entity_list_offset)
        if not entity_list:
            return 0
            
        list_entry = read_ptr(pm, entity_list + 0x10 + 8 * ((index >> 9) & 0x7FFF)) # Logic from misc.py
        if not list_entry:
            return 0
            
        pawn = read_ptr(pm, list_entry + 120 * (index & 0x1FF))
        return pawn
    except:
        return 0

def scan_vm_services():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        # Load offsets
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        dwEntityList = offs['client.dll']['dwEntityList']
        
        print(f"Client Base: {hex(client)}")
        
        local_pawn = read_ptr(pm, client + dwLocalPlayerPawn)
        print(f"Local Pawn: {hex(local_pawn)}")
        
        if not local_pawn:
            return

        # Scan for potential m_pViewModelServices pointers
        # Normally between 0x1000 and 0x1500
        print("Scanning for ViewModelServices...")
        
        for offset in range(0x1000, 0x1600, 8):
            ptr = read_ptr(pm, local_pawn + offset)
            if ptr > 0x10000: # pointer validation roughly
                # Assume this ptr is ViewModelServices
                # Check for m_hViewModel at 0x40
                h_vm = read_uint(pm, ptr + 0x40)
                
                # Handle should be smallish int, not huge pointer
                if 0 < h_vm < 0x100000:
                    # Valid-ish handle
                    # Try to resolve it
                    vm_ent = get_entity_by_handle(pm, client, dwEntityList, h_vm)
                    
                    if vm_ent:
                        print(f"[ MATCH ] Offset: {hex(offset)} -> Svc: {hex(ptr)} -> Handle: {hex(h_vm)} -> VM Entity: {hex(vm_ent)}")
                        
                        # Check FOV at VM Entity
                        fov = read_float(pm, vm_ent + 9252) # m_flViewmodelFOV
                        print(f"    -> FOV at 9252: {fov}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scan_vm_services()
