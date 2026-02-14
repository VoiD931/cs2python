
import pymem
import json

def scan_handle():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwLocalPlayerPawn = offs['client.dll']['dwLocalPlayerPawn']
        local_pawn = pm.read_longlong(client + dwLocalPlayerPawn)
        
        if not local_pawn: return

        target_index = 392 # 0x188
        print(f"Scanning Pawn {hex(local_pawn)} for handle matching index 0x188...")
        
        # Scan 0 to 0x4000
        for off in range(0, 0x4000, 4):
            val = pm.read_uint(local_pawn + off)
            if (val & 0x7FFF) == target_index and val != 0xFFFFFFFF:
                print(f"Found match at offset {hex(off)}: Handle {hex(val)}")

                # Verify handle by resolving it
                # Using my resolve logic (which I debugged in resolve_handle.py)
                # But here just knowing the offset is good enough if we assume it's stable.
                # However, it might be inside a Service struct.
                
                # Check if offset is relative to a service pointer?
                # No, we scan relative to Pawn base.
                # If it's inside a nested struct (Service), we might see it directly if Service is embedded or pointed to.
                # But read_uint reads from Pawn + off.
                # If Services are pointers, then the handle is IN the Service object (on heap).
                # So we won't see it here unless it's embedded in Pawn.
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scan_handle()
