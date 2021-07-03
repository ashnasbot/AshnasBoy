class Reg():
    # TODO: move into cpu

    def __init__(self):
        self.A = 1
        self.B = 0
        self.C = 20
        self.D = 0
        self.E = 0
        # Registers
        self.PC = 0
        self.SP = 0
        #self._HL = bytearray(2)
        self.H = 0
        self.L = 0
        # Flags
        self.fZ = True
        self.fN = False
        self.fH = False
        self.fC = False
        # internal flags
        self.HALT = False
        self.STOP = False
        self.IME = False

    def __str__(self):
        return f"""A: {self.A:02X}
        BC: {self.BC:04X}
        DE: {self.DE:04X}
        HL: {self.HL:04X}
        Z:{self.fZ} N:{self.fN} H:{self.fH} C:{self.fC}"""

    @property
    def F(self):
        return (int(self.fZ) << 7) + (int(self.fN) << 6) + (int(self.fH) << 5) + (int(self.fC) << 4)

    @property
    def strF(self):
        return f'{"Z" if self.fZ else "_"}{"N" if self.fN else "_"}{"H" if self.fH else "_"}{"C" if self.fC else "_"}'

    @F.setter
    def F(self, value):
        self.fZ = value & (1 << 7) != 0
        self.fN = value & (1 << 6) != 0
        self.fH = value & (1 << 5) != 0
        self.fC = value & (1 << 4) != 0

    @property
    def AF(self):
        return (self.A << 8) + self.F

    @AF.setter
    def AF(self, value):
        a, f = value.to_bytes(2, byteorder='big')
        self.A = a
        self.F = f

    @property
    def BC(self):
        return (self.B << 8) + self.C

    @BC.setter
    def BC(self, value):
        self.B = (value & 0xFF00) >> 8
        self.C = value & 0x00FF

    @property
    def DE(self):
        return (self.D << 8) + self.E

    @DE.setter
    def DE(self, value):
        self.D = (value & 0xFF00) >> 8
        self.E = value & 0x00FF

    @property
    def HL(self):
        return (self.H << 8) + self.L

    @HL.setter
    def HL(self, value):
        self.H = value >> 8
        self.L = value & 0x00FF

    def __str__(self):
        return f"A:{self.A:02X} F:{self.strF} BC:{self.BC:04X} DE:{self.DE:04X} HL:{self.HL:04X} SP:{self.SP:04X} PC:{self.PC:04X}"


class LCDC:
    def __init__(self):
        self._byte = 0xF0
        self.screen_on          = True
        self.windowmap_select   = False
        self.window_enable      = False
        self.tile_data_select   = False
        self.bg_tile_map_select = False
        self.sprite_height      = False
        self.sprite_enable      = False
        self.bg_enable          = False

    @property
    def value(self):
        return self._byte

    @value.setter    
    def value(self, val):
        self._byte = val

        self.screen_on          = val & 0b10000000  # 7
        self.windowmap_select   = val & 0b01000000  # 6
        self.window_enable      = val & 0b00100000  # 5
        self.tile_data_select   = val & 0b00010000  # 4
        self.bg_tile_map_select = val & 0b00001000  # 3
        self.sprite_height      = val & 0b00000100  # 2
        self.sprite_enable      = val & 0b00000010  # 1
        self.bg_enable          = val & 0b00000001  # 0

class STAT:
    def __init__(self):
        self._byte = 0x00
        self.lyc_eq_ly_enabled    = False
        self.mode_2_OAM_enable    = False
        self.mode_1_vblank_enable = False
        self.mode_0_hblank_enable = False
        self.lyc_eq_ly            = False
        self.mode                 = 0

    @property
    def value(self):
        return self._byte

    @value.setter    
    def value(self, val):
        self._byte = val & 0b01111111

        self.lyc_eq_ly_enabled    = val & 0b01000000  # 6
        self.mode_2_OAM_enable    = val & 0b00100000  # 5
        self.mode_1_vblank_enable = val & 0b00010000  # 4
        self.mode_0_hblank_enable = val & 0b00001000  # 3
        self.lyc_eq_ly            = val & 0b00000100  # 2
        self.mode                 = val & 0b00000011  # 0-1