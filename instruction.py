from __future__ import annotations
from operator import setitem
from enum import Enum
import re
from typing import Callable, Type

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cpu import CPU
    from reg import Reg


def as_signed(n: int) -> int:
    return n - 256 if n > 127 else n

def cp (r: Reg, b: int) -> None:
    r.fZ = r.A == b
    r.fH = (r.A & 0xF) < (b & 0xF)
    r.fN = True
    r.fC = r.A < b

def addA(r: Reg, b: int) -> None:
    n = r.A + b
    r.fH = ((r.A & 0x0F) + (b & 0x0F)) & 0x10 == 0x10
    r.fC = n > 0xFF
    r.fN = False
    r.A = n & 0xFF
    r.fZ = r.A == 0

def add16(r: Reg, a:int, b:int) -> int:
    n = a + b
    r.fN = False
    r.fC = n > 0xFFFF
    r.fH = ((a & 0x0FFF) + (b & 0x0FFF)) > 0x0FFF
    return n & 0xFFFF

def subA(r: Reg, b:int) -> None:
    r.fZ = r.A == b
    r.fH = (r.A & 0xF) < (b & 0xF)
    r.fN = True
    r.fC = r.A < b
    r.A = (r.A - b) & 0xFF

def addn(r: Reg, n:str, b:int) -> None:
    val = getattr(r, n)
    r.fH = ((val & 0x0F) + (b & 0x0F)) & 0x10 == 0x10
    val += b
    r.fZ = False
    r.fN = False
    r.fC = val > 0xFF
    setattr(r,n, val & 0xFF)

def ADC(r: Reg, b: int) -> None:
    n = r.A + b
    if r.fC:
       n += 1
    r.fZ = (n & 0xFF) == 0
    r.fH = ((r.A & 0x0F) + (b & 0x0F) + r.fC) > 0x0F
    r.fC = n > 0xFF
    r.fN = False
    r.A = n & 0xFF

def SBC(r:Reg, b:int) -> None:
    c = r.fC
    f_res = r.A - b - c
    res = f_res & 0xFF

    r.fZ = res == 0
    r.fN = True
    r.fC = f_res < 0
    r.fH = ((r.A & 0x0F) - (b & 0x0F) - c) < 0

    r.A = res & 0xFF

def andA(r:Reg, b:int) -> None:
    r.A &= b
    r.fZ = r.A == 0
    r.fN = False
    r.fH = True
    r.fC = False

def xorA(r:Reg, b:int) -> None:
	r.A ^= b
	r.fZ = r.A == 0
	r.fH = False
	r.fN = False
	r.fC = False

def orA(r:Reg, b:int) -> None:
	r.A |= b
	r.fZ = r.A == 0
	r.fH = False
	r.fN = False
	r.fC = False

def nop(c:CPU, _:int) -> None:
    pass

def inc(r:Reg, b:int) -> int:
    r.fH = (b & 0xF) == 0xF
    b += 1
    b &= 0xFF
    r.fZ = b == 0
    r.fN = False
    return b

def dec(r:Reg, b:int) -> int:
    b -= 1
    b &= 0xFF
    r.fZ = b == 0
    r.fN = True
    r.fH = (b & 0xF) == 0xF
    return b

def swap(r:Reg, val:int) -> int:
    r.fZ = val == 0
    r.fN = False
    r.fH = False
    r.fC = False
    return ((val << 4) & 0xFF) | (val >> 4)

def ccf(c:CPU, _:int) -> None:
    c.r.fC = not c.r.fC
    c.r.fH = False
    c.r.fN = False

def scf(c:CPU, _:int) -> None:
    c.r.fC = True
    c.r.fH = False
    c.r.fN = False

def halt(c:CPU, _:int) -> None:
    c.r.HALT = True

def stop(c:CPU, _:int) -> None:
    c.r.STOP = True

def di(c:CPU, _:int) -> None:
    c.r.IME = False

def ei(c:CPU, _:int) -> None:
    if not c.r.IME:
        c.r.ei = 1

def rlca(c:CPU, _:int) -> None:
    r = c.r
    t = (r.A << 1) + (r.A >> 7)
    r.fC = t > 0xFF
    r.fH = False
    r.fN = False
    r.fZ = False
    r.A = t & 0xFF

def rlc(r:Reg, n:int) -> int:
    t = (n << 1) + (n >> 7)
    r.fZ = (t & 0xFF) == 0
    r.fC = t > 0xFF
    r.fH = False
    r.fN = False
    return t & 0xFF

def rrc(r:Reg, n:int) -> int:
	r.fC = (n & 0x1) == 0x1
	r.fH = False
	r.fN = False
	n >>= 1
	if r.fC:
		n |= (1 << 7)
	r.fZ = n == 0
	return n

def rl(r:Reg, n:int) -> int:
    t = (n << 1) + r.fC
    r.fH = False
    r.fN = False
    r.fZ = (t & 0xFF) == 0
    r.fC = t > 0xFF
    return t & 0xFF

def rr(r:Reg, n:int) -> int:
    oldc = r.fC
    r.fC = n & 0x1 == 0x1
    r.fH = False
    r.fN = False
    n >>= 1
    if oldc:
        n |= (1 << 7)
    r.fZ = n == 0
    return n

def osla(r:Reg, n:int) -> int:
    r.fC = (n & (1 << 7)) != 0
    n <<= 1
    n %= 0xFF
    r.fZ = n == 0
    r.fH = False
    r.fN = False
    return n

def sla(r:Reg, n:int) -> int:
    t = (n << 1)
    r.fZ = (t & 0xFF) == 0
    r.fC = t > 0xFF
    r.fH = False
    r.fN = False
    return t & 0xFF

def sra(r:Reg, n:int) -> int:
    t = ((n >> 1) | (n & 0x80)) + ((n & 1) << 8)
    r.fZ = (t & 0xFF) == 0
    r.fC = t > 0xFF
    r.fH = False
    r.fN = False
    return t & 0xFF

def srl(r:Reg, n:int) -> int:
    r.fC = (n & 0x1) != 0
    n >>= 1
    r.fZ = n == 0
    r.fH = False
    r.fN = False
    return n

def bit(r:Reg, n:int, b:int) -> int:
    t = n & (1 << b)
    r.fH = True
    r.fZ = (t & 0xFF) == 0
    r.fN = False
    return t & 0xFF

def push_word(c:CPU, n:int) -> None:
    c.r.SP -= 1
    c.m[c.r.SP] = n >> 8
    c.r.SP -= 1
    c.m[c.r.SP] = n & 0xFF

def pop_word(c:CPU) -> int:
    l = c.m[c.r.SP]
    c.r.SP += 1
    h = c.m[c.r.SP]
    c.r.SP += 1
    return (h << 8) + l

def call(c:CPU, nn:int) -> None:
    push_word(c, c.r.PC)
    c.r.PC = nn

def ret(c:CPU, _:int) -> None:
    c.r.PC = pop_word(c)

def daa(r:Reg) -> None:
    if not r.fN:
        if (r.fC or r.A > 0x99):
            r.A = (r.A  + 0x60) & 0xFF
            r.fC = True
        if r.fH or (r.A & 0x0F) > 0x09:
            r.A = (r.A + 0x6) & 0xFF
    else:  # after a subtraction, only adjust if (half-)carry occurred
        if r.fC:
            r.A = (r.A - 0x60) & 0xFF
        if r.fH:
            r.A = (r.A - 0x6) & 0xFF
    # these flags are always updated
    r.fZ = r.A == 0 # the usual z flag
    r.fH = False # h flag is always cleared

def JR_n(c:CPU, n:int) -> None:
    if n <= 127:
        c.r.PC += n
    else:
        c.r.PC += n - 256

def cpl(c:CPU, _:int) -> None:
    c.r.A = (~c.r.A) & 0xFF
    c.r.fN = True
    c.r.fH = True

def add_sp(c:CPU, n:int) -> None:
    t = c.r.SP + as_signed(n)
    c.r.fH = (((c.r.SP & 0xF) + (n & 0xF)) > 0xF)
    c.r.fC = (((c.r.SP & 0xFF) + (n & 0xFF)) > 0xFF)
    c.r.fN = False
    c.r.fZ = False
    t &= 0xFFFF
    c.r.SP = t

def ld_hl_SP_plus(c:CPU, n:int) -> None:
    c.r.fH = (((c.r.SP & 0xF) + (n & 0xF)) > 0xF)
    c.r.fC = (((c.r.SP & 0xFF) + (n & 0xFF)) > 0xFF)
    c.r.fN = False
    c.r.fZ = False
    c.r.HL = (c.r.SP + as_signed(n)) & 0xFFFF


instrs_table: dict[str, tuple[int, int, int, Callable]] = {
    "NOP        " : ( 0, 0, 4, nop                                                                             ),  # 00
    "LD_BC_nn   " : ( 1, 2, 12, lambda c, nn: setattr(c.r, 'BC', nn)                                           ),  # 01
    "LD_vBC_A   " : ( 2, 0, 8, lambda c, _: setitem(c.m, c.r.BC, c.r.A)                                        ),  # 02
    "INC_BC     " : ( 3, 0, 8, lambda c, _: setattr(c.r, 'BC', (c.r.BC+1)&0xFFFF)                              ),  # 03
    "INC_B      " : ( 4, 0, 4, lambda c, _: setattr(c.r, 'B', inc(c.r, c.r.B))                                 ),  # 04
    "DEC_B      " : ( 5, 0, 4, lambda c, _: setattr(c.r, 'B', dec(c.r, c.r.B))                                 ),  # 05
    "LD_B_n     " : ( 6, 1, 8, lambda c, n: setattr(c.r, 'B', n)                                               ),  # 06
    "RLCA       " : ( 7, 0, 4, rlca                                                                            ),  # 07
    "LD_nn_SP   " : ( 8, 2, 20, lambda c, nn: [setitem(c.m, nn, c.r.SP &0xFF), setitem(c.m, nn+1, c.r.SP >> 8)]),  # 08
    "ADD_HL_BC  " : ( 9, 0, 8, lambda c, _: setattr(c.r, "HL", add16(c.r, c.r.HL, c.r.BC))                     ),  # 09
    "LD_A_vBC   " : ( 10, 0, 8, lambda c, _: setattr(c.r, "A", c.m[c.r.BC])                                    ),  # 0A
    "DEC_BC     " : ( 11, 0, 8, lambda c, _: setattr(c.r, 'BC', (c.r.BC-1) & 0xFFFF)                           ),  # 0B
    "INC_C      " : ( 12, 0, 4, lambda c, _: setattr(c.r, 'C', inc(c.r, c.r.C))                                ),  # 0C
    "DEC_C      " : ( 13, 0, 4, lambda c, _: setattr(c.r, 'C', dec(c.r, c.r.C))                                ),  # 0D
    "LD_C_n     " : ( 14, 1, 8, lambda c, n: setattr(c.r, 'C', n)                                              ),  # 0E
    "RRCA       " : ( 15, 0, 4, lambda c, _: [setattr(c.r, 'A', rrc(c.r, c.r.A)), setattr(c.r, "fZ", False)]   ),  # type: ignore # 0F
    "STOP       " : ( 16, 1, 4, stop                                                                           ),  # 10 00
    "LD_DE_nn   " : ( 17, 2, 12, lambda c, nn: setattr(c.r, 'DE', nn)                                          ),  # 11
    "LD_vDE_A   " : ( 18, 0, 8, lambda c, _: setitem(c.m, c.r.DE, c.r.A)                                       ),  # 12
    "INC_DE     " : ( 19, 0, 8, lambda c, _: setattr(c.r, 'DE', (c.r.DE+1)&0xFFFF)                             ),  # 13
    "INC_D      " : ( 20, 0, 4, lambda c, _: setattr(c.r, 'D', inc(c.r, c.r.D))                                ),  # 14
    "DEC_D      " : ( 21, 0, 4, lambda c, _: setattr(c.r, 'D', dec(c.r, c.r.D))                                ),  # 15
    "LD_D_n     " : ( 22, 1, 8, lambda c, n: setattr(c.r, 'D', n)                                              ),  # 16
    "RLA        " : ( 23, 0, 4, lambda c, _: [setattr(c.r, 'A', rl(c.r, c.r.A)), setattr(c.r, "fZ", False)]    ),  # type: ignore # 17
    "JR_n       " : ( 24, 1, 8, JR_n                                                                           ),  # 18
    "ADD_HL_DE  " : ( 25, 0, 8, lambda c, _: setattr(c.r, "HL", add16(c.r, c.r.HL, c.r.DE))                    ),  # 19
    "LD_A_vDE   " : ( 26, 0, 8,  lambda c, _: setattr(c.r, "A", c.m[c.r.DE])                                   ),  # 1A
    "DEC_DE     " : ( 27, 0, 8, lambda c, _: setattr(c.r, 'DE', (c.r.DE-1) & 0xFFFF)                           ),  # 1B
    "INC_E      " : ( 28, 0, 4, lambda c, _: setattr(c.r, 'E', inc(c.r, c.r.E))                                ),  # 1C
    "DEC_E      " : ( 29, 0, 4, lambda c, _: setattr(c.r, 'E', dec(c.r, c.r.E))                                ),  # 1D
    "LD_E_n     " : ( 30, 1, 8, lambda c, n: setattr(c.r, 'E', n)                                              ),  # 1E
    "RRA        " : ( 31, 0, 4, lambda c, _: [setattr(c.r, 'A', rr(c.r, c.r.A)), setattr(c.r, "fZ", False)]    ),  # type: ignore # 1F
    "JR_NZ_n    " : ( 32, 1, 8,  lambda c, n: setattr(c.r, "PC", c.r.PC + as_signed(n)) if not c.r.fZ else 1   ),  # 20
    "LD_HL_nn   " : ( 33, 2, 12, lambda c, nn: setattr(c.r, 'HL', nn)                                          ),  # 21
    "LD_HLi_A   " : ( 34, 0, 8,  lambda c, _: [setitem(c.m, c.r.HL, c.r.A), setattr(c.r, "HL", c.r.HL+1)]      ),  # type: ignore # 22
    "INC_HL     " : ( 35, 0, 8, lambda c, _: setattr(c.r, 'HL', (c.r.HL+1)&0xFFFF)                             ),  # 23
    "INC_H      " : ( 36, 0, 4, lambda c, _: setattr(c.r, 'H', inc(c.r, c.r.H))                                ),  # 24
    "DEC_H      " : ( 37, 0, 4, lambda c, _: setattr(c.r, 'H', dec(c.r, c.r.H))                                ),  # 25
    "LD_H_n     " : ( 38, 1, 8, lambda c, n: setattr(c.r, 'H', n)                                              ),  # 26
    "DAA        " : ( 39, 0, 4, lambda c, _: daa(c.r)                                                          ),  # 27
    "JR_Z_n     " : ( 40, 1, 8, lambda c, n: setattr(c.r, "PC", c.r.PC + as_signed(n)) if c.r.fZ else 1        ),  # 28
    "ADD_HL_HL  " : ( 41, 0, 8, lambda c, _: setattr(c.r, "HL", add16(c.r, c.r.HL, c.r.HL))                    ),  # 29
    "LD_A_HLi   " : ( 42, 0, 8,  lambda c, _: [setattr(c.r, "A", c.m[c.r.HL]), setattr(c.r, "HL", c.r.HL+1)]   ),  # type: ignore # 2A
    "DEC_HL     " : ( 43, 0, 8, lambda c, _: setattr(c.r, 'HL', (c.r.HL-1) & 0xFFFF)                           ),  # 2B
    "INC_L      " : ( 44, 0, 4,  lambda c, _: setattr(c.r, 'L', inc(c.r, c.r.L))                               ),  # 2C
    "DEC_L      " : ( 45, 0, 4,  lambda c, _: setattr(c.r, 'L', dec(c.r, c.r.L))                               ),  # 2D
    "LD_L_n     " : ( 46, 1, 8, lambda c, n: setattr(c.r, 'L', n)                                              ),  # 2E
    "CPL        " : ( 47, 0, 4, cpl                                                                            ),  # 2F
    "JR_NC_n    " : ( 48, 1, 8, lambda c, n: setattr(c.r, "PC", c.r.PC + as_signed(n)) if not c.r.fC else 1    ),  # 30
    "LD_SP_nn   " : ( 49, 2, 12, lambda c, nn: setattr(c.r, 'SP', nn)                                          ),  # 31
    "LD_HLd_A   " : ( 50, 0, 8,  lambda c, _: [setitem(c.m, c.r.HL, c.r.A), setattr(c.r, "HL", c.r.HL-1)]      ),  # type: ignore # 32
    "INC_SP     " : ( 51, 0, 8, lambda c, _: setattr(c.r, 'SP', (c.r.SP+1)&0xFFFF)                             ),  # 33
    "INC_vHL    " : ( 52, 0, 12,  lambda c, _: setitem(c.m, c.r.HL, inc(c.r, c.m[c.r.HL]))                     ),  # 34
    "DEC_vHL    " : ( 53, 0, 12,  lambda c, _: setitem(c.m, c.r.HL, dec(c.r, c.m[c.r.HL]))                     ),  # 35
    "LD_vHL_n   " : ( 54, 1, 12,  lambda c, n: setitem(c.m, c.r.HL, n)                                         ),  # 36
    "SCF        " : ( 55, 0, 4, scf                                                                            ),  # 37
    "JR_C_n     " : ( 56, 1, 8, lambda c, n: setattr(c.r, "PC", c.r.PC + as_signed(n)) if c.r.fC else 1        ),  # 38
    "ADD_HL_SP  " : ( 57, 0, 8, lambda c, _: setattr(c.r, "HL", add16(c.r, c.r.HL, c.r.SP))                    ),  # 39
    "LD_A_HLd   " : ( 58, 0, 8,  lambda c, _: [setattr(c.r, "A", c.m[c.r.HL]), setattr(c.r, "HL", c.r.HL-1)]   ),  # type: ignore # 3A
    "DEC_SP     " : ( 59, 0, 8, lambda c, _: setattr(c.r, 'SP', (c.r.SP - 1) & 0xFFFF)                         ),  # 3B
    "INC_A      " : ( 60, 0, 4,  lambda c, _: setattr(c.r, 'A', inc(c.r, c.r.A))                               ),  # 3c
    "DEC_A      " : ( 61, 0, 4, lambda c, _: setattr(c.r, 'A', dec(c.r, c.r.A))                                ),  # 3D
    "LD_A_n     " : ( 62, 1, 8,  lambda c, n: setattr(c.r, "A", n)                                             ),  # 3E
    "CCF        " : ( 63, 0, 4, ccf                                                                            ),  # 3F
    "LD_B_B     " : ( 64, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.B)                                         ),  # 40
    "LD_B_C     " : ( 65, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.C)                                         ),  # 41
    "LD_B_D     " : ( 66, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.D)                                         ),  # 42
    "LD_B_E     " : ( 67, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.E)                                         ),  # 43
    "LD_B_H     " : ( 68, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.H)                                         ),  # 44
    "LD_B_L     " : ( 69, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.L)                                         ),  # 45
    "LD_B_vHL   " : ( 70, 0, 8,  lambda c, _: setattr(c.r, "B", c.m[c.r.HL])                                   ),  # 46
    "LD_B_A     " : ( 71, 0, 4,  lambda c, _: setattr(c.r, "B", c.r.A)                                         ),  # 47
    "LD_C_B     " : ( 72, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.B)                                         ),  # 48
    "LD_C_C     " : ( 73, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.C)                                         ),  # 49
    "LD_C_D     " : ( 74, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.D)                                         ),  # 4A
    "LD_C_E     " : ( 75, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.E)                                         ),  # 4B
    "LD_C_H     " : ( 76, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.H)                                         ),  # 4C
    "LD_C_L     " : ( 77, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.L)                                         ),  # 4D
    "LD_C_vHL   " : ( 78, 0, 8,  lambda c, _: setattr(c.r, "C", c.m[c.r.HL])                                   ),  # 4E
    "LD_C_A     " : ( 79, 0, 4,  lambda c, _: setattr(c.r, "C", c.r.A)                                         ),  # 4F
    "LD_D_B     " : ( 80, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.B)                                         ),  # 50
    "LD_D_C     " : ( 81, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.C)                                         ),  # 51
    "LD_D_D     " : ( 82, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.D)                                         ),  # 52
    "LD_D_E     " : ( 83, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.E)                                         ),  # 53
    "LD_D_H     " : ( 84, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.H)                                         ),  # 54
    "LD_D_L     " : ( 85, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.L)                                         ),  # 55
    "LD_D_vHL   " : ( 86, 0, 8,  lambda c, _: setattr(c.r, "D", c.m[c.r.HL])                                   ),  # 56
    "LD_D_A     " : ( 87, 0, 4,  lambda c, _: setattr(c.r, "D", c.r.A)                                         ),  # 57
    "LD_E_B     " : ( 88, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.B)                                         ),  # 58
    "LD_E_C     " : ( 89, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.C)                                         ),  # 59
    "LD_E_D     " : ( 90, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.D)                                         ),  # 5A
    "LD_E_E     " : ( 91, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.E)                                         ),  # 5B
    "LD_E_H     " : ( 92, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.H)                                         ),  # 5C
    "LD_E_L     " : ( 93, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.L)                                         ),  # 5D
    "LD_E_vHL   " : ( 94, 0, 8,  lambda c, _: setattr(c.r, "E", c.m[c.r.HL])                                   ),  # 5E
    "LD_E_A     " : ( 95, 0, 4,  lambda c, _: setattr(c.r, "E", c.r.A)                                         ),  # 5F
    "LD_H_B     " : ( 96, 0, 4,   lambda c, _: setattr(c.r, "H", c.r.B)                                        ),  # 60
    "LD_H_C     " : ( 97, 0, 4,   lambda c, _: setattr(c.r, "H", c.r.C)                                        ),  # 61
    "LD_H_D     " : ( 98, 0, 4,   lambda c, _: setattr(c.r, "H", c.r.D)                                        ),  # 62
    "LD_H_E     " : ( 99, 0, 4,   lambda c, _: setattr(c.r, "H", c.r.E)                                        ),  # 63
    "LD_H_H     " : ( 100, 0, 4,  lambda c, _: setattr(c.r, "H", c.r.H)                                        ),  # 64
    "LD_H_L     " : ( 101, 0, 4,  lambda c, _: setattr(c.r, "H", c.r.L)                                        ),  # 65
    "LD_H_vHL   " : ( 102, 0, 8,  lambda c, _: setattr(c.r, "H", c.m[c.r.HL])                                  ),  # 66
    "LD_H_A     " : ( 103, 0, 4,  lambda c, _: setattr(c.r, "H", c.r.A)                                        ),  # 57
    "LD_L_B     " : ( 104, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.B)                                        ),  # 68
    "LD_L_C     " : ( 105, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.C)                                        ),  # 69
    "LD_L_D     " : ( 106, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.D)                                        ),  # 6A
    "LD_L_E     " : ( 107, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.E)                                        ),  # 6B
    "LD_L_H     " : ( 108, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.H)                                        ),  # 6C
    "LD_L_L     " : ( 109, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.L)                                        ),  # 6D
    "LD_L_vHL   " : ( 110, 0, 8,  lambda c, _: setattr(c.r, "L", c.m[c.r.HL])                                  ),  # 6E
    "LD_L_A     " : ( 111, 0, 4,  lambda c, _: setattr(c.r, "L", c.r.A)                                        ),  # 6F
    "LD_vHL_B   " : ( 112, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.B)                                     ),  # 70
    "LD_vHL_C   " : ( 113, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.C)                                     ),  # 71
    "LD_vHL_D   " : ( 114, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.D)                                     ),  # 72
    "LD_vHL_E   " : ( 115, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.E)                                     ),  # 73
    "LD_vHL_H   " : ( 116, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.H)                                     ),  # 74
    "LD_vHL_L   " : ( 117, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.L)                                     ),  # 75
    "HALT       " : ( 118, 0, 4,  halt                                                                         ),  # 76
    "LD_vHL_A   " : ( 119, 0, 8,  lambda c, _: setitem(c.m, c.r.HL, c.r.A)                                     ),  # 77
    "LD_A_B     " : ( 120, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.B)                                        ),  # 78
    "LD_A_C     " : ( 121, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.C)                                        ),  # 79
    "LD_A_D     " : ( 122, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.D)                                        ),  # 7A
    "LD_A_E     " : ( 123, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.E)                                        ),  # 7B
    "LD_A_H     " : ( 124, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.H)                                        ),  # 7C
    "LD_A_L     " : ( 125, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.L)                                        ),  # 7D
    "LD_A_vHL   " : ( 126, 0, 8,  lambda c, _: setattr(c.r, "A", c.m[c.r.HL])                                  ),  # 7E
    "LD_A_A     " : ( 127, 0, 4,  lambda c, _: setattr(c.r, "A", c.r.A)                                        ),  # 7F
    "ADD_A_B    " : ( 128, 0, 4,  lambda c, _: addA(c.r, c.r.B)                                                ),  # 80
    "ADD_A_C    " : ( 129, 0, 4,  lambda c, _: addA(c.r, c.r.C)                                                ),  # 81
    "ADD_A_D    " : ( 130, 0, 4,  lambda c, _: addA(c.r, c.r.D)                                                ),  # 82
    "ADD_A_E    " : ( 131, 0, 4,  lambda c, _: addA(c.r, c.r.E)                                                ),  # 82
    "ADD_A_H    " : ( 132, 0, 4,  lambda c, _: addA(c.r, c.r.H)                                                ),  # 84
    "ADD_A_L    " : ( 133, 0, 4,  lambda c, _: addA(c.r, c.r.L)                                                ),  # 85
    "ADD_A_vHL  " : ( 134, 0, 8,  lambda c, _: addA(c.r, c.m[c.r.HL])                                          ),  # 86
    "ADD_A_A    " : ( 135, 0, 4,  lambda c, _: addA(c.r, c.r.A)                                                ),  # 87
    "ADC_A_B    " : ( 136, 0, 4,  lambda c, _: ADC(c.r, c.r.B)                                                 ),  # 88
    "ADC_A_C    " : ( 137, 0, 4,  lambda c, _: ADC(c.r, c.r.C)                                                 ),  # 89
    "ADC_A_D    " : ( 138, 0, 4,  lambda c, _: ADC(c.r, c.r.D)                                                 ),  # 8A
    "ADC_A_E    " : ( 139, 0, 4,  lambda c, _: ADC(c.r, c.r.E)                                                 ),  # 8B
    "ADC_A_H    " : ( 140, 0, 4,  lambda c, _: ADC(c.r, c.r.H)                                                 ),  # 8C
    "ADC_A_L    " : ( 141, 0, 4,  lambda c, _: ADC(c.r, c.r.L)                                                 ),  # 8D
    "ADC_A_vHL  " : ( 142, 0, 8,  lambda c, _: ADC(c.r, c.m[c.r.HL])                                           ),  # 8E
    "ADC_A_A    " : ( 143, 0, 4,  lambda c, _: ADC(c.r, c.r.A)                                                 ),  # 8F
    "SUB_A_B    " : ( 144, 0, 4,  lambda c, _: subA(c.r, c.r.B)                                                ),  # 90
    "SUB_A_C    " : ( 145, 0, 4,  lambda c, _: subA(c.r, c.r.C)                                                ),  # 91
    "SUB_A_D    " : ( 146, 0, 4,  lambda c, _: subA(c.r, c.r.D)                                                ),  # 92
    "SUB_A_E    " : ( 147, 0, 4,  lambda c, _: subA(c.r, c.r.E)                                                ),  # 93
    "SUB_A_H    " : ( 148, 0, 4,  lambda c, _: subA(c.r, c.r.H)                                                ),  # 94
    "SUB_A_L    " : ( 149, 0, 4,  lambda c, _: subA(c.r, c.r.L)                                                ),  # 95
    "SUB_A_vHL  " : ( 150, 0, 8,  lambda c, _: subA(c.r, c.m[c.r.HL])                                          ),  # 96
    "SUB_A_A    " : ( 151, 0, 4,  lambda c, _: subA(c.r, c.r.A)                                                ),  # 97
    "SBC_A_B    " : ( 152, 0, 4,  lambda c, _: SBC(c.r, c.r.B)                                                 ),  # 98
    "SBC_A_C    " : ( 153, 0, 4,  lambda c, _: SBC(c.r, c.r.C)                                                 ),  # 99
    "SBC_A_D    " : ( 154, 0, 4,  lambda c, _: SBC(c.r, c.r.D)                                                 ),  # 9A
    "SBC_A_E    " : ( 155, 0, 4,  lambda c, _: SBC(c.r, c.r.E)                                                 ),  # 9B
    "SBC_A_H    " : ( 156, 0, 4,  lambda c, _: SBC(c.r, c.r.H)                                                 ),  # 9C
    "SBC_A_L    " : ( 157, 0, 4,  lambda c, _: SBC(c.r, c.r.L)                                                 ),  # 9D
    "SBC_A_vHL  " : ( 158, 0, 8,  lambda c, _: SBC(c.r, c.m[c.r.HL])                                           ),  # 9E
    "SBC_A_A    " : ( 159, 0, 8,  lambda c, _: SBC(c.r, c.r.A)                                                 ),  # 9F
    "AND_B      " : ( 160, 0, 4,  lambda c, _: andA(c.r, c.r.B)                                                ),  # A0
    "AND_C      " : ( 161, 0, 4,  lambda c, _: andA(c.r, c.r.C)                                                ),  # A1
    "AND_D      " : ( 162, 0, 4,  lambda c, _: andA(c.r, c.r.D)                                                ),  # A2
    "AND_E      " : ( 163, 0, 4,  lambda c, _: andA(c.r, c.r.E)                                                ),  # A3
    "AND_H      " : ( 164, 0, 4,  lambda c, _: andA(c.r, c.r.H)                                                ),  # A4
    "AND_L      " : ( 165, 0, 4,  lambda c, _: andA(c.r, c.r.L)                                                ),  # A5
    "AND_vHL    " : ( 166, 0, 8,  lambda c, _: andA(c.r, c.m[c.r.HL])                                          ),  # A6
    "AND_A      " : ( 167, 0, 4,  lambda c, _: andA(c.r, c.r.A)                                                ),  # A7
    "XOR_B      " : ( 168, 0, 4,  lambda c, _: xorA(c.r, c.r.B)                                                ),  # A8
    "XOR_C      " : ( 169, 0, 4,  lambda c, _: xorA(c.r, c.r.C)                                                ),  # A9
    "XOR_D      " : ( 170, 0, 4,  lambda c, _: xorA(c.r, c.r.D)                                                ),  # AA
    "XOR_E      " : ( 171, 0, 4,  lambda c, _: xorA(c.r, c.r.E)                                                ),  # AB
    "XOR_H      " : ( 172, 0, 4,  lambda c, _: xorA(c.r, c.r.H)                                                ),  # AC
    "XOR_L      " : ( 173, 0, 4,  lambda c, _: xorA(c.r, c.r.L)                                                ),  # AD
    "XOR_vHL    " : ( 174, 0, 8,  lambda c, _: xorA(c.r, c.m[c.r.HL])                                          ),  # AE
    "XOR_A      " : ( 175, 0, 4,  lambda c, _: xorA(c.r, c.r.A)                                                ),  # AF
    "OR_B       " : (176, 0, 4,  lambda c, _: orA(c.r, c.r.B)                                                  ),  # B0
    "OR_C       " : (177, 0, 4,  lambda c, _: orA(c.r, c.r.C)                                                  ),  # B1
    "OR_D       " : (178, 0, 4,  lambda c, _: orA(c.r, c.r.D)                                                  ),  # B2
    "OR_E       " : (179, 0, 4,  lambda c, _: orA(c.r, c.r.E)                                                  ),  # B3
    "OR_H       " : (180, 0, 4,  lambda c, _: orA(c.r, c.r.H)                                                  ),  # B4
    "OR_L       " : (181, 0, 4,  lambda c, _: orA(c.r, c.r.L)                                                  ),  # B5
    "OR_vHL     " : (182, 0, 8,  lambda c, _: orA(c.r, c.m[c.r.HL])                                            ),  # B6
    "OR_A       " : (183, 0, 4,  lambda c, _: orA(c.r, c.r.A)                                                  ),  # B7
    "CP_B       " : (184, 0, 4,  lambda c, _: cp(c.r, c.r.B)                                                   ),  # B8
    "CP_C       " : (185, 0, 4,  lambda c, _: cp(c.r, c.r.C)                                                   ),  # B9
    "CP_D       " : (186, 0, 4,  lambda c, _: cp(c.r, c.r.D)                                                   ),  # BA
    "CP_E       " : (187, 0, 4,  lambda c, _: cp(c.r, c.r.E)                                                   ),  # BB
    "CP_H       " : (188, 0, 4,  lambda c, _: cp(c.r, c.r.H)                                                   ),  # BC
    "CP_L       " : (189, 0, 4,  lambda c, _: cp(c.r, c.r.L)                                                   ),  # BD
    "CP_vHL     " : (190, 0, 8,  lambda c, _: cp(c.r, c.m[c.r.HL])                                             ),  # BE
    "CP_A       " : (191, 0, 4,  lambda c, _: cp(c.r, c.r.A)                                                   ),  # BF
    "RET_NZ     " : ( 192, 0, 8, lambda c, _: ret(c, _) if not c.r.fZ else 1                                   ),  # C0
    "POP_BC     " : ( 193, 0, 12,  lambda c, _: setattr(c.r, "BC", pop_word(c))                                ),  # C1
    "JP_NZ_nn   " : ( 194, 2, 12,  lambda c, nn: setattr(c.r, "PC", nn) if not c.r.fZ else 1                   ),  # C2
    "JP         " : ( 195, 2, 12,  lambda c, nn: setattr(c.r, "PC", nn)                                        ),  # C3
    "CALL_NZ    " : ( 196, 2, 12, lambda c, nn: call(c, nn) if not c.r.fZ else 1                               ),  # C4
    "PUSH_BC    " : ( 197, 0, 16, lambda c, _: push_word(c, c.r.BC)                                            ),  # C5
    "ADD_A_n    " : ( 198, 1, 4,  lambda c, n: addA(c.r, n)                                                    ),  # C6
    "RST_00H    " : ( 199, 0, 16, lambda c, _: call(c, 0)                                                      ),  # C7
    "RET_Z      " : ( 200, 0, 8, lambda c, _: ret(c, _) if c.r.fZ else 1                                       ),  # C8
    "RET        " : ( 201, 0, 8, ret                                                                           ),  # C9
    "JP_Z_nn    " : ( 202, 2, 12,  lambda c, nn: setattr(c.r, "PC", nn) if c.r.fZ else 1                       ),  # CA
    "CB         " : ( 203, 1, 0, lambda c, n: 1/0                                                              ),  # cb
    "CALL_Z     " : ( 204, 2, 12, lambda c, nn: call(c, nn) if c.r.fZ else 1                                   ),  # CC
    "CALL       " : ( 205, 2, 12, call                                                                         ),  # CD
    "ADC_A_n    " : ( 206, 1, 8,  lambda c, n: ADC(c.r, n)                                                     ),  # CE
    "RST_08H    " : ( 207, 0, 16, lambda c, _: call(c, 0x08)                                                   ),  # CF
    "RET_NC     " : ( 208, 0, 8, lambda c, _: ret(c, _) if not c.r.fC else 1                                   ),  # D0
    "POP_DE     " : ( 209, 0, 12,  lambda c, _: setattr(c.r, "DE", pop_word(c))                                ),  # D1
    "JP_NC_nn   " : ( 210, 2, 12,  lambda c, nn: setattr(c.r, "PC", nn) if not c.r.fC else 1                   ),  # D2
    "CALL_NC    " : ( 212, 2, 12, lambda c, nn: call(c, nn) if not c.r.fC else 1                               ),  # D4
    "PUSH_DE    " : ( 213, 0, 16, lambda c, _: push_word(c, c.r.DE)                                            ),  # D5
    "SUB_A_n    " : ( 214, 1, 8,  lambda c, n: subA(c.r, n)                                                    ),  # D6
    "RST_10H    " : ( 215, 0, 16, lambda c, _: call(c, 0x10)                                                   ),  # D7
    "RET_C      " : ( 216, 0, 8, lambda c, _: ret(c, _) if c.r.fC else 1                                       ),  # D8
    "RETI       " : ( 217, 0, 8, lambda c, _: [ret(c, _), ei(c, _)]                                            ),  # type: ignore # D9
    "JP_C_nn    " : ( 218, 2, 12,  lambda c, nn: setattr(c.r, "PC", nn) if c.r.fC else 1                       ),  # DA
    "CALL_C     " : ( 220, 2, 12, lambda c, nn: call(c, nn) if c.r.fC else 1                                   ),  # DC
    "SBC_n      " : ( 222, 1, 8, lambda c, n: SBC(c.r, n)                                                      ),  # DE
    "RST_18H    " : ( 223, 0, 16, lambda c, _: call(c, 0x18)                                                   ),  # DF
    "LD_vffn_A  " : ( 224, 1, 12,  lambda c, n: setitem(c.m, 0xFF00 + n, c.r.A)                                ),  # E0
    "POP_HL     " : ( 225, 0, 12,  lambda c, _: setattr(c.r, "HL", pop_word(c))                                ),  # E1
    "LD_vffC_A  " : ( 226, 0, 8,  lambda c, _: setitem(c.m, 0xFF00 + c.r.C, c.r.A)                             ),  # E2
    "PUSH_HL    " : ( 229, 0, 16, lambda c, _: push_word(c, c.r.HL)                                            ),  # E5
    "AND_n      " : ( 230, 1, 8,  lambda c, n: andA(c.r, n)                                                    ),  # E6
    "RST_20H    " : ( 231, 0, 16, lambda c, _: call(c, 0x20)                                                   ),  # E7
    "ADD_SP_n   " : ( 232, 1, 16, add_sp                                                                       ),  # E8
    "JP_vHL     " : ( 233, 0, 4,  lambda c, _: setattr(c.r, "PC", c.r.HL)                                      ),  # E9
    "LD_nn_A    " : ( 234, 2, 16, lambda c, nn: setitem(c.m, nn, c.r.A)                                        ),  # EA
    "XOR_A_n    " : ( 238, 1, 8,  lambda c, n: xorA(c.r, n)                                                    ),  # EE
    "RST_28H    " : ( 239, 0, 16, lambda c, _: call(c, 0x28)                                                   ),  # EF
    "LD_A_vffn  " : ( 240, 1, 12,  lambda c, n: setattr(c.r, "A", c.m[(0xFF00 + n) & 0xFFFF])                  ),  # F0
    "POP_AF     " : ( 241, 0, 12,  lambda c, _: setattr(c.r, "AF", pop_word(c))                                ),  # F1
    "LD_A_vffC  " : ( 242, 0, 8,  lambda c, _: setattr(c.r, "A", c.m[0xFF00 + c.r.C])                          ),  # F2
    "DI         " : ( 243, 0, 4,  di                                                                           ),  # F3
    "PUSH_AF    " : ( 245, 0, 16, lambda c, _: push_word(c, c.r.AF)                                            ),  # F5
    "OR_n       " : ( 246, 1, 8,  lambda c, n: orA(c.r, n)                                                     ),  # F6
    "RST_30H    " : ( 247, 0, 16, lambda c, _: call(c, 0x30)                                                   ),  # F7
    "LDHL_SP_n  " : ( 248, 1, 12, ld_hl_SP_plus                                                                ),  # F8
    "LD_SP_HL   " : ( 249, 0, 8, lambda c, _: setattr(c.r, 'SP', c.r.HL)                                       ),  # F9
    "LD_A_vnn   " : ( 250, 2, 16,  lambda c, nn: setattr(c.r, "A", c.m[nn])                                    ),  # FA
    "EI         " : ( 251, 0, 4,  ei                                                                           ),  # FB
    "CP_n       " : ( 254, 1, 8,  lambda c, n: cp(c.r, n)                                                      ),  # FE
    "RST_38H    " : ( 255, 0, 16, lambda c, _: call(c, 0x38)                                                   )   # FF
}


cbinstrs_table: dict[str, tuple[int, int, int, Callable]] = {
    "RLC_B      " : ( 0, 0, 8,  lambda c, _: setattr(c.r, "B", rlc(c.r, c.r.B))                 ), # 00
    "RLC_C      " : ( 1, 0, 8,  lambda c, _: setattr(c.r, "C", rlc(c.r, c.r.C))                 ), # 01
    "RLC_D      " : ( 2, 0, 8,  lambda c, _: setattr(c.r, "D", rlc(c.r, c.r.D))                 ), # 02
    "RLC_E      " : ( 3, 0, 8,  lambda c, _: setattr(c.r, "E", rlc(c.r, c.r.E))                 ), # 03
    "RLC_H      " : ( 4, 0, 8,  lambda c, _: setattr(c.r, "H", rlc(c.r, c.r.H))                 ), # 04
    "RLC_L      " : ( 5, 0, 8,  lambda c, _: setattr(c.r, "L", rlc(c.r, c.r.L))                 ), # 05
    "RLC_vHL    " : ( 6, 0, 16,  lambda c, _: setitem(c.m, c.r.HL, rlc(c.r, c.m[c.r.HL]))       ), # 06
    "RLC_A      " : ( 7, 0, 8,  lambda c, _: setattr(c.r, "A", rlc(c.r, c.r.A))                 ), # 07
    "RRC_B      " : ( 8, 0, 8,  lambda c, _: setattr(c.r, "B", rrc(c.r, c.r.B))                 ), # 08
    "RRC_C      " : ( 9, 0, 8,  lambda c, _: setattr(c.r, "C", rrc(c.r, c.r.C))                 ), # 09
    "RRC_D      " : ( 10, 0, 8,  lambda c, _: setattr(c.r, "D", rrc(c.r, c.r.D))                ), # 0A
    "RRC_E      " : ( 11, 0, 8,  lambda c, _: setattr(c.r, "E", rrc(c.r, c.r.E))                ), # 0B
    "RRC_H      " : ( 12, 0, 8,  lambda c, _: setattr(c.r, "H", rrc(c.r, c.r.H))                ), # 0C
    "RRC_L      " : ( 13, 0, 8,  lambda c, _: setattr(c.r, "L", rrc(c.r, c.r.L))                ), # 0D
    "RRC_vHL    " : ( 14, 0, 16, lambda c, _: setitem(c.m, c.r.HL, rrc(c.r, c.m[c.r.HL]))       ), # 0E
    "RRC_A      " : ( 15, 0, 8,  lambda c, _: setattr(c.r, "A", rrc(c.r, c.r.A))                ), # 0F
    "RL_B       " : ( 16, 0, 8,  lambda c, _: setattr(c.r, "B", rl(c.r, c.r.B))                 ), # 10
    "RL_C       " : ( 17, 0, 8,  lambda c, _: setattr(c.r, "C", rl(c.r, c.r.C))                 ), # 11
    "RL_D       " : ( 18, 0, 8,  lambda c, _: setattr(c.r, "D", rl(c.r, c.r.D))                 ), # 12
    "RL_E       " : ( 19, 0, 8,  lambda c, _: setattr(c.r, "E", rl(c.r, c.r.E))                 ), # 13
    "RL_H       " : ( 20, 0, 8,  lambda c, _: setattr(c.r, "H", rl(c.r, c.r.H))                 ), # 14
    "RL_L       " : ( 21, 0, 8,  lambda c, _: setattr(c.r, "L", rl(c.r, c.r.L))                 ), # 15
    "RL_vHL     " : ( 22, 0, 16, lambda c, _: setitem(c.m, c.r.HL, rl(c.r, c.m[c.r.HL]))        ), # 16
    "RL_A       " : ( 23, 0, 8,  lambda c, _: setattr(c.r, "A", rl(c.r, c.r.A))                 ), # 17
    "RR_B       " : ( 24, 0, 8,  lambda c, _: setattr(c.r, "B", rr(c.r, c.r.B))                 ), # 18
    "RR_C       " : ( 25, 0, 8,  lambda c, _: setattr(c.r, "C", rr(c.r, c.r.C))                 ), # 19
    "RR_D       " : ( 26, 0, 8,  lambda c, _: setattr(c.r, "D", rr(c.r, c.r.D))                 ), # 1A
    "RR_E       " : ( 27, 0, 8,  lambda c, _: setattr(c.r, "E", rr(c.r, c.r.E))                 ), # 1B
    "RR_H       " : ( 28, 0, 8,  lambda c, _: setattr(c.r, "H", rr(c.r, c.r.H))                 ), # 1C
    "RR_L       " : ( 29, 0, 8,  lambda c, _: setattr(c.r, "L", rr(c.r, c.r.L))                 ), # 1D
    "RR_vHL     " : ( 30, 0, 16, lambda c, _: setitem(c.m, c.r.HL, rr(c.r, c.m[c.r.HL]))        ), # 1E
    "RR_A       " : ( 31, 0, 8,  lambda c, _: setattr(c.r, "A", rr(c.r, c.r.A))                 ), # 1F
    "SLA_B      " : ( 32, 0, 8,  lambda c, _: setattr(c.r, "B", sla(c.r, c.r.B))                ), # 20
    "SLA_C      " : ( 33, 0, 8,  lambda c, _: setattr(c.r, "C", sla(c.r, c.r.C))                ), # 21
    "SLA_D      " : ( 34, 0, 8,  lambda c, _: setattr(c.r, "D", sla(c.r, c.r.D))                ), # 22
    "SLA_E      " : ( 35, 0, 8,  lambda c, _: setattr(c.r, "E", sla(c.r, c.r.E))                ), # 23
    "SLA_H      " : ( 36, 0, 8,  lambda c, _: setattr(c.r, "H", sla(c.r, c.r.H))                ), # 24
    "SLA_L      " : ( 37, 0, 8,  lambda c, _: setattr(c.r, "L", sla(c.r, c.r.L))                ), # 25
    "SLA_vHL    " : ( 38, 0, 16, lambda c, _: setitem(c.m, c.r.HL, sla(c.r, c.m[c.r.HL]))       ), # 26
    "SLA_A      " : ( 39, 0, 8,  lambda c, _: setattr(c.r, "A", sla(c.r, c.r.A))                ), # 27
    "SRA_B      " : ( 40, 0, 8,  lambda c, _: setattr(c.r, "B", sra(c.r, c.r.B))                ), # 28
    "SRA_C      " : ( 41, 0, 8,  lambda c, _: setattr(c.r, "C", sra(c.r, c.r.C))                ), # 29
    "SRA_D      " : ( 42, 0, 8,  lambda c, _: setattr(c.r, "D", sra(c.r, c.r.D))                ), # 2A
    "SRA_E      " : ( 43, 0, 8,  lambda c, _: setattr(c.r, "E", sra(c.r, c.r.E))                ), # 2B
    "SRA_H      " : ( 44, 0, 8,  lambda c, _: setattr(c.r, "H", sra(c.r, c.r.H))                ), # 2C
    "SRA_L      " : ( 45, 0, 8,  lambda c, _: setattr(c.r, "L", sra(c.r, c.r.L))                ), # 2D
    "SRA_vHL    " : ( 46, 0, 16, lambda c, _: setitem(c.m, c.r.HL, sra(c.r, c.m[c.r.HL]))       ), # 2E
    "SRA_A      " : ( 47, 0, 8,  lambda c, _: setattr(c.r, "A", sra(c.r, c.r.A))                ), # 2F
    "SWAP_B     " : ( 48, 0, 8,  lambda c, _: setattr(c.r, "B", swap(c.r, c.r.B))               ), # 30
    "SWAP_C     " : ( 49, 0, 8,  lambda c, _: setattr(c.r, "C", swap(c.r, c.r.C))               ), # 31
    "SWAP_D     " : ( 50, 0, 8,  lambda c, _: setattr(c.r, "D", swap(c.r, c.r.D))               ), # 32
    "SWAP_E     " : ( 51, 0, 8,  lambda c, _: setattr(c.r, "E", swap(c.r, c.r.E))               ), # 33
    "SWAP_H     " : ( 52, 0, 8,  lambda c, _: setattr(c.r, "H", swap(c.r, c.r.H))               ), # 34
    "SWAP_L     " : ( 53, 0, 8,  lambda c, _: setattr(c.r, "L", swap(c.r, c.r.L))               ), # 35
    "SWAP_vHL   " : ( 54, 0, 16, lambda c, _: setitem(c.m, c.r.HL, swap(c.r, c.m[c.r.HL]))      ), # 36
    "SWAP_A     " : ( 55, 0, 8,  lambda c, _: setattr(c.r, "A", swap(c.r, c.r.A))               ), # 37
    "SRL_B      " : ( 56, 0, 8,  lambda c, _: setattr(c.r, "B", srl(c.r, c.r.B))                ), # 38
    "SRL_C      " : ( 57, 0, 8,  lambda c, _: setattr(c.r, "C", srl(c.r, c.r.C))                ), # 39
    "SRL_D      " : ( 58, 0, 8,  lambda c, _: setattr(c.r, "D", srl(c.r, c.r.D))                ), # 3A
    "SRL_E      " : ( 59, 0, 8,  lambda c, _: setattr(c.r, "E", srl(c.r, c.r.E))                ), # 3B
    "SRL_H      " : ( 60, 0, 8,  lambda c, _: setattr(c.r, "H", srl(c.r, c.r.H))                ), # 3C
    "SRL_L      " : ( 61, 0, 8,  lambda c, _: setattr(c.r, "L", srl(c.r, c.r.L))                ), # 3D
    "SRL_vHL    " : ( 62, 0, 16, lambda c, _: setitem(c.m, c.r.HL, srl(c.r, c.m[c.r.HL]))       ), # 3E
    "SRL_A      " : ( 63, 0, 8,  lambda c, _: setattr(c.r, "A", srl(c.r, c.r.A))                ), # 3F
    "BIT_0_B    " : ( 64, 0, 8,  lambda c, _:  bit(c.r, c.r.B, 0)                               ), # 40
    "BIT_0_C    " : ( 65, 0, 8,  lambda c, _:  bit(c.r, c.r.C, 0)                               ), # 41
    "BIT_0_D    " : ( 66, 0, 8,  lambda c, _:  bit(c.r, c.r.D, 0)                               ), # 42
    "BIT_0_E    " : ( 67, 0, 8,  lambda c, _:  bit(c.r, c.r.E, 0)                               ), # 43
    "BIT_0_H    " : ( 68, 0, 8,  lambda c, _:  bit(c.r, c.r.H, 0)                               ), # 44
    "BIT_0_L    " : ( 69, 0, 8,  lambda c, _:  bit(c.r, c.r.L, 0)                               ), # 45
    "BIT_0_vHL  " : ( 70, 0, 16, lambda c, _:  bit(c.r, c.m[c.r.HL], 0)                         ), # 46
    "BIT_0_A    " : ( 71, 0, 8,  lambda c, _:  bit(c.r, c.r.A, 0)                               ), # 47
    "BIT_1_B    " : ( 72, 0, 8,  lambda c, _:  bit(c.r, c.r.B, 1)                               ), # 48
    "BIT_1_C    " : ( 73, 0, 8,  lambda c, _:  bit(c.r, c.r.C, 1)                               ), # 49
    "BIT_1_D    " : ( 74, 0, 8,  lambda c, _:  bit(c.r, c.r.D, 1)                               ), # 4A
    "BIT_1_E    " : ( 75, 0, 8,  lambda c, _:  bit(c.r, c.r.E, 1)                               ), # 4B
    "BIT_1_H    " : ( 76, 0, 8,  lambda c, _:  bit(c.r, c.r.H, 1)                               ), # 4C
    "BIT_1_L    " : ( 77, 0, 8,  lambda c, _:  bit(c.r, c.r.L, 1)                               ), # 4D
    "BIT_1_vHL  " : ( 78, 0, 16, lambda c, _:  bit(c.r, c.m[c.r.HL], 1)                         ), # 4E
    "BIT_1_A    " : ( 79, 0, 8,  lambda c, _:  bit(c.r, c.r.A, 1)                               ), # 4F
    "BIT_2_B    " : ( 80, 0, 8,  lambda c, _:  bit(c.r, c.r.B, 2)                               ), # 50
    "BIT_2_C    " : ( 81, 0, 8,  lambda c, _:  bit(c.r, c.r.C, 2)                               ), # 51
    "BIT_2_D    " : ( 82, 0, 8,  lambda c, _:  bit(c.r, c.r.D, 2)                               ), # 52
    "BIT_2_E    " : ( 83, 0, 8,  lambda c, _:  bit(c.r, c.r.E, 2)                               ), # 53
    "BIT_2_H    " : ( 84, 0, 8,  lambda c, _:  bit(c.r, c.r.H, 2)                               ), # 54
    "BIT_2_L    " : ( 85, 0, 8,  lambda c, _:  bit(c.r, c.r.L, 2)                               ), # 55
    "BIT_2_vHL  " : ( 86, 0, 16, lambda c, _:  bit(c.r, c.m[c.r.HL], 2)                         ), # 56
    "BIT_2_A    " : ( 87, 0, 8,  lambda c, _:  bit(c.r, c.r.A, 2)                               ), # 57
    "BIT_3_B    " : ( 88, 0, 8,  lambda c, _:  bit(c.r, c.r.B, 3)                               ), # 58
    "BIT_3_C    " : ( 89, 0, 8,  lambda c, _:  bit(c.r, c.r.C, 3)                               ), # 59
    "BIT_3_D    " : ( 90, 0, 8,  lambda c, _:  bit(c.r, c.r.D, 3)                               ), # 5A
    "BIT_3_E    " : ( 91, 0, 8,  lambda c, _:  bit(c.r, c.r.E, 3)                               ), # 5B
    "BIT_3_H    " : ( 92, 0, 8,  lambda c, _:  bit(c.r, c.r.H, 3)                               ), # 5C
    "BIT_3_L    " : ( 93, 0, 8,  lambda c, _:  bit(c.r, c.r.L, 3)                               ), # 5D
    "BIT_3_vHL  " : ( 94, 0, 16, lambda c, _:  bit(c.r, c.m[c.r.HL], 3)                         ), # 5E
    "BIT_3_A    " : ( 95, 0, 8,  lambda c, _:  bit(c.r, c.r.A, 3)                               ), # 5F
    "BIT_4_B    " : ( 96, 0, 8,  lambda c, _:  bit(c.r, c.r.B, 4)                               ), # 60
    "BIT_4_C    " : ( 97, 0, 8,  lambda c, _:  bit(c.r, c.r.C, 4)                               ), # 61
    "BIT_4_D    " : ( 98, 0, 8,  lambda c, _:  bit(c.r, c.r.D, 4)                               ), # 62
    "BIT_4_E    " : ( 99, 0, 8,  lambda c, _:  bit(c.r, c.r.E, 4)                               ), # 63
    "BIT_4_H    " : ( 100, 0, 8,  lambda c, _: bit(c.r, c.r.H, 4)                               ), # 64
    "BIT_4_L    " : ( 101, 0, 8,  lambda c, _: bit(c.r, c.r.L, 4)                               ), # 65
    "BIT_4_vHL  " : ( 102, 0, 16, lambda c, _: bit(c.r, c.m[c.r.HL], 4)                         ), # 66
    "BIT_4_A    " : ( 103, 0, 8,  lambda c, _: bit(c.r, c.r.A, 4)                               ), # 67
    "BIT_5_B    " : ( 104, 0, 8,  lambda c, _: bit(c.r, c.r.B, 5)                               ), # 68
    "BIT_5_C    " : ( 105, 0, 8,  lambda c, _: bit(c.r, c.r.C, 5)                               ), # 69
    "BIT_5_D    " : ( 106, 0, 8,  lambda c, _: bit(c.r, c.r.D, 5)                               ), # 6A
    "BIT_5_E    " : ( 107, 0, 8,  lambda c, _: bit(c.r, c.r.E, 5)                               ), # 6B
    "BIT_5_H    " : ( 108, 0, 8,  lambda c, _: bit(c.r, c.r.H, 5)                               ), # 6C
    "BIT_5_L    " : ( 109, 0, 8,  lambda c, _: bit(c.r, c.r.L, 5)                               ), # 6D
    "BIT_5_vHL  " : ( 110, 0, 16, lambda c, _: bit(c.r, c.m[c.r.HL], 5)                         ), # 6E
    "BIT_5_A    " : ( 111, 0, 8,  lambda c, _: bit(c.r, c.r.A, 5)                               ), # 6F
    "BIT_6_B    " : ( 112, 0, 8,  lambda c, _: bit(c.r, c.r.B, 6)                               ), # 70
    "BIT_6_C    " : ( 113, 0, 8,  lambda c, _: bit(c.r, c.r.C, 6)                               ), # 71
    "BIT_6_D    " : ( 114, 0, 8,  lambda c, _: bit(c.r, c.r.D, 6)                               ), # 72
    "BIT_6_E    " : ( 115, 0, 8,  lambda c, _: bit(c.r, c.r.E, 6)                               ), # 73
    "BIT_6_H    " : ( 116, 0, 8,  lambda c, _: bit(c.r, c.r.H, 6)                               ), # 74
    "BIT_6_L    " : ( 117, 0, 8,  lambda c, _: bit(c.r, c.r.L, 6)                               ), # 75
    "BIT_6_vHL  " : ( 118, 0, 16, lambda c, _: bit(c.r, c.m[c.r.HL], 6)                         ), # 76
    "BIT_6_A    " : ( 119, 0, 8,  lambda c, _: bit(c.r, c.r.A, 6)                               ), # 77
    "BIT_7_B    " : ( 120, 0, 8,  lambda c, _: bit(c.r, c.r.B, 7)                               ), # 78
    "BIT_7_C    " : ( 121, 0, 8,  lambda c, _: bit(c.r, c.r.C, 7)                               ), # 79
    "BIT_7_D    " : ( 122, 0, 8,  lambda c, _: bit(c.r, c.r.D, 7)                               ), # 7A
    "BIT_7_E    " : ( 123, 0, 8,  lambda c, _: bit(c.r, c.r.E, 7)                               ), # 7B
    "BIT_7_H    " : ( 124, 0, 8,  lambda c, _: bit(c.r, c.r.H, 7)                               ), # 7C
    "BIT_7_L    " : ( 125, 0, 8,  lambda c, _: bit(c.r, c.r.L, 7)                               ), # 7D
    "BIT_7_vHL  " : ( 126, 0, 16, lambda c, _: bit(c.r, c.m[c.r.HL], 7)                         ), # 7E
    "BIT_7_A    " : ( 127, 0, 8,  lambda c, _: bit(c.r, c.r.A, 7)                               ), # 7F
    "RES_0_B    " : ( 128, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xFE)                   ), # 80
    "RES_0_C    " : ( 129, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xFE)                   ), # 81
    "RES_0_D    " : ( 130, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xFE)                   ), # 82
    "RES_0_E    " : ( 131, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xFE)                   ), # 83
    "RES_0_H    " : ( 132, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xFE)                   ), # 84
    "RES_0_L    " : ( 133, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xFE)                   ), # 85
    "RES_0_vHL  " : ( 134, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xFE)         ), # 86
    "RES_0_A    " : ( 135, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xFE)                   ), # 87
    "RES_1_B    " : ( 136, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xFD)                   ), # 88
    "RES_1_C    " : ( 137, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xFD)                   ), # 89
    "RES_1_D    " : ( 138, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xFD)                   ), # 8A
    "RES_1_E    " : ( 139, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xFD)                   ), # 8B
    "RES_1_H    " : ( 140, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xFD)                   ), # 8C
    "RES_1_L    " : ( 141, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xFD)                   ), # 8D
    "RES_1_vHL  " : ( 142, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xFD)         ), # 8E
    "RES_1_A    " : ( 143, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xFD)                   ), # 8F
    "RES_2_B    " : ( 144, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xFB)                   ), # 90
    "RES_2_C    " : ( 145, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xFB)                   ), # 91
    "RES_2_D    " : ( 146, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xFB)                   ), # 92
    "RES_2_E    " : ( 147, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xFB)                   ), # 93
    "RES_2_H    " : ( 148, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xFB)                   ), # 94
    "RES_2_L    " : ( 149, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xFB)                   ), # 95
    "RES_2_vHL  " : ( 150, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xFB)         ), # 96
    "RES_2_A    " : ( 151, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xFB)                   ), # 97
    "RES_3_B    " : ( 152, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xF7)                   ), # 98
    "RES_3_C    " : ( 153, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xF7)                   ), # 99
    "RES_3_D    " : ( 154, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xF7)                   ), # 9A
    "RES_3_E    " : ( 155, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xF7)                   ), # 9B
    "RES_3_H    " : ( 156, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xF7)                   ), # 9C
    "RES_3_L    " : ( 157, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xF7)                   ), # 9D
    "RES_3_vHL  " : ( 158, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xF7)         ), # 9E
    "RES_3_A    " : ( 159, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xF7)                   ), # 9F
    "RES_4_B    " : ( 160, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xEF)                   ), # A0
    "RES_4_C    " : ( 161, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xEF)                   ), # A1
    "RES_4_D    " : ( 162, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xEF)                   ), # A2
    "RES_4_E    " : ( 163, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xEF)                   ), # A3
    "RES_4_H    " : ( 164, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xEF)                   ), # A4
    "RES_4_L    " : ( 165, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xEF)                   ), # A5
    "RES_4_vHL  " : ( 166, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xEF)         ), # A6
    "RES_4_A    " : ( 167, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xEF)                   ), # A7
    "RES_5_B    " : ( 168, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xDF)                   ), # A8
    "RES_5_C    " : ( 169, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xDF)                   ), # A9
    "RES_5_D    " : ( 170, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xDF)                   ), # AA
    "RES_5_E    " : ( 171, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xDF)                   ), # AB
    "RES_5_H    " : ( 172, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xDF)                   ), # AC
    "RES_5_L    " : ( 173, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xDF)                   ), # AD
    "RES_5_vHL  " : ( 174, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xDF)         ), # AE
    "RES_5_A    " : ( 175, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xDF)                   ), # AF
    "RES_6_B    " : ( 176, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0xBF)                   ), # B0
    "RES_6_C    " : ( 177, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0xBF)                   ), # B1
    "RES_6_D    " : ( 178, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0xBF)                   ), # B2
    "RES_6_E    " : ( 179, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0xBF)                   ), # B3
    "RES_6_H    " : ( 180, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0xBF)                   ), # B4
    "RES_6_L    " : ( 181, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0xBF)                   ), # B5
    "RES_6_vHL  " : ( 182, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0xBF)         ), # B6
    "RES_6_A    " : ( 183, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0xBF)                   ), # B7
    "RES_7_B    " : ( 184, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B & 0x7F)                   ), # B8
    "RES_7_C    " : ( 185, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C & 0x7F)                   ), # B9
    "RES_7_D    " : ( 186, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D & 0x7F)                   ), # BA
    "RES_7_E    " : ( 187, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E & 0x7F)                   ), # BB
    "RES_7_H    " : ( 188, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H & 0x7F)                   ), # BC
    "RES_7_L    " : ( 189, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L & 0x7F)                   ), # BD
    "RES_7_vHL  " : ( 190, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] & 0x7F)         ), # BE
    "RES_7_A    " : ( 191, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A & 0x7F)                   ), # BF
    "SET_0_B    " : ( 192, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1)                      ), # C0
    "SET_0_C    " : ( 193, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1)                      ), # C1
    "SET_0_D    " : ( 194, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1)                      ), # C2
    "SET_0_E    " : ( 195, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1)                      ), # C3
    "SET_0_H    " : ( 196, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1)                      ), # C4
    "SET_0_L    " : ( 197, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1)                      ), # C5
    "SET_0_vHL  " : ( 198, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1)            ), # C6
    "SET_0_A    " : ( 199, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1)                      ), # C7
    "SET_1_B    " : ( 200, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 1)                 ), # C8
    "SET_1_C    " : ( 201, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 1)                 ), # C9
    "SET_1_D    " : ( 202, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 1)                 ), # CA
    "SET_1_E    " : ( 203, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 1)                 ), # CB
    "SET_1_H    " : ( 204, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 1)                 ), # CC
    "SET_1_L    " : ( 205, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 1)                 ), # CD
    "SET_1_vHL  " : ( 206, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 1)       ), # CE
    "SET_1_A    " : ( 207, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 1)                 ), # CF
    "SET_2_B    " : ( 208, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 2)                 ), # D0
    "SET_2_C    " : ( 209, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 2)                 ), # D1
    "SET_2_D    " : ( 210, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 2)                 ), # D2
    "SET_2_E    " : ( 211, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 2)                 ), # D3
    "SET_2_H    " : ( 212, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 2)                 ), # D4
    "SET_2_L    " : ( 213, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 2)                 ), # D5
    "SET_2_vHL  " : ( 214, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 2)       ), # D6
    "SET_2_A    " : ( 215, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 2)                 ), # D7
    "SET_3_B    " : ( 216, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 3)                 ), # D8
    "SET_3_C    " : ( 217, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 3)                 ), # D9
    "SET_3_D    " : ( 218, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 3)                 ), # DA
    "SET_3_E    " : ( 219, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 3)                 ), # DB
    "SET_3_H    " : ( 220, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 3)                 ), # DC
    "SET_3_L    " : ( 221, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 3)                 ), # DD
    "SET_3_vHL  " : ( 222, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 3)       ), # DE
    "SET_3_A    " : ( 223, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 3)                 ), # DF
    "SET_4_B    " : ( 224, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 4)                 ), # E0
    "SET_4_C    " : ( 225, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 4)                 ), # E1
    "SET_4_D    " : ( 226, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 4)                 ), # E2
    "SET_4_E    " : ( 227, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 4)                 ), # E3
    "SET_4_H    " : ( 228, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 4)                 ), # E4
    "SET_4_L    " : ( 229, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 4)                 ), # E5
    "SET_4_vHL  " : ( 230, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 4)       ), # E6
    "SET_4_A    " : ( 231, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 4)                 ), # E7
    "SET_5_B    " : ( 232, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 5)                 ), # E8
    "SET_5_C    " : ( 233, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 5)                 ), # E9
    "SET_5_D    " : ( 234, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 5)                 ), # EA
    "SET_5_E    " : ( 235, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 5)                 ), # EB
    "SET_5_H    " : ( 236, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 5)                 ), # EC
    "SET_5_L    " : ( 237, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 5)                 ), # ED
    "SET_5_vHL  " : ( 238, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 5)       ), # EE
    "SET_5_A    " : ( 239, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 5)                 ), # EF
    "SET_6_B    " : ( 240, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 6)                 ), # F0
    "SET_6_C    " : ( 241, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 6)                 ), # F1
    "SET_6_D    " : ( 242, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 6)                 ), # F2
    "SET_6_E    " : ( 243, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 6)                 ), # F3
    "SET_6_H    " : ( 244, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 6)                 ), # F4
    "SET_6_L    " : ( 245, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 6)                 ), # F5
    "SET_6_vHL  " : ( 246, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 6)       ), # F6
    "SET_6_A    " : ( 247, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 6)                 ), # F7
    "SET_7_B    " : ( 248, 0, 8, lambda c, _: setattr(c.r, "B", c.r.B | 1 << 7)                 ), # F8
    "SET_7_C    " : ( 249, 0, 8, lambda c, _: setattr(c.r, "C", c.r.C | 1 << 7)                 ), # F9
    "SET_7_D    " : ( 250, 0, 8, lambda c, _: setattr(c.r, "D", c.r.D | 1 << 7)                 ), # FA
    "SET_7_E    " : ( 251, 0, 8, lambda c, _: setattr(c.r, "E", c.r.E | 1 << 7)                 ), # FB
    "SET_7_H    " : ( 252, 0, 8, lambda c, _: setattr(c.r, "H", c.r.H | 1 << 7)                 ), # FC
    "SET_7_L    " : ( 253, 0, 8, lambda c, _: setattr(c.r, "L", c.r.L | 1 << 7)                 ), # FD
    "SET_7_vHL  " : ( 254, 0, 16, lambda c, _: setitem(c.m, c.r.HL, c.m[c.r.HL] | 1 << 7)       ), # FE
    "SET_7_A    " : ( 255, 0, 8, lambda c, _: setattr(c.r, "A", c.r.A | 1 << 7)                 ) # FF
}


class SimpleInstr():
    def __init__(self, name: str, value:int, argbytes:int, cycles:int, op:Callable) -> None:
        self.value = value
        self.argbytes = argbytes
        self.cycles = cycles
        self.op:Callable = op
        # Prettify the function names for printing traces
        # Prebake to optimise printing
        strname = re.sub(r"(.*)_v(\w+)(.*)", r"\1_(\2)\3", name)
        strname = re.sub(r"_n$", r"_#", strname)
        strname = re.sub(r"_n_", r"_#_", strname)
        self.str:str = f"{value:02X} {strname.replace('_', ' ')}"

    def __str__(self) -> str:
        return self.str

#for i in Instruction:
#    instrs = { i.value: SimpleInstr(i.name, i.value, i.argbytes, i.cycles, i.op) }

instrs = { i[0]: SimpleInstr(n, i[0], i[1], i[2], i[3]) for n, i in instrs_table.items()}
cbinstrs = { j[0]: SimpleInstr(n, j[0], j[1], j[2], j[3]) for n, j in cbinstrs_table.items()}