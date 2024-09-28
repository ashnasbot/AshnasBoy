from enum import Enum
import os
from typing import Union


# Flags
class MBC_MODE(Enum):
    ROM = 0
    RAM = 1


class MBC_TYPE(Enum):
    # need better sorting of type functionality
    NONE = 0x00
    MBC1 = 0x04
    MBC2 = 0x05
    MBC3 = 0x10
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


class MBC():

    def __init__(self, file: str, boot: bool = False) -> None:
        self._rom: list[memoryview] = []
        self.type = MBC_TYPE.NONE
        self.rom_size = 0
        self.mode = MBC_MODE.ROM
        self.ram_enabled = False
        self.upper_bank = 0
        self.file = file
        self.rom_name: Union[str, None] = None
        self.bank0: memoryview = memoryview(bytearray(0x4000))
        self.bank1: memoryview = memoryview(bytearray(0x4000))

    def get_mbc(self, bank: memoryview) -> MBC_TYPE:
        return MBC_TYPE(bank[0x147])

    def get_rom_size(self, bank: memoryview) -> int:
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
        }
        return banks[size]

    def load_rom(self, boot: bool = False) -> None:
        self._rom = []  # clear rom
        path = os.path.join("roms", self.file)
        with open(path, "r+b") as f:
            # Read first two banks
            self.rom_name = self.file
            if self.rom_size == 0:
                bank = memoryview(bytearray(0x4000))
                f.readinto(bank)  # type: ignore # https://github.com/python/typing/issues/659#issuecomment-638384893
                self.rom_size = self.get_rom_size(bank)
                self.type = self.get_mbc(bank)
                self._rom.append(bank)

            while True:
                # Read remainder of ROM
                bank = memoryview(bytearray(0x4000))
                if f.readinto(bank) == 0:  # type: ignore # https://github.com/python/typing/issues/659#issuecomment-638384893
                    break
                self._rom.append(bank)

        bootrom = os.path.join("roms", "boot.bin")
        if boot and os.path.isfile(bootrom):
            with open(bootrom, "r+b") as f:
                print("Running boot rom")
                bank = memoryview(bytearray(0x100))
                f.readinto(bank)  # type: ignore # https://github.com/python/typing/issues/659#issuecomment-638384893
                self._rom[0][0:0x100] = bank[:]
        else:
            print("Loading", os.path.abspath(path))

        self.bank0[:] = self._rom[0]
        if len(self._rom) > 1:
            self.bank1[:] = self._rom[1]

    def get_rom_name(self) -> str:
        return self._rom[0][0x0134:0x0143].tobytes().decode()

    def disable_bootrom(self, val: int) -> None:
        if val == 0x01:
            self.load_rom()

    def __setitem__(self, key: int, val: int) -> None:
        if self.type == MBC_TYPE.NONE:
            return
        elif self.type == MBC_TYPE.MBC1:
            if key < 0x2000:  # RAM Gate
                self.ram_enabled = val & 0b1111 == 0b1010
            elif key < 0x4000:  # MBC1 Bank 1 0x2000 - 0x3FFF

                bank = val & 0b00011111    # Bit 7-5 ignored

                if bank == 0:
                    bank = 1
                bank += self.upper_bank
                self.bank1[:] = self._rom[bank % (self.rom_size // 16384)]
            elif key < 0x6000:  # RAM Bank Number / Upper Bits of ROM Bank no 0x4000 - 0x5FFF
                if self.mode == MBC_MODE.ROM:
                    self.upper_bank = (val & 0x03) << 5
                else:
                    pass
            else:  # ROM/RAM Mode select 0x6000 - 0x7FFF
                mode = val & 0x01
                if mode:
                    self.mode = MBC_MODE.RAM
                    self.bank0[:] = self._rom[self.upper_bank % (self.rom_size // 16384)]
                else:
                    self.mode = MBC_MODE.ROM
                    self.bank0[:] = self._rom[0]

        elif self.type == MBC_TYPE.MBC2:
            if key < 0x4000:  # RAM Enable and Bank switching
                if val & 0x10:
                    print(f"MBC2 - {key:04x} = {val:08b}")
                    bank = val & 0x0F
                    if bank == 0:
                        bank = 1
                    self.bank1[:] = self._rom[bank % (self.rom_size // 16384)]
                else:
                    self.ram_enabled = val & 0x0A == 0x0A
        elif self.type == MBC_TYPE.MBC3:
            if key < 0x2000:  # RAM Gate
                self.ram_enabled = val & 0b1111 == 0b1010
            elif key < 0x4000:  # MBC1 Bank 1 0x2000 - 0x3FFF
                bank = val

                if bank == 0:
                    bank = 1
                self.bank1[:] = self._rom[bank % (self.rom_size // 16384)]
            elif key < 0x6000:  # RAM Bank Number / Upper Bits of ROM Bank no 0x4000 - 0x5FFF
                self.ram_bank = (val & 0x03)
