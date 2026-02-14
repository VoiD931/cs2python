"""
CS2 External — Konfigürasyon Modülü
=====================================
Tüm offset'leri JSON'dan yükler, ayarları merkezi olarak yönetir.
"""

from utils import get_screen_resolution


class Config:
    """Merkezi konfigürasyon sınıfı."""

    def __init__(self):
        self.process_name = "cs2.exe"
        
        # ── Offset Loader ──
        from offset_loader import get_loader
        loader = get_loader()

        # ── Client Offsets (offsets.json) ──
        self.client_offsets = {}
        self.client_offsets["dwEntityList"] = loader.get_client_offset("dwEntityList")
        self.client_offsets["dwLocalPlayerPawn"] = loader.get_client_offset("dwLocalPlayerPawn") 
        self.client_offsets["dwViewMatrix"] = loader.get_client_offset("dwViewMatrix")
        self.client_offsets["dwViewAngles"] = loader.get_client_offset("dwViewAngles")
        self.client_offsets["dwCSGOInput"] = loader.get_client_offset("dwCSGOInput")
        self.client_offsets["dwGlobalVars"] = loader.get_client_offset("dwGlobalVars")
        self.client_offsets["dwLocalPlayerController"] = loader.get_client_offset("dwLocalPlayerController")
        self.client_offsets["dwSensitivity"] = loader.get_client_offset("dwSensitivity")
        self.client_offsets["dwSensitivity_sensitivity"] = loader.get_client_offset("dwSensitivity_sensitivity") or 88
        self.client_offsets["dwPlantedC4"] = loader.get_client_offset("dwPlantedC4")

        # CGlobalVars: curtime (oyun zamanı) — Source2'de genelde +0x10
        self.GLOBALVARS_CURTIME_OFFSET = 0x10

        # ── NetVars (client_dll.json) ──
        self.netvars = {}
        
        # Helper to cleaner loading
        def nv(key, cls, field):
            self.netvars[key] = loader.get_netvar(cls, field)

        # Temel Entity
        nv("C_BaseEntity.m_iTeamNum", "C_BaseEntity", "m_iTeamNum")
        nv("C_BaseEntity.m_iHealth", "C_BaseEntity", "m_iHealth")
        nv("C_BaseEntity.m_fFlags", "C_BaseEntity", "m_fFlags")
        nv("C_BaseEntity.m_pGameSceneNode", "C_BaseEntity", "m_pGameSceneNode")
        
        # Player Pawn
        nv("C_BasePlayerPawn.m_vOldOrigin", "C_BasePlayerPawn", "m_vOldOrigin")
        nv("C_CSPlayerPawn.m_iIDEntIndex", "C_CSPlayerPawn", "m_iIDEntIndex")
        nv("C_CSPlayerPawn.m_ArmorValue", "C_CSPlayerPawn", "m_ArmorValue")
        nv("C_CSPlayerPawn.m_bIsScoped", "C_CSPlayerPawn", "m_bIsScoped")
        nv("C_CSPlayerPawn.m_bIsDefusing", "C_CSPlayerPawn", "m_bIsDefusing")
        nv("C_CSPlayerPawn.m_bIsDefusing", "C_CSPlayerPawn", "m_bIsDefusing")
        nv("C_CSPlayerPawn.m_entitySpottedState", "C_CSPlayerPawn", "m_entitySpottedState")
        nv("C_CSPlayerPawn.m_aimPunchAngle", "C_CSPlayerPawn", "m_aimPunchAngle")
        nv("C_CSPlayerPawn.m_iShotsFired", "C_CSPlayerPawn", "m_iShotsFired")
        
        # Node & Bone
        nv("CGameSceneNode.m_vecAbsOrigin", "CGameSceneNode", "m_vecAbsOrigin")
        
        # Controller
        nv("CCSPlayerController.m_hPlayerPawn", "CCSPlayerController", "m_hPlayerPawn")
        nv("CCSPlayerController.m_sSanitizedPlayerName", "CCSPlayerController", "m_sSanitizedPlayerName")
        
        # Spotted State Struct
        nv("EntitySpottedState_t.m_bSpotted", "EntitySpottedState_t", "m_bSpotted")
        # FOV (oyun görüş açısı)
        nv("CBasePlayerController.m_iDesiredFOV", "CBasePlayerController", "m_iDesiredFOV")
        # Bomba (C4)
        nv("C_PlantedC4.m_flC4Blow", "C_PlantedC4", "m_flC4Blow")
        nv("C_PlantedC4.m_bBombTicking", "C_PlantedC4", "m_bBombTicking")
        nv("C_PlantedC4.m_bHasExploded", "C_PlantedC4", "m_bHasExploded")
        # Sahipsiz entity (yere atılan silah)
        nv("C_BaseEntity.m_hOwnerEntity", "C_BaseEntity", "m_hOwnerEntity")
        
        # Flashbang Duration
        nv("C_CSPlayerPawnBase.m_flFlashDuration", "C_CSPlayerPawnBase", "m_flFlashDuration")

        # ── Ekran ──
        sw, sh = get_screen_resolution()
        self.screen_width  = sw
        self.screen_height = sh

        # ══════════════════════════════════
        #  ESP
        # ══════════════════════════════════
        self.esp_enabled       = True
        self.esp_box           = True
        self.esp_health_bar    = True
        self.esp_name          = True
        self.esp_distance      = True
        self.esp_snaplines     = False
        self.esp_team_check    = True # Enemy Only default
        self.obs_bypass        = True
        self.esp_radar         = False   # 2D radar (üstten görünüm)
        self.radar_radius      = 65      # piksel
        self.radar_scale        = 0.028  # dünya birimi -> radar piksel (küçük = daha uzak görünür)
        self.local_position    = None    # her frame güncellenir (x,y,z)
        self.overlay_show_fps  = False
        self.overlay_show_enemy_count = False
        self.esp_bomb_timer     = True   # Kurulu bomba kalan süre
        self.bomb_remaining_sec = 0.0    # ESP tarafından güncellenir
        self.bomb_ticking       = False
        self.crosshair_style   = 0   # 0=çarpı, 1=nokta, 2=daire
        self.crosshair_size    = 6
        self.crosshair_gap     = 2
        self.aim_auto_focus = False # En yakın düşmana odaklan (FOV dışı olsa bile)
        self.aim_auto_dist = 500.0  # Auto-focus mesafe limiti
        
        # Flick Aimbot (Headshot Trigger)
        self.flick_enabled = False
        self.flick_fov = 15.0      # Daha dar bir alan
        self.flick_key = 0x01      # VK_LBUTTON (Sol Tık)
        self.flick_smooth = 1.0    # Çok hızlı (neredeyse instant)
        self.flick_bone = 6        # Head
        
        # ══════════════════════════════════
        #  Bones & Connections
        # ══════════════════════════════════
        self.aim_enabled    = True
        self.aim_key        = 0x02      # VK_RBUTTON
        self.aim_fov        = 5.0
        self.aim_fov_circle = True
        self.aim_fov_color  = [130, 80, 255] # Default Purple
        self.aim_smoothness = 12.0 # Increased for smoother tracking
        self.aim_team_check = True
        self.aim_auto_focus = False
        self.aim_auto_dist  = 300.0
        self.aim_max_distance = 80.0       # Metre cinsinden üst sınır (sadece açıksa uygulanır)
        self.aim_max_distance_enabled = False  # False = sınır yok (tüm FOV içi), True = sadece X m içindekiler
        self.aim_bone       = "head"

        # RCS (Recoil Control)
        self.rcs_enabled = False
        self.rcs_scale_x = 2.0
        self.rcs_scale_y = 2.0
        self.rcs_start_bullet = 1


        self.bone_offsets = {"head": 65.0, "neck": 60.0, "chest": 45.0}
        self.bone_offset_crouching = {"head": 50.0, "neck": 46.0, "chest": 34.0}

        # ══════════════════════════════════
        #  Skeleton ESP Config
        # ══════════════════════════════════
        self.skeleton_enabled = False
        
        # Load m_modelState dynamically
        # CSkeletonInstance -> m_modelState
        self.m_modelState = loader.get_netvar("CSkeletonInstance", "m_modelState") 
        if self.m_modelState == 0:
            self.m_modelState = 0x160 # Fallback
            
        self.bone_array_offset = 0x80 # Usually static in CModelState
        
        # Bone Indices (CS2 Standard)
        self.bones = {
            'head': 6, 'neck': 5, 'spine': 4, 'pelvis': 0,
            'l_shoulder': 13, 'l_arm': 8, 'l_hand': 9,
            'r_shoulder': 18, 'r_arm': 13, 'r_hand': 14, # 13 might be wrong for R, check standard
            'l_hip': 22, 'l_knee': 23, 'l_foot': 24,
            'r_hip': 25, 'r_knee': 26, 'r_foot': 27
        }
        # Correcting right arm chain based on common CS2 dumps:
        # arm_upper_R=13?, usually it is:
        # 8=arm_upper_L, 9=arm_lower_L, 10=hand_L
        # 13=arm_upper_R, 14=arm_lower_R, 15=hand_R
        # Let's use a safer set.
        self.bones = {
            'head': 6, 'neck': 5, 'spine': 4, 'pelvis': 0,
            'l_shoulder': 8, 'l_eblow': 9, 'l_hand': 10,
            'r_shoulder': 13, 'r_elbow': 14, 'r_hand': 15,
            'l_hip': 22, 'l_knee': 23, 'l_feet': 24,
            'r_hip': 25, 'r_knee': 26, 'r_feet': 27
        }

        self.bone_connections = [
            ('head', 'neck'),
            ('neck', 'spine'),
            ('spine', 'pelvis'),
            ('neck', 'l_shoulder'), ('l_shoulder', 'l_eblow'), ('l_eblow', 'l_hand'),
            ('neck', 'r_shoulder'), ('r_shoulder', 'r_elbow'), ('r_elbow', 'r_hand'),
            ('pelvis', 'l_hip'), ('l_hip', 'l_knee'), ('l_knee', 'l_feet'),
            ('pelvis', 'r_hip'), ('r_hip', 'r_knee'), ('r_knee', 'r_feet')
        ]
        
        # ══════════════════════════════════
        #  Weapon ESP Config
        # ══════════════════════════════════
        self.esp_weapon_enemies = True
        self.esp_weapon_team    = True
        
        # Silah offset'leri (client_dll.json ile; silah pointer zinciri için)
        # Pawn -> m_pWeaponServices (C_CSPlayerPawn / C_CSPlayerPawnBase)
        self.m_pWeaponServices = loader.get_netvar("C_CSPlayerPawn", "m_pWeaponServices") or loader.get_netvar("C_CSPlayerPawnBase", "m_pWeaponServices") or 5080
        # CPlayer_WeaponServices -> m_hActiveWeapon
        self.m_hActiveWeapon = loader.get_netvar("CPlayer_WeaponServices", "m_hActiveWeapon") or 96
        # Silah entity: C_CSWeaponBaseGun=5048, C_EconEntity=4984 (fallback)
        self.m_WeaponAttributeManager = loader.get_netvar("C_CSWeaponBaseGun", "m_AttributeManager") or 5048
        self._m_WeaponAttr_Econ = loader.get_netvar("C_EconEntity", "m_AttributeManager") or 4984
        # C_AttributeContainer -> m_Item (pointer)
        self.m_Item = loader.get_netvar("C_AttributeContainer", "m_Item") or 80
        # C_EconItemView -> m_iItemDefinitionIndex (uint16)
        self.m_iItemDefinitionIndex = loader.get_netvar("C_EconItemView", "m_iItemDefinitionIndex") or 442
        # Eski kod uyumluluğu (bazı modüllerde m_AttributeManager kullanılıyor)
        self.m_AttributeManager = self.m_WeaponAttributeManager
        
        self.weapon_names = {
            1: "DESERT EAGLE", 2: "DUAL BERETTAS", 3: "FIVE-SEVEN", 4: "GLOCK", 
            7: "AK-47", 8: "AUG", 9: "AWP", 10: "FAMAS", 11: "G3SG1", 13: "GALIL AR", 
            14: "M249", 16: "M4A4", 17: "MAC-10", 19: "P90", 23: "MP5-SD", 24: "UMP-45", 
            25: "XM1014", 26: "BIZON", 27: "MAG-7", 28: "NEGEV", 29: "SAWED-OFF", 
            30: "TEC-9", 31: "ZEUS", 32: "P2000", 33: "MP7", 34: "MP9", 35: "NOVA", 
            36: "P250", 38: "SCAR-20", 39: "SG 553", 40: "SSG 08", 42: "KNIFE", 
            43: "FLASHBANG", 44: "HE GRENADE", 45: "SMOKE", 46: "MOLOTOV", 
            47: "DECOY", 48: "INCENDIARY", 49: "C4", 59: "KNIFE", 60: "M4A1-S", 
            61: "USP-S", 63: "CZ75-AUTO", 64: "R8 REVOLVER", 500: "BAYONET", 
            503: "CLASSIC KNIFE", 505: "FLIP KNIFE", 506: "GUT KNIFE", 507: "KARAMBIT", 
            508: "M9 BAYONET", 509: "HUNTSMAN", 512: "FALCHION", 514: "BOWIE", 
            515: "BUTTERFLY", 516: "DAGGERS", 519: "URSUS", 520: "NAVAJA", 
            522: "STILETTO", 523: "TALON", 525: "SKELETON KNIFE", 526: "KUKRI"
        }

        # ══════════════════════════════════
        #  Triggerbot
        # ══════════════════════════════════
        self.trigger_enabled   = False
        self.trigger_delay_ms  = 60
        self.trigger_auto      = False

        # ══════════════════════════════════
        #  Bhop
        # ══════════════════════════════════
        self.bhop_enabled = False
        self.bhop_key     = 0x20        # VK_SPACE

        # ══════════════════════════════════
        #  Spinbot (Mevlana)
        # ══════════════════════════════════
        self.spin_enabled  = False
        self.spin_speed    = 30.0
        self.spin_key      = 0x58       # VK_X

        # ══════════════════════════════════
        #  No Flash & Radar
        # ══════════════════════════════════
        self.no_flash_enabled = False
        self.radar_hack_enabled = False

        # ══════════════════════════════════
        #  Skeleton ESP
        # ══════════════════════════════════
        self.skeleton_enabled = False
        self.skeleton_color   = (255, 255, 255) # Beyaz
        
        # Offsets
        self.m_modelState = loader.get_netvar("CSkeletonInstance", "m_modelState") 
        self.m_pGameSceneNode = loader.get_netvar("C_BaseEntity", "m_pGameSceneNode")
        self.bone_array_offset = 0x80 # Hardcoded common offset


        # Bone IDs (CS2)
        self.bones = {
            "head": 6, "neck": 5, "spine": 4, "spine_1": 2,
            "shoulder_l": 13, "arm_l": 14, "hand_l": 16,
            "shoulder_r": 8, "arm_r": 9, "hand_r": 11,
            "hip_l": 22, "knee_l": 23, "foot_l": 24,
            "hip_r": 25, "knee_r": 26, "foot_r": 27
        }
        self.bone_connections = [
            ("head", "neck"), ("neck", "spine"), ("spine", "spine_1"),
            ("neck", "shoulder_l"), ("shoulder_l", "arm_l"), ("arm_l", "hand_l"),
            ("neck", "shoulder_r"), ("shoulder_r", "arm_r"), ("arm_r", "hand_r"),
            ("spine_1", "hip_l"), ("hip_l", "knee_l"), ("knee_l", "foot_l"),
            ("spine_1", "hip_r"), ("hip_r", "knee_r"), ("knee_r", "foot_r")
        ]

        self.spin_check_shoot = True

        # ══════════════════════════════════
        #  Oyun FOV (görüş açısı)
        # ══════════════════════════════════
        self.game_fov_enabled = False
        self.game_fov_value = 90

        # ══════════════════════════════════
        #  Viewmodel FOV (el/silah görüş açısı)
        # ══════════════════════════════════
        self.viewmodel_fov_enabled = False
        self.viewmodel_fov_value = 68
        
        # Hardcoded fallback offsets for Viewmodel if not in JSON
        self.m_pViewModelServices = 0x1420 # C_CSPlayerPawn
        self.m_hViewModel = 0x40           # CCSPlayer_ViewModelServices
        self.m_hPlayerPawn = 2316          # CCSPlayerController::m_hPlayerPawn
        # Backup: Direct handle offset from Pawn (found by scanning)
        self.viewmodel_handle_offset = 0x3ECC
        self.viewmodel_fov_enabled = False
        self.viewmodel_fov_value = 68
        # C_CSPlayerPawn / C_BasePlayerPawn; birden fazla olası offset (build farkı)
        self.m_flViewmodelFOV = (
            loader.get_netvar("C_CSPlayerPawn", "m_flViewmodelFOV")
            or loader.get_netvar("C_BasePlayerPawn", "m_flViewmodelFOV")
            or 9252
        )
        self._viewmodel_fov_offsets = [9252, 0x2424]

    # ── Hızlı erişim ──

    def get_bone_offset(self, is_crouching: bool) -> float:
        offsets = self.bone_offset_crouching if is_crouching else self.bone_offsets
        return offsets.get(self.aim_bone, 65.0)

    def client(self, key: str) -> int:
        return self.client_offsets.get(key, 0)

    def netvar(self, key: str) -> int:
        return self.netvars.get(key, 0)

    @property
    def m_flFlashDuration(self):
        return self.netvars.get("C_CSPlayerPawnBase.m_flFlashDuration", 5624)
    