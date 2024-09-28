from interface import Interface
from typing import Any

from instruction import SimpleInstr, instrs, cbinstrs
import reg
import mmu
import ppu


class CPU():

    def __init__(self, mem: mmu.MMU, ppu: ppu.PPU, gui: Interface) -> None:
        self.reg = reg.Reg()
        self.r = self.reg
        self.mem = mem
        self.m = self.mem
        self.ppu = ppu
        self.cycles = 0
        self.IF = self.mem.mem[mmu.IF]
        self.ui = gui

        self.DIV = reg.DIV()
        self.TIMA = reg.TIMA()
        self.DIV_counter = 0
        self.TIMA_counter = 0
        self.TIMA_dividers = [1024, 16, 64, 256]
        self.TIMA_bits = [9, 3, 5, 7]
        self.remaining_cycles = 0

        mem.add_io_handler(0xFF04, self.DIV)
        mem.add_io_handler(0xFF05, self.TIMA)


    def clock(self, cycles: int) -> None:
        self.remaining_cycles -= cycles
        self.DIV._value += cycles

        #Timer
        tac = self.m[mmu.TAC]
        if tac & 0b100 != 0:  # TIMA enabled
            divider = self.TIMA_dividers[tac & 0b11]
            cur_div_bit = self.DIV._value & divider
            if self.TIMA.prev and not cur_div_bit: # Falling edge
                self.TIMA._value += 1
            
            self.TIMA.prev = cur_div_bit

            if self.TIMA._value > 0xFF:
                self.TIMA._value = self.m[0xFF06]
                if self.m[mmu.IE] & 0b00100:  # TIMER
                    self.m[mmu.IF] |= 0b00100

        # PPU
        self.ppu.clock(cycles)

        # Interrupt
        if self.r.HALT and self.m.mem[0xFF0F] & self.m.mem[0xFFFF]:
            self.r.HALT = False

        if self.r.IME:
            intr = self.m.mem[0xFF0F]
            if not intr:
                return
            enabled = self.m.mem[0xFFFF]

            if intr & 0b00001 and enabled & 0b00001:  # VBLANK
                self.r.IME = False
                self.m.mem[0xFF0F] &= 0b11110
                instrs[205].op(self, 0x40)
            elif intr & 0b00010 and enabled & 0b00010:  # STAT
                self.r.IME = False
                self.m.mem[0xFF0F] &= 0b11101
                instrs[205].op(self, 0x48)
            elif intr & 0b00100 and enabled & 0b00100:  # TIMER
                self.r.IME = False
                self.m.mem[0xFF0F] &= 0b11011
                instrs[205].op(self, 0x50)
            # TODO: Serial?
        elif self.r.ei:
            if self.r.ei == 2:
                self.r.IME = True
                self.r.ei = 0
            else:
                self.r.ei += 1

    def read_byte(self) -> int:
        self.reg.PC += 1
        return self.m[self.reg.PC-1]

    def read_word(self) -> int:
        l = self.m[self.r.PC]
        self.r.PC += 1
        h = self.m[self.r.PC]
        self.r.PC += 1
        return (h << 8) + l

    def advance_frame(self, dt: float) -> None:
        self.remaining_cycles += 70256
        self.run()
        self.ui.do_drawing(dt)

    def boot(self) -> None:
        #if not __debug__:
        self.r.PC = 0x0000
        #else:
        #    self.r.A = 0x01
        #    self.r.BC = 0x0013
        #    self.r.DE = 0x00D8
        #    self.r.DE = 0x00D8
        #    self.r.HL = 0x014D
        #    self.r.SP = 0xFFFE
        #    self.r.fZ = True
        #    self.r.fH = True
        #    self.r.fC = True
        #    self.m.IO[0x05] = 0x00   # TIMA
        #    self.m.IO[0x06] = 0x00   # TMA
        #    self.m.IO[0x07] = 0x00   # TAC
        #    self.m.IO[0x10] = 0x80   # NR10
        #    self.m.IO[0x11] = 0xBF   # NR11
        #    self.m.IO[0x12] = 0xF3   # NR12
        #    self.m.IO[0x14] = 0xBF   # NR14
        #    self.m.IO[0x16] = 0x3F   # NR21
        #    self.m.IO[0x17] = 0x00   # NR22
        #    self.m.IO[0x19] = 0xBF   # NR24
        #    self.m.IO[0x1A] = 0x7F   # NR30
        #    self.m.IO[0x1B] = 0xFF   # NR31
        #    self.m.IO[0x1C] = 0x9F   # NR32
        #    self.m.IO[0x1E] = 0xBF   # NR33
        #    self.m.IO[0x20] = 0xFF   # NR41
        #    self.m.IO[0x21] = 0x00   # NR42
        #    self.m.IO[0x22] = 0x00   # NR43
        #    self.m.IO[0x23] = 0xBF   # NR30
        #    self.m.IO[0x24] = 0x77   # NR50
        #    self.m.IO[0x25] = 0xF3   # NR51
        #    self.m.IO[0x26] = 0xF1   # NR52
        #    self.m.IO[0x40] = 0x91   # LCDC
        #    self.m.IO[0x42] = 0x00   # SCY
        #    self.m.IO[0x43] = 0x00   # SCX
        #    self.m.IO[0x45] = 0x00   # LYC
        #    self.m.IO[0x47] = 0xFC   # BGP
        #    self.m.IO[0x48] = 0xFF   # OBP0
        #    self.m.IO[0x49] = 0xFF   # OBP1
        #    self.m.IO[0x4A] = 0x00   # WY
        #    self.m.IO[0x4B] = 0x00   # WX
        #    self.r.PC = 0x0100

        # Not technically the boot rom - these should be moved elsewhere
        self.m.mem[0xFF00] = 0xFF   # Joypad

    def run(self) -> None:

        arg = 0x00
        #trace = False
        while self.remaining_cycles > 0:
            if self.reg.HALT:
                self.clock(4)
                continue

            #ipc = self.reg.PC

            i:SimpleInstr = instrs[self.mem[self.reg.PC]]
            #if trace:
            #    trc = f"{self.reg} (cy: {self.cycles}) ppu:+0 |"

            self.reg.PC += 1

            # TODO: move this into instruction somehow (without overhead)?
            if i.argbytes:
                if i.argbytes == 1:
                    arg = self.read_byte()
                    if i.value == 0xCB:
                        i = cbinstrs[arg]
                        if i.argbytes != 0:
                            arg = self.read_byte()
                    #if trace:
                    #    print(f"{trc}[00]{ipc:04X} {arg:02X} {i} ")
                else:
                    arg = self.read_word()
                #if trace:
                #    print(f"{trc}[00]{ipc:04X} {arg:04X} {i} ")
            #elif trace:
            #    arg = 0x00
            #    print(f"{trc}[00]{ipc:04X} {i}")

            # TODO: arg, reg, mem?
            i.op(self, arg)

            self.clock(i.cycles)
