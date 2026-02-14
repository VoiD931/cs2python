
import pymem
import struct

def check_vm_fov():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        # dwLocalPlayerPawn
        # using config-like offset logic if possible, or just hardcode for testing if needed
        # We need the offset for dwLocalPlayerPawn. 
        # In offsets.json it might be there.
        # Let's assume standard offset or read from offsets.json
        
        import json
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
            
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        print(f"dwLocalPlayerPawn: {dwLocalPlayerPawn}")
        
        pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        print(f"Pawn: {hex(pawn)}")
        
        if not pawn:
            return

        # Check 9252 (m_flViewmodelFOV)
        val = pm.read_float(pawn + 9252)
        print(f"Value at 9252: {val}")
       
        # Check nearby
        for i in range(-20, 20, 4):
            try:
                v = pm.read_float(pawn + 9252 + i)
                print(f"Offset {9252+i} ({hex(9252+i)}): {v}")
            except:
                pass

    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_vm_fov()
