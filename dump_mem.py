
import pymem
import json

def dump_memory():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        
        print(f"Local Pawn: {hex(local_pawn)}")
        if not local_pawn:
            return

        # Check Health (m_iHealth) - usually around 0x32C in C_BaseEntity or Pawn
        # Let's try to find where health is.
        # In client_dll.json, C_BaseEntity::m_iHealth is 50 (+ something?)
        # Let's just dump the first 0x500 bytes to see if we spot familiar data.
        
        print(f"Dumping first 0x400 bytes of Pawn")
        for off in range(0, 0x400, 8):
            val = pm.read_longlong(local_pawn + off)
            # visual formatting
            print(f"{hex(off)}: {hex(val)}")
            
        print("Checking specific offsets:")
        # m_iHealth
        try:
             # m_iHealth is often at 0x32C or similar. 
             # Let's look for integers.
             h = pm.read_int(local_pawn + 0x32C)
             print(f"Health at 0x32C: {h}")
        except: pass

        # m_flViewmodelFOV at 9252
        try:
            vf = pm.read_float(local_pawn + 9252)
            print(f"FOV at 9252: {vf}")
        except: pass

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_memory()
