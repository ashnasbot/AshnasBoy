from mbc import MBC
import random
import sys
from typing import Dict

from interface import Interface
from reg import Register, HandlerProxy

# I/O Registers
IE  = 0xFFFF
DIV = 0xFF04 
TIMA= 0xFF05
TMA = 0xFF06
TAC = 0xFF07
IF  = 0xFF0F
LY  = 0xFF44



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

    def __init__(self, interface:Interface, mbc:MBC) -> None:
        self._ui = interface

        self.mem = bytearray(random.getrandbits(8) for _ in range(65536))  # type: ignore # Randomise RAM
        view = memoryview(self.mem)
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
        self.mbc = mbc
        self.mbc.bank0 = self._rom0
        self.mbc.bank1 = self._rom1

        self.view[0xFE00:0xFFFF]      = bytearray([0x00 for _ in range(0x1FF)])  # IO, etc defaults to blank
        self.mem[0xFFFF] = 0xFF  # IE

        self.link_buffer = 0

        self.serial_buff = ""
        self._io_handlers:Dict[int, Register] = {}
        self.add_io_handler(0xFF46, HandlerProxy(self.dma))
        # Add bootrom disable handler
        self.add_io_handler(0xFF50, HandlerProxy(self.mbc.disable_bootrom))

    def dma(self, val:int) -> None:
        dest = 0xFE00
        offset = val * 0x100
        for n in range(0xA0):
            self.mem[dest + n] = self.mem[n + offset]

    def __getitem__(self, val:int) -> int:
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
                return self._ui.input
            else:
                return self.IO[val-0xFF00]
        elif val < 0xFFFF:
            return self._HiRAM[val-0xFF80]
        elif val == 0xFFFF:
            return self.mem[0xFFFF]
        raise ValueError("Access out of bounds")

    def __setitem__(self, key:int, val:int) -> None:
        if key < 0x8000:
            self.mbc[key] = val
        elif key < 0xA000:
	        self._vram[key-0x8000] = val
        elif key < 0xC000:
            if self.mbc.ram_enabled:
                # TODO: Read $0x149 and determine RAM Size
                # TODO: Pass to MBC
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
                self._ui.input = val
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

    def add_io_handler(self, val:int, handler:Register) -> None:
        self._io_handlers[val] = handler
