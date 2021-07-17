from time import time, sleep
from datetime import datetime
from typing import Any, Union

from instruction import CB_Instruction, Instruction
import reg
import mmu
import ppu


class CPU():

    def __init__(self, mem: mmu.MMU, ppu: ppu.PPU) -> None:
        self.reg = reg.Reg()
        self.r = self.reg
        self.mem = mem
        self.m = self.mem
        self.ppu = ppu
        self.cycles = 0
        self.IF = self.mem.mem[mmu.IF]

        self.DIV = 0 # Always showing self.counter with mode 3 divider
        self.TIMA = 0 # Can be set from RAM 0xFF05
        self.DIV_counter = 0
        self.TIMA_counter = 0
        self.TIMA_dividers = [1024, 16, 64, 256]
        self.remaining_cycles = 0


    def clock(self, cycles: int) -> None:
        # DIV
        self.remaining_cycles -= cycles
        self.DIV_counter += cycles
        if self.DIV_counter >= 256:
            self.DIV += (self.DIV_counter >> 8) # Add overflown bits to DIV
            self.DIV_counter &= 0xFF # Remove the overflown bits
            self.DIV &= 0xFF
            self.m[mmu.DIV] = self.DIV

        #Timer
        self.TIMA_counter += cycles
        TAC = self.m[mmu.TAC]
        if TAC & 0b100 != 0:
            divider = self.TIMA_dividers[TAC & 0b11]

            if self.TIMA_counter >= divider:
                self.TIMA_counter -= divider # Keeps possible remainder
                TIMA = self.m[mmu.TIMA]
                TIMA += 1

                if TIMA > 0xFF:
                    TIMA = self.m[mmu.TMA]
                    TIMA &= 0xFF
                    if self.m[mmu.IE] & 0b00100:  # TIMER
                        self.m[mmu.IF] |= 0b00100
                self.m[mmu.TIMA] = TIMA

        # PPU
        self.ppu.clock(cycles)

        # Interrupt
        if self.r.HALT and self.m.mem[0xFF0F]:
            self.r.HALT = False

        if self.r.IME:
            intr = self.m.mem[0xFF0F]
            if not intr:
                return
            enabled = self.m.mem[0xFFFF]

            if intr & 0b00001 and enabled & 0b00001:  # VBLANK
                self.r.IME = False
                self.m.mem[0xFF0F] &= 0b11110
                Instruction.CALL.op(self, 0x40)
            elif intr & 0b00010 and enabled & 0b00010:  # STAT
                self.r.IME = False
                self.m.mem[0xFF0F] &= 0b11101
                Instruction.CALL.op(self, 0x48)
            elif intr & 0b00100 and enabled & 0b00100:  # TIMER
                self.r.IME = False
                self.m.mem[0xFF0F] &= 0b11011
                Instruction.CALL.op(self, 0x50)

    def read_byte(self) -> int:
        self.reg.PC += 1
        return self.m[self.reg.PC-1]

    def read_word(self) -> int:
        l = self.m[self.r.PC]
        self.r.PC += 1
        h = self.m[self.r.PC]
        self.r.PC += 1
        return (h << 8) + l

    def advance_frame(self, _: Any) -> None:
        self.remaining_cycles += 70256
        self.run()

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
        self.m.mem[0xFF04] = 0x00   # DIV

    def run(self) -> None:

        arg = None
        trace = False
        instrs = { i.value: i for i in Instruction }
        cbinstrs = { i.value: i for i in CB_Instruction }
        while self.remaining_cycles > 0:
            if self.reg.HALT:
                self.clock(4)
                continue

            ipc = self.reg.PC

            i:Union[Instruction, CB_Instruction] = instrs[self.mem[self.reg.PC]]
            if trace:
                trc = f"{self.reg} (cy: {self.cycles}) ppu:+0 |"

            self.reg.PC += 1

            # TODO: move this into instruction somehow (without overhead)?
            if i.argbytes == 1:
                arg = self.read_byte()
                if i == Instruction.CB:
                    i = cbinstrs[arg]
                    if i.argbytes == 1:
                        arg = self.read_byte()
                if trace:
                    print(f"{trc}[00]{ipc:04X} {arg:02X} {i} ")
            elif i.argbytes == 2:
                arg = self.read_word()
                if trace:
                    print(f"{trc}[00]{ipc:04X} {arg:04X} {i} ")
            elif trace:
                    print(f"{trc}[00]{ipc:04X} {i}")

            # TODO: arg, reg, mem?
            i.op(self, arg)

            #if self.cycles > 100000000:
            #    return

            self.clock(i.cycles)