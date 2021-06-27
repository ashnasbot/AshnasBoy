from enum import Enum, auto
import sys

# I/O Registers
IE  = 0xFFFF
DIV = 0xFF04 
TIMA= 0xFF05
TMA = 0xFF06
TAC = 0xFF07
IF  = 0xFF0F
LY  = 0xFF44

# Flags
class MBC_MODE(Enum):
    ROM = auto()
    RAM = auto()

class MMU():

    #0000	3FFF	16KB ROM bank 00	From cartridge, usually a fixed bank
    #4000	7FFF	16KB ROM Bank 01~NN	From cartridge, switchable bank via MBC (if any)
    #8000	9FFF	8KB Video RAM (VRAM)	Only bank 0 in Non-CGB mode
    #Switchable bank 0/1 in CGB mode
    #
    #A000	BFFF	8KB External RAM	In cartridge, switchable bank if any
    #C000	CFFF	4KB Work RAM (WRAM) bank 0	
    #D000	DFFF	4KB Work RAM (WRAM) bank 1~N	Only bank 1 in Non-CGB mode
    #Switchable bank 1~7 in CGB mode
    #
    #E000	FDFF	Mirror of C000~DDFF (ECHO RAM)	Typically not used
    #FE00	FE9F	Sprite attribute table (OAM)	
    #FEA0	FEFF	Not Usable	
    #FF00	FF7F	I/O Registers	
    #FF80	FFFE	High RAM (HRAM)	
    #FFFF	FFFF	Interrupts Enable Register (IE)

    def __init__(self, interface):
        self._interface = interface

        self.mem = bytearray(65536)
        view = memoryview(self.mem)
        self._rom = []
        self._rom0  = view[0:0x4000]
        self._rom1  = view[0x4000:0x8000]
        self._vram  = view[0x8000:0xA000]
        self._eram  = view[0xA000:0xC000]
        self._wram  = view[0xC000:0xE000]
        self._wram2 = view[0xE000:0xFE00]
        self.OAM    = view[0xFE00:0xFEA0]
        self.IO     = view[0xFF00:0xFF80]
        self._HiRAM = view[0xFF80:0xFFFF]
        self._IE     = view[0xFFFF]
        #with open("roms/07-jr.gb", "r+b") as f:
        #with open("roms/tetris.gb", "r+b") as f:
        #with open("roms/Dr.Mario.gb", "r+b") as f:
        with open("roms/zaldo.gb", "r+b") as f:
        #with open("roms/poke.gb", "r+b") as f:
            # Read first two banks
            # TODO: Read $0x148 and determine ROM Size
            while True:
                bank = bytearray(0x4000)
                if f.readinto(bank) == 0:
                    break
                self._rom.append(bank)

        self._rom0[:] = self._rom[0]
        if len(self._rom) > 1:
            self._rom1[:] = self._rom[1]
        
        self.view = view

        self.mem[65535] = 0xFF  # IE

        self.link_buffer = 0
        self._FF = [0xFF for _ in range(256)]

        self.serial_buff = ""
        # MBC
        self.mbc_mode = MBC_MODE.ROM
        self.mbc_upper_bank = 0
        # TODO: Read $0x147 and determine MBC ($01 = MBC1)
        self._io_handlers = {}


    def __getitem__(self, val):
        if val < 0xE000:
            return self.view[val]
        elif val < 0xFE00:
            return self.view[val-0x2000]
        elif val < 0xFE80:
            return self.OAM[val-0xFE00]
        elif val < 0xFF00:
            return 0xFF
        elif val < 0xFF80:
            if val in self._io_handlers:
                return self._io_handlers[val].value
            elif val == 0xFF00:
                return self._interface.input
            else:
                return self.IO[val-0xFF00]
        elif val < 0xFFFF:
            return self._HiRAM[val-0xFF80]
        elif val == 0xFFFF:
            return self.IE
        raise ValueError("Access out of bounds")

    def __setitem__(self, key, val):
        if key < 0x8000:
            # ROM Write - MBC
            if key < 0x2000:  # RAM Gate
                # TODO: enable/disable RAM
                pass
                1 == 1
            elif key < 0x4000:  # MBC1 Bank 1
                bank = val & 0b00011111    # Bit 7-5 ignored

                if bank == 0:
                    bank = 1
                bank += self.mbc_upper_bank
                self._rom1[:] = self._rom[bank % len(self._rom)]
            elif key < 0x6000:  # RAM Bank Number / Upper Bits of ROM Bank no
                if self.mbc_mode == MBC_MODE.ROM:
                    self.mbc_upper_bank = (val & 0x03) << 5
                else:
                    pass
            else:  ## ROM/RAM Mode select
                mode = val & 0x01
                if mode:
                    self.mbc_mode = MBC_MODE.RAM
                else:
                    self.mbc_mode = MBC_MODE.ROM

        elif key < 0xA000:
	        self._vram[key-0x8000] = val
        elif key < 0xC000:
            # TODO: Read $0x149 and determine RAM Size
	        self._eram[key-0xA000] = val
        elif key < 0xE000:
	        self._wram[key-0xC000] = val
        elif key < 0xFE00:
	        self._wram[key-0xE000] = val
        elif key < 0xFEA0:
	        self.OAM[key-0xFE00] = val
        elif key < 0xFF00:
            pass
        elif key < 0xFF80:
            if key in self._io_handlers:
                self._io_handlers[key].value = val
            if key == 0xFF00:
                self._interface.input = val
            elif key == 0xFF01:
                self.link_buffer = val
            elif key == 0xFF02:
                if val == 0x81:
                    self.serial_buff += chr(self.link_buffer)
                    if self.link_buffer == ord("\n"):
                        print(self.serial_buff, end='', file=sys.stderr)
                        if self.serial_buff == "Passed\n":
                            #sys.exit(0)
                            pass
                        elif self.serial_buff ==  "Failed\n":
                            #sys.exit(1)
                            pass
                        self.serial_buff = ""
            else:
                self.IO[key-0xFF00] = val
        elif key < 0xFFFF:
	        self._HiRAM[key-0xFF80] = val
        else:
            self.mem[65535] = val

    @property
    def IE(self):
        return self.mem[65535]

    def add_io_handler(self, val, handler):
        self._io_handlers[val] = handler

