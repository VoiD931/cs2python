
import pymem
import json
import struct

def list_pawns():
    try:
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        with open('offsets.json', 'r') as f:
            offs = json.load(f)
        dwEntityList = offs['client.dll']['dwEntityList']
        
        entity_list = pm.read_longlong(client + dwEntityList)
        
        print("Scanning indices 1-64 for Player Pawns...")
        
        for i in range(1, 64):
            chunk = (i >> 9)
            idx = i & 0x1FF
            
            try:
                list_entry = pm.read_longlong(entity_list + 0x10 + 8 * chunk)
                if not list_entry: continue
                
                ent_ptr = pm.read_longlong(list_entry + 120 * idx)
                if not ent_ptr: continue
                
                # Check for Pawn characteristics
                # m_pCameraServices: 5136 (0x1410)
                cam_svc = pm.read_longlong(ent_ptr + 5136)
                
                # m_pViewModelServices: 5080? No, that was WeaponServices.
                # ViewmodelServices was 0x1420? Or something.
                # m_pWeaponServices: 5080 (0x13D8)
                wep_svc = pm.read_longlong(ent_ptr + 5080)
                
                if cam_svc == 0 and wep_svc == 0:
                    continue # Not a pawn
                    
                print(f"Index {i} ({hex(ent_ptr)}) seems to be a Pawn.")
                print(f"  CameraServices: {hex(cam_svc)}")
                print(f"  WeaponServices: {hex(wep_svc)}")
                
                # Check FOV at 9252
                try:
                    fov = pm.read_float(ent_ptr + 9252)
                    print(f"  FOV at 9252: {fov}")
                except:
                    print("  FOV at 9252: Error")

                # Check Viewmodel Handle at 0x3ECC (if it exists)
                try:
                    vm_h = pm.read_uint(ent_ptr + 0x3ECC)
                    print(f"  Handle at 0x3ECC: {hex(vm_h)} (Index {vm_h & 0x7FFF})")
                except: pass
                
                # Scan first 0x5000 bytes for 68.0 roughly
                # Optional: too noisy
                
            except:
                pass

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_pawns()
