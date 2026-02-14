import time
import struct

class Glow:
    def __init__(self, config, memory):
        self.config = config
        self.memory = memory

    def update(self):
        if not self.config.glow_enabled or not self.memory.is_attached:
            return

        client_base = self.memory.get_base("client.dll")
        if not client_base: return

        entity_list = self.memory.read_ptr(client_base + self.config.client("dwEntityList"))
        local_pawn = self.memory.read_ptr(client_base + self.config.client("dwLocalPlayerPawn"))
        if not entity_list or not local_pawn: return

        local_team = self.memory.read_int(local_pawn + self.config.netvar("C_BaseEntity.m_iTeamNum"))

        # Loop through entities (Players)
        for i in range(1, 64):
            try:
                # 1. Get Controller
                list_entry = self.memory.read_ptr(entity_list + (8 * (i & 0x7FFF) >> 9) + 16)
                if not list_entry: continue
                
                controller = self.memory.read_ptr(list_entry + 120 * (i & 0x1FF))
                if not controller or controller == 0: continue
                
                # 2. Get Pawn Handle
                pawn_handle = self.memory.read_uint(controller + self.config.netvar("CCSPlayerController.m_hPlayerPawn"))
                if pawn_handle == 0xFFFFFFFF: continue
                
                # 3. Get Pawn
                list_entry2 = self.memory.read_ptr(entity_list + 0x8 * ((pawn_handle & 0x7FFF) >> 9) + 16)
                if not list_entry2: continue
                
                pawn = self.memory.read_ptr(list_entry2 + 120 * (pawn_handle & 0x1FF))
                if not pawn or pawn == local_pawn: continue

                # 4. Check Team
                team = self.memory.read_int(pawn + self.config.netvar("C_BaseEntity.m_iTeamNum"))
                is_enemy = (team != local_team)

                if self.config.glow_team_check and not is_enemy:
                    continue

                # 5. Check Life State (Health > 0)
                health = self.memory.read_int(pawn + self.config.netvar("C_BaseEntity.m_iHealth"))
                if health <= 0: continue

                # 6. Apply Glow (Write Memory)
                
                # Determine Color
                color = self.config.glow_enemy_color if is_enemy else self.config.glow_team_color
                
                # Color is [R, G, B] floats 0-1
                # CS2 Glow Struct (GlowColorOverride): R (float), G (float), B (float), A (float)
                # Offset: m_glowColorOverride = 0x40 + m_Glow (0xC00 usually)
                
                # IMPORTANT: These offsets must be verified. 
                # Using the ones from config: GLOW_OFFSET, GLOW_COLOR_OFFSET
                
                # m_Glow (0xC00) -> m_glowColorOverride (0x40) + m_bGlowing (0x51)
                
                # Calculate address
                glow_base = pawn + self.config.GLOW_OFFSET
                
                # Create byte array for color (R, G, B, A=1.0)
                # struct.pack('ffff') -> 16 bytes
                color_data = struct.pack('ffff', color[0], color[1], color[2], 1.0)
                
                # Create byte array for enable (bool) -> 1 byte
                enable_data = struct.pack('?', True)

                # Write Color
                self.memory.write_bytes(glow_base + self.config.GLOW_COLOR_OFFSET, color_data)
                
                # Write Enable
                self.memory.write_bytes(glow_base + self.config.GLOW_ENABLE_OFFSET, enable_data)
                
                # Optional: Handle m_iGlowType if needed (usually not needed if just overriding color, but standard is 1)
                # self.memory.write_int(glow_base + self.config.GLOW_TYPE_OFFSET, 1)

            except Exception:
                continue
