"""
W2S Formula Test — hangi matris erişim sırasının doğru olduğunu test eder.
Düşman pozisyonlarını hem row-major hem column-major ile ekran koordinatına çevirir.
"""
import ctypes
from offset_loader import load_offsets
from utils import Memory

PROCESS = "cs2.exe"
ENTITY_STRIDE = 0x70


def w2s_row_major(pos, m, sw, sh):
    """Row-major: clip_x=row0, clip_y=row1, clip_w=row3"""
    x, y, z = pos
    w = m[12]*x + m[13]*y + m[14]*z + m[15]
    if w < 0.001:
        return None
    cx = m[0]*x + m[1]*y + m[2]*z + m[3]
    cy = m[4]*x + m[5]*y + m[6]*z + m[7]
    sx = (sw/2) * (1 + cx/w)
    sy = (sh/2) * (1 - cy/w)
    return (sx, sy)


def w2s_col_major(pos, m, sw, sh):
    """Column-major: clip_w=col3, clip_x=col0, clip_y=col1"""
    x, y, z = pos
    w = m[3]*x + m[7]*y + m[11]*z + m[15]
    if w < 0.001:
        return None
    cx = m[0]*x + m[4]*y + m[8]*z + m[12]
    cy = m[1]*x + m[5]*y + m[9]*z + m[13]
    sx = (sw/2) * (1 + cx/w)
    sy = (sh/2) * (1 - cy/w)
    return (sx, sy)


def main():
    offsets = load_offsets()
    co = offsets["client.dll"]
    nv = offsets["netvars"]

    mem = Memory(PROCESS)
    if not mem.attach():
        print("CS2 bulunamadi!")
        return

    client = mem.get_base("client.dll")

    # Screen size
    sw = ctypes.windll.user32.GetSystemMetrics(0)
    sh = ctypes.windll.user32.GetSystemMetrics(1)
    print(f"Ekran: {sw}x{sh}")

    # Game window
    hwnd = ctypes.windll.user32.FindWindowW(None, "Counter-Strike 2")
    if hwnd:
        import ctypes.wintypes as wt
        rect = wt.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
        print(f"CS2 client rect: {rect.right}x{rect.bottom}")

        point = wt.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        print(f"CS2 client origin: ({point.x}, {point.y})")
    else:
        print("CS2 penceresi bulunamadi!")

    # View matrix — her float'u ayrı yazdır
    vm_addr = client + co["dwViewMatrix"]
    vm = mem.read_view_matrix(vm_addr)
    if not vm:
        print("ViewMatrix okunamadi!")
        mem.detach()
        return

    print(f"\nViewMatrix (16 float):")
    for row in range(4):
        vals = [f"{vm[row*4+c]:12.4f}" for c in range(4)]
        print(f"  Row {row}: {' '.join(vals)}")

    # Local player
    local_pawn = mem.read_ptr(client + co["dwLocalPlayerPawn"])
    local_team = mem.read_int(local_pawn + nv["C_BaseEntity.m_iTeamNum"]) if local_pawn else 0
    local_pos = mem.read_vec3(local_pawn + nv["C_BasePlayerPawn.m_vOldOrigin"]) if local_pawn else (0,0,0)
    va = mem.read_vec3(client + co["dwViewAngles"])
    print(f"\nLocal: team={local_team} pos=({local_pos[0]:.0f},{local_pos[1]:.0f},{local_pos[2]:.0f})")
    print(f"ViewAngles: pitch={va[0]:.2f} yaw={va[1]:.2f}")

    # Enemy scan
    entity_list = mem.read_ptr(client + co["dwEntityList"])
    if not entity_list:
        print("Entity list NULL!")
        mem.detach()
        return

    print(f"\n{'IDX':>3} {'NAME':<16} {'HP':>3} {'POS':<30} {'ROW-MAJOR W2S':<20} {'COL-MAJOR W2S':<20}")
    print("-" * 110)

    for i in range(1, 64):
        chunk = mem.read_ptr(entity_list + 0x10 + 8 * (i >> 9))
        if not chunk:
            continue
        controller = mem.read_ptr(chunk + ENTITY_STRIDE * (i & 0x1FF))
        if not controller or controller < 0x10000:
            continue

        pawn_handle = mem.read_uint(controller + nv["CCSPlayerController.m_hPlayerPawn"])
        if not pawn_handle or pawn_handle == 0xFFFFFFFF:
            continue

        pawn_idx = pawn_handle & 0x7FFF
        pawn_chunk = mem.read_ptr(entity_list + 0x10 + 8 * (pawn_idx >> 9))
        if not pawn_chunk:
            continue
        pawn = mem.read_ptr(pawn_chunk + ENTITY_STRIDE * (pawn_idx & 0x1FF))
        if not pawn:
            continue

        hp = mem.read_int(pawn + nv["C_BaseEntity.m_iHealth"])
        team = mem.read_int(pawn + nv["C_BaseEntity.m_iTeamNum"])
        if hp <= 0 or team == local_team:
            continue

        scene = mem.read_ptr(pawn + nv["C_BaseEntity.m_pGameSceneNode"])
        if not scene:
            continue
        pos = mem.read_vec3(scene + nv["CGameSceneNode.m_vecAbsOrigin"])

        name_ptr = mem.read_ptr(controller + nv["CCSPlayerController.m_sSanitizedPlayerName"])
        name = mem.read_string(name_ptr, 64) if name_ptr else ""
        if not name:
            name = mem.read_string(controller + nv["CBasePlayerController.m_iszPlayerName"], 64)

        pos_str = f"({pos[0]:7.1f},{pos[1]:7.1f},{pos[2]:7.1f})"

        rm = w2s_row_major(pos, vm, sw, sh)
        cm = w2s_col_major(pos, vm, sw, sh)

        rm_str = f"({rm[0]:7.0f},{rm[1]:7.0f})" if rm else "BEHIND"
        cm_str = f"({cm[0]:7.0f},{cm[1]:7.0f})" if cm else "BEHIND"

        print(f"{i:3d} {name:<16} {hp:3d} {pos_str:<30} {rm_str:<20} {cm_str:<20}")

    mem.detach()
    print("\nTest tamamlandi.")

if __name__ == "__main__":
    main()
