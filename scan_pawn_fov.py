
import pymem
import json
import struct

def scan_pawn_fov():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        print(f"Local Pawn: {hex(local_pawn)}")
        
        if not local_pawn: return

        print("Scanning Pawn for FOV values (90.0, 60.0, 68.0)...")
        try:
             buff = pm.read_bytes(local_pawn, 0x5000)
             
             for j in range(0, 0x5000, 4):
                 fval = struct.unpack('<f', buff[j:j+4])[0]
                 
                 if abs(fval - 90.0) < 0.1:
                      print(f"Found 90.0 at offset {hex(j)}")
                 
                 elif abs(fval - 60.0) < 0.1:
                      print(f"Found 60.0 at offset {hex(j)}")
                      
                 elif abs(fval - 68.0) < 0.1:
                      print(f"Found 68.0 at offset {hex(j)}")

        except Exception as e:
             print(f"Error reading pawn memory: {e}")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_pawn_fov()
