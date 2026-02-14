"""
CS2 External — ESP Modülü
==========================
Entity listesini tarayarak oyuncu bilgilerini toplar.
Takım filtresi, crouch algılama, kemik hedefli aim point.
"""

import math
from utils import world_to_screen



ENTITY_STRIDE = 0x70
FL_DUCKING = (1 << 1)


class PlayerData:
    """Bir oyuncunun tüm verilerini tutar."""
    __slots__ = (
        'index', 'name', 'health', 'armor', 'team',
        'pos', 'screen_pos', 'screen_head', 'screen_aim',
        'is_visible', 'is_crouching', 'is_scoped', 'is_defusing',
        'is_enemy', 'distance', 'bones', 'address', 'start_addr', 'weapon_name'
    )

    def __init__(self):
        self.index = 0
        self.name = ""
        self.health = 0
        self.armor = 0
        self.team = 0
        self.pos = (0.0, 0.0, 0.0)
        self.screen_pos = None
        self.screen_head = None
        self.screen_aim = None
        self.is_visible = False
        self.is_crouching = False
        self.is_scoped = False
        self.is_defusing = False
        self.is_enemy = True
        self.distance = 0.0
        self.bones = [] # [(x1,y1,x2,y2), ...] çizgiler
        self.address = 0
        self.start_addr = 0
        self.weapon_name = ""


class ESP:
    """Entity tarama ve PlayerData üretimi."""

    def __init__(self, config, memory):
        self.config = config
        self.memory = memory
        self.players = []
        self.local_player = None

    def get_bone_position(self, pawn_ptr, bone_index):
        """Kemik pozisyonunu okur (Pawn -> m_modelState -> BoneArray)."""
        mem = self.memory
        cfg = self.config
        
        # Skeleton verisi Pawn'dan okunmalı, SceneNode'dan değil
        model_state = mem.read_ptr(pawn_ptr + cfg.m_modelState)
        if not model_state: return None
        
        bone_array = mem.read_ptr(model_state + cfg.bone_array_offset)
        if not bone_array: return None
        
        # 32 byte her kemik (float x, y, z ...)
        bone_addr = bone_array + bone_index * 32
        x = mem.read_float(bone_addr)
        y = mem.read_float(bone_addr + 4)
        z = mem.read_float(bone_addr + 8)
        z = mem.read_float(bone_addr + 8)
        return (x, y, z)

    def _head_bone_from_scene(self, mem, cfg, scene_node, bone_index):
        """Scene node üzerinden kafa kemiği pozisyonu (skeleton ile aynı yol)."""
        model_state_addr = scene_node + cfg.m_modelState
        bone_array = mem.read_ptr(model_state_addr + cfg.bone_array_offset)
        if not bone_array:
            return None
        bone_addr = bone_array + bone_index * 32
        x = mem.read_float(bone_addr)
        y = mem.read_float(bone_addr + 4)
        z = mem.read_float(bone_addr + 8)
        if x == 0.0 and y == 0.0 and z == 0.0:
            return None
        return (x, y, z)

    def get_entity_from_handle(self, handle):
        """Handle ile entity pointer alır. _read_player ile aynı chunk/stride yapısı kullanılır."""
        if not handle or handle == 0xFFFFFFFF:
            return 0
        index = handle & 0x7FFF
        mem = self.memory
        cfg = self.config
        client_base = mem.get_base("client.dll")
        if not client_base:
            return 0
        entity_list = mem.read_ptr(client_base + cfg.client("dwEntityList"))
        if not entity_list:
            return 0
        # ESP ile aynı yapı: chunk = entity_list + 0x10 + 8*(index>>9), entity = chunk + 0x70*(index&0x1FF)
        chunk = mem.read_ptr(entity_list + 0x10 + 8 * (index >> 9))
        if not chunk:
            return 0
        return mem.read_ptr(chunk + ENTITY_STRIDE * (index & 0x1FF))

    def _get_entity_from_handle_78(self, handle):
        """Stride 0x78 ile entity pointer (silahlar için yaygın)."""
        return self._get_entity_from_handle_stride(handle, 0x78)

    def _get_entity_from_handle_stride(self, handle, stride):
        """Belirtilen stride ile handle'dan entity pointer döner."""
        if not handle or handle == 0xFFFFFFFF:
            return 0
        index = handle & 0x7FFF
        mem = self.memory
        cfg = self.config
        client_base = mem.get_base("client.dll")
        if not client_base:
            return 0
        entity_list = mem.read_ptr(client_base + cfg.client("dwEntityList"))
        if not entity_list:
            return 0
        chunk = mem.read_ptr(entity_list + 0x10 + 8 * (index >> 9))
        if not chunk:
            return 0
        return mem.read_ptr(chunk + stride * (index & 0x1FF))

    def _is_valid_weapon_id(self, def_idx):
        """CS2'de geçerli silah/kılıç ID aralığı: 1-64 (silahlar), 31 (zeus), 500-526 (bıçaklar)."""
        if def_idx <= 0:
            return False
        if def_idx <= 64:
            return True
        if def_idx == 31:  # Zeus
            return True
        if 500 <= def_idx <= 526:
            return True
        return False

    def _read_weapon_definition_index(self, mem, cfg, weapon_ptr):
        """Silah entity'sinden m_iItemDefinitionIndex okur (uint16). Birden fazla yol dener."""
        item_idx = cfg.m_iItemDefinitionIndex
        item_offset = cfg.m_Item
        def_idx = 0

        # 1) Pointer zinciri: attr_base -> m_Item (ptr) -> C_EconItemView.m_iItemDefinitionIndex
        for attr_off in (cfg.m_WeaponAttributeManager, getattr(cfg, "_m_WeaponAttr_Econ", 4984)):
            if not attr_off:
                continue
            attr_base = weapon_ptr + attr_off
            item_view_ptr = mem.read_ptr(attr_base + item_offset)
            if item_view_ptr and item_view_ptr > 0x10000:
                raw = mem.read_bytes(item_view_ptr + item_idx, 2)
                if raw and len(raw) >= 2:
                    def_idx = int.from_bytes(raw[:2], "little") & 0xFFFF
                if not def_idx:
                    def_idx = mem.read_uint(item_view_ptr + item_idx) & 0xFFFF
                if self._is_valid_weapon_id(def_idx):
                    return def_idx
            # m_Item gömülüyse: attr_base + m_Item + m_iItemDefinitionIndex
            u = mem.read_uint(attr_base + item_offset + item_idx) & 0xFFFF
            if self._is_valid_weapon_id(u):
                return u

        # 2) C_EconItemView gömülü: weapon + 4984 + 80 + 442 = weapon + 5506
        for embedded_base in (4984 + item_offset + item_idx, 5048 + item_offset + item_idx):
            raw = mem.read_bytes(weapon_ptr + embedded_base, 2)
            if raw and len(raw) >= 2:
                def_idx = int.from_bytes(raw[:2], "little") & 0xFFFF
                if self._is_valid_weapon_id(def_idx):
                    return def_idx

        # 3) Doğrudan silah entity üzerinde yaygın offsetler
        for direct_off in (442, 0x1B8, 0x1BA, 0x1BC, 5064 + item_idx):
            raw = mem.read_bytes(weapon_ptr + direct_off, 2)
            if raw and len(raw) >= 2:
                def_idx = int.from_bytes(raw[:2], "little") & 0xFFFF
                if self._is_valid_weapon_id(def_idx):
                    return def_idx
        return 0

    def update(self) -> list:
        result = []
        # Reset local player
        self.local_player = None
        
        if not self.config.esp_enabled or not self.memory.is_attached:
            self.players = result
            return result

        mem = self.memory
        cfg = self.config
        client_base = mem.get_base("client.dll")
        if not client_base:
            self.players = result
            return result

        local_pawn = mem.read_ptr(client_base + cfg.client("dwLocalPlayerPawn"))
        if not local_pawn:
            self.players = result
            return result

        local_team = mem.read_int(local_pawn + cfg.netvar("C_BaseEntity.m_iTeamNum"))
        local_pos = mem.read_vec3(local_pawn + cfg.netvar("C_BasePlayerPawn.m_vOldOrigin"))
        view_matrix = mem.read_view_matrix(client_base + cfg.client("dwViewMatrix"))

        # Create basic local player data for Aimbot/RCS
        lp = PlayerData()
        lp.pos = local_pos
        lp.team = local_team
        lp.address = local_pawn # Pawn address
        lp.start_addr = local_pawn # Alias for RCS check
        lp.health = mem.read_int(local_pawn + cfg.netvar("C_BaseEntity.m_iHealth"))
        self.local_player = lp

        entity_list = mem.read_ptr(client_base + cfg.client("dwEntityList"))
        if not entity_list:
            self.players = result
            return result

        for i in range(1, 64):
            try:
                p = self._read_player(mem, cfg, entity_list, i,
                                      local_pawn, local_team, local_pos, view_matrix)
                if p is not None:
                    result.append(p)
            except Exception:
                continue

        # Bomba süresi (kurulu C4)
        self._update_bomb_info(mem, cfg, client_base, local_pos)

        self.players = result
        return result

    def _update_bomb_info(self, mem, cfg, client_base, local_pos):
        """Kurulu bomba varsa kalan süreyi ve tick durumunu günceller."""
        cfg.bomb_ticking = False
        cfg.bomb_remaining_sec = 0.0
        planted_addr = cfg.client("dwPlantedC4")
        if not planted_addr:
            return
        planted_ptr = mem.read_ptr(client_base + planted_addr)
        if not planted_ptr:
            return
        if mem.read_bool(planted_ptr + cfg.netvar("C_PlantedC4.m_bHasExploded")):
            return
        if not mem.read_bool(planted_ptr + cfg.netvar("C_PlantedC4.m_bBombTicking")):
            return
        cfg.bomb_ticking = True
        blow_time = mem.read_float(planted_ptr + cfg.netvar("C_PlantedC4.m_flC4Blow"))
        global_vars_addr = client_base + cfg.client("dwGlobalVars")
        curtime = mem.read_float(global_vars_addr + getattr(cfg, "GLOBALVARS_CURTIME_OFFSET", 0x10))
        cfg.bomb_remaining_sec = max(0.0, blow_time - curtime)

    def _read_player(self, mem, cfg, entity_list, index,
                     local_pawn, local_team, local_pos, view_matrix):

        chunk = mem.read_ptr(entity_list + 0x10 + 8 * (index >> 9))
        if not chunk:
            return None

        # ENTITY_STRIDE is back to 0x70 as requested
        controller = mem.read_ptr(chunk + ENTITY_STRIDE * (index & 0x1FF))
        if not controller or controller < 0x10000:
            return None

        pawn_handle = mem.read_uint(controller + cfg.netvar("CCSPlayerController.m_hPlayerPawn"))
        if not pawn_handle or pawn_handle == 0xFFFFFFFF:
            return None

        pawn_idx = pawn_handle & 0x7FFF
        pawn_chunk = mem.read_ptr(entity_list + 0x10 + 8 * (pawn_idx >> 9))
        if not pawn_chunk:
            return None

        pawn = mem.read_ptr(pawn_chunk + ENTITY_STRIDE * (pawn_idx & 0x1FF))
        if not pawn or pawn == local_pawn:
            return None

        team = mem.read_int(pawn + cfg.netvar("C_BaseEntity.m_iTeamNum"))
        is_enemy = (team != local_team)

        # Takım filtresi — team_check açıksa sadece düşmanları göster
        if cfg.esp_team_check and not is_enemy:
            return None

        health = mem.read_int(pawn + cfg.netvar("C_BaseEntity.m_iHealth"))
        if health <= 0 or health > 100:
            return None

        scene_node = mem.read_ptr(pawn + cfg.netvar("C_BaseEntity.m_pGameSceneNode"))
        if not scene_node:
            return None

        pos = mem.read_vec3(scene_node + cfg.netvar("CGameSceneNode.m_vecAbsOrigin"))
        if pos[0] == 0.0 and pos[1] == 0.0 and pos[2] == 0.0:
            return None

        flags = mem.read_uint(pawn + cfg.netvar("C_BaseEntity.m_fFlags"))
        is_crouching = bool(flags & FL_DUCKING)
        is_scoped = mem.read_bool(pawn + cfg.netvar("C_CSPlayerPawn.m_bIsScoped"))
        is_defusing = mem.read_bool(pawn + cfg.netvar("C_CSPlayerPawn.m_bIsDefusing"))

        spotted_addr = pawn + cfg.netvar("C_CSPlayerPawn.m_entitySpottedState")
        spotted_offset = cfg.netvar("EntitySpottedState_t.m_bSpotted")
        
        is_visible = mem.read_bool(spotted_addr + spotted_offset)
        
        if cfg.radar_hack_enabled:
            # Sadece düşmansa ve mapte görünmüyorsa force et
            if is_enemy and not is_visible:
                 mem.write_bool(spotted_addr + spotted_offset, True)
                 is_visible = True

        armor = mem.read_int(pawn + cfg.netvar("C_CSPlayerPawn.m_ArmorValue"))
        armor = max(0, armor) if 0 <= armor <= 100 else 0

        dx = pos[0] - local_pos[0]
        dy = pos[1] - local_pos[1]
        dz = pos[2] - local_pos[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)

        head_offset = 72.0 if not is_crouching else 54.0
        aim_offset = cfg.get_bone_offset(is_crouching)
        # Gerçek kafa kemiği (flick/aimbot doğruluğu); önce pawn sonra scene_node dene
        head_id = cfg.bones.get("head", 6)
        head_bone_world = self.get_bone_position(pawn, head_id)
        if not head_bone_world:
            head_bone_world = self._head_bone_from_scene(mem, cfg, scene_node, head_id)
        head_pos = head_bone_world if head_bone_world else (pos[0], pos[1], pos[2] + head_offset)
        aim_pos  = (pos[0], pos[1], pos[2] + aim_offset)

        screen_feet = world_to_screen(pos, view_matrix, cfg.screen_width, cfg.screen_height)
        screen_head = world_to_screen(head_pos, view_matrix, cfg.screen_width, cfg.screen_height)
        screen_aim  = world_to_screen(aim_pos, view_matrix, cfg.screen_width, cfg.screen_height)

        if screen_feet is None and screen_head is None:
            return None

        # ── Skeleton Okuma ──
        bone_lines = []
        if cfg.skeleton_enabled and distance < 8000:
            # Tüm kemiklerin ekran pozisyonlarını hesapla
            screen_bones = {}
            # m_modelState bir STRUCT, pointer değil. O yüzden adresi topluyoruz.
            model_state_addr = scene_node + cfg.m_modelState
            
            # BoneArray pointer'ı CModelState + 0x80 (bone_array_offset) adresinde
            bone_array = mem.read_ptr(model_state_addr + cfg.bone_array_offset)
            
            if bone_array:
                    for b_name, b_id in cfg.bones.items():
                         # 32 byte stride
                        bone_addr = bone_array + b_id * 32
                        bx = mem.read_float(bone_addr)
                        by = mem.read_float(bone_addr + 4)
                        bz = mem.read_float(bone_addr + 8)
                        
                        s_pos = world_to_screen((bx, by, bz), view_matrix, cfg.screen_width, cfg.screen_height)
                        if s_pos:
                            screen_bones[b_name] = s_pos
            
            for b1, b2 in cfg.bone_connections:
                if b1 in screen_bones and b2 in screen_bones:
                    bone_lines.append( (screen_bones[b1], screen_bones[b2]) )

        # ── Weapon Okuma (pointer zinciri: Pawn -> WeaponServices -> Handle -> Weapon -> ItemView -> ItemDefinitionIndex) ──
        weapon_name = ""
        show_weapon = (is_enemy and cfg.esp_weapon_enemies) or (not is_enemy and cfg.esp_weapon_team)
        
        if show_weapon:
            weapon_services = mem.read_ptr(pawn + cfg.m_pWeaponServices)
            if weapon_services:
                weapon_handle = mem.read_uint(weapon_services + cfg.m_hActiveWeapon)
                if (not weapon_handle or weapon_handle == 0xFFFFFFFF) and cfg.m_hActiveWeapon <= 98:
                    raw2 = mem.read_bytes(weapon_services + cfg.m_hActiveWeapon, 2)
                    if raw2 and len(raw2) >= 2:
                        weapon_handle = int.from_bytes(raw2[:2], "little") & 0xFFFF
                if weapon_handle and weapon_handle != 0xFFFFFFFF:
                    # Birden fazla stride dene (0x78, 0x70, 0x80) — farklı oyuncular farklı listelerde olabilir
                    weapon_ptr = 0
                    for stride in (0x78, ENTITY_STRIDE, 0x80):
                        weapon_ptr = self._get_entity_from_handle_stride(weapon_handle, stride)
                        if weapon_ptr and weapon_ptr >= 0x10000:
                            break
                    if not weapon_ptr or weapon_ptr < 0x10000:
                        weapon_ptr = self.get_entity_from_handle(weapon_handle)
                    # Handle bazen 16-bit; düşük 16 bit ile de dene
                    if (not weapon_ptr or weapon_ptr < 0x10000) and weapon_handle & 0xFFFF:
                        low = weapon_handle & 0xFFFF
                        for stride in (0x78, ENTITY_STRIDE, 0x80):
                            weapon_ptr = self._get_entity_from_handle_stride(low, stride)
                            if weapon_ptr and weapon_ptr >= 0x10000:
                                break
                    if weapon_ptr and weapon_ptr >= 0x10000:
                        def_idx = self._read_weapon_definition_index(mem, cfg, weapon_ptr)
                        if def_idx and self._is_valid_weapon_id(def_idx):
                            weapon_name = cfg.weapon_names.get(def_idx, "")
                            if not weapon_name:
                                weapon_name = f"#{def_idx}"

        name_ptr = mem.read_ptr(controller + cfg.netvar("CCSPlayerController.m_sSanitizedPlayerName"))
        name = ""
        if name_ptr:
            name = mem.read_string(name_ptr, 64)
        if not name:
            name = mem.read_string(controller + cfg.netvar("CBasePlayerController.m_iszPlayerName"), 64)

        p = PlayerData()
        p.index = index
        p.name = name if name else f"Player {index}"
        p.health = health
        p.armor = armor
        p.team = team
        p.pos = pos
        p.screen_pos = screen_feet
        p.screen_head = screen_head
        p.screen_aim = screen_aim
        p.is_visible = is_visible
        p.is_crouching = is_crouching
        p.is_scoped = is_scoped
        p.is_defusing = is_defusing
        p.is_enemy = is_enemy
        p.distance = distance
        p.distance = distance
        p.bones = bone_lines
        p.weapon_name = weapon_name

        return p