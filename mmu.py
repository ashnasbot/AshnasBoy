from enum import Enum, auto
import random
import os
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
    ROM = 0
    RAM = 1

class MBC_TYPE(Enum):
    # need better sorting of type functionality
    NONE = 0x00
    MBC1 = 0x01
    # 00h  ROM ONLY                 19h  MBC5
    # 01h  MBC1                     1Ah  MBC5+RAM
    # 02h  MBC1+RAM                 1Bh  MBC5+RAM+BATTERY
    # 03h  MBC1+RAM+BATTERY         1Ch  MBC5+RUMBLE
    # 05h  MBC2                     1Dh  MBC5+RUMBLE+RAM
    # 06h  MBC2+BATTERY             1Eh  MBC5+RUMBLE+RAM+BATTERY
    # 08h  ROM+RAM                  20h  MBC6
    # 09h  ROM+RAM+BATTERY          22h  MBC7+SENSOR+RUMBLE+RAM+BATTERY
    # 0Bh  MMM01
    # 0Ch  MMM01+RAM
    # 0Dh  MMM01+RAM+BATTERY
    # 0Fh  MBC3+TIMER+BATTERY
    # 10h  MBC3+TIMER+RAM+BATTERY   FCh  POCKET CAMERA
    # 11h  MBC3                     FDh  BANDAI TAMA5
    # 12h  MBC3+RAM                 FEh  HuC3
    # 13h  MBC3+RAM+BATTERY         FFh  HuC1+RAM+BATTERY

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

        self.mem = bytearray(random.getrandbits(8) for _ in range(65536))  # Randomise RAM
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

        self.view = view

        self.IO[:]      = bytearray([0x00 for _ in range(0x80)])  # IO defaults to nothing
        self.mem[0xFFFF] = 0xFF  # IE

        self.link_buffer = 0

        self.serial_buff = ""
        # MBC
        self.mbc = MBC_TYPE.NONE
        self.rom_size = 0
        self.mbc_mode = MBC_MODE.ROM
        self.mbc_ram_enabled = False
        self.mbc_upper_bank = 0
        # TODO: Read $0x147 and determine MBC ($01 = MBC1)
        self._io_handlers = {}
        # Add bootrom disable handler
        self.add_io_handler(0xFF50, HandlerProxy(self.disable_bootrom))

    def load_rom(self, name, boot=False):
        self._rom = []
        path = os.path.join("roms", name)
        with open(path, "r+b") as f:
            # Read first two banks
            self.rom_name = name
            if self.rom_size == 0:
                bank = bytearray(0x4000)
                f.readinto(bank)
                self.rom_size = self.get_rom_size(bank)
                self.mbc = self.get_mbc(bank)
                self._rom.append(bank)

            while True:
                # Read remainder of ROM
                bank = bytearray(0x4000)
                if f.readinto(bank) == 0:
                    break
                self._rom.append(bank)

        path = os.path.join("roms", "boot.bin")
        if boot and os.path.isfile(path):
            with open(path, "r+b") as f:
                bank = bytearray(0x100)
                f.readinto(bank)
                self._rom[0][0:0x100] = bank[:]

        self._rom0[:] = self._rom[0]
        if len(self._rom) > 1:
            self._rom1[:] = self._rom[1]

    def disable_bootrom(self, val):
        if val == 0x01:
            self.load_rom(self.rom_name)

    def get_rom_size(self, bank):
        size = bank[0x148]
        banks = {
            0x00:  2**15,  # 32KByte (no ROM banking)
            0x01:  2**16,  # 64KByte (4 banks)
            0x02:  2**17,  # 128KByte (8 banks)
            0x03:  2**18,  # 256KByte (16 banks)
            0x04:  2**19,  # 512KByte (32 banks)
            0x05:  2**20,  # 1MByte (64 banks)  - only 63 banks used by MBC1
            0x06:  2**21,  # 2MByte (128 banks) - only 125 banks used by MBC1
            0x07:  2**22,  # 4MByte (256 banks)
            0x08:  2**23,  # 8MByte (512 banks)
            #0x52 - 1.1MByte (72 banks)
            #0x53 - 1.2MByte (80 banks)
            #0x54 - 1.5MByte (96 banks)
        }
        return banks[size]

    def get_mbc(self, bank):
        return MBC_TYPE(bank[0x148])

    def __getitem__(self, val):
        if val < 0xE000:
            return self.view[val]
        elif val < 0xFE00:
            # Echo RAM, subtract 0x2000
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
            return self.mem[0xFFFF]
        raise ValueError("Access out of bounds")

    def __setitem__(self, key, val):
        if key < 0x8000:
            # ROM Write = MBC
            if self.mbc == MBC_TYPE.NONE:
                return

            if key < 0x2000:  # RAM Gate
                self.mbc_ram_enabled = val & 0b1111 == 0b1010
            elif key < 0x4000:  # MBC1 Bank 1 0x2000 - 0x3FFF
                bank = val & 0b00011111    # Bit 7-5 ignored

                if bank == 0:
                    bank = 1
                bank += self.mbc_upper_bank
                self._rom1[:] = self._rom[bank % (self.rom_size // 16384)]
            elif key < 0x6000:  # RAM Bank Number / Upper Bits of ROM Bank no 0x4000 - 0x5FFF
                if self.mbc_mode == MBC_MODE.ROM:
                    self.mbc_upper_bank = (val & 0x03) << 5
                else:
                    pass
            else:  ## ROM/RAM Mode select 0x6000 - 0x7FFF
                mode = val & 0x01
                if mode:
                    self.mbc_mode = MBC_MODE.RAM
                    self._rom0[:] = self._rom[self.mbc_upper_bank % (self.rom_size // 16384)]
                else:
                    self.mbc_mode = MBC_MODE.ROM
                    self._rom0[:] = self._rom[0]

        elif key < 0xA000:
	        self._vram[key-0x8000] = val
        elif key < 0xC000:
            if self.mbc_ram_enabled:
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
                        # Test ROM Routines
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

    def add_io_handler(self, val, handler):
        self._io_handlers[val] = handler


class HandlerProxy:
    # Probably slow, don't use for hot path
    def __init__(self, handler):
        self._handler = handler

    @property
    def value(self):
        raise Exception("Can't read handlerproxy") 

    @value.setter    
    def value(self, val):
        return self._handler(val)