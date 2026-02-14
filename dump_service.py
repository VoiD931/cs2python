
import pymem
import json

def dump_obj():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        # Hardcoded address from previous step
        # 0x34d9bf83000
        # But wait, this address might change if I restart game or new round.
        # So I must read it from pawn again.
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        
        if not local_pawn:
            return

        print(f"Pawn: {hex(local_pawn)}")
        
        svc_addr = pm.read_longlong(local_pawn + 0x1420)
        print(f"Service at 0x1420: {hex(svc_addr)}")
        
        if svc_addr:
            print("Dumping Service memory (0x0 - 0x100):")
            for off in range(0, 0x100, 4):
                val = pm.read_uint(svc_addr + off)
                print(f"{hex(off)}: {hex(val)}")
        
        # Verify 9252 again
        fov = pm.read_float(local_pawn + 9252)
        print(f"Pawn FOV (9252): {fov}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_obj()
