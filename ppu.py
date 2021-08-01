from array import array
import functools
from mmu import MMU
from interface import Interface
from time import time

from pyglet.gl import GLubyte

from reg import LCDC, Register, STAT

ROWS, COLS = 144, 160
TILES = 384

@functools.lru_cache()
def color_code(byte1:int, byte2:int, offset:int) -> int:
    return (((byte2 >> (offset)) & 0b1) << 1) + ((byte1 >> (offset)) & 0b1)

class PPU():
    def __init__(self, interface:Interface, mem:MMU) -> None:
        self.vram = mem._vram
        self.OAM = mem.OAM
        self.io = mem.IO
        self.mem = mem
        self._ui = interface

        base = bytearray([0xFF] * (160*144))

        self._screenbuffer = (GLubyte * (160*144))(*base)
        self._tiles = array("B", [0xFF] * (TILES*8*8))
        self._sprites0 = array("B", [0xFF] * (TILES*8*8))
        self._sprites1 = array("B", [0xFF] * (TILES*8*8))

        self._LCDC = LCDC()
        self._STAT = STAT()
        self.bg_palette = Palette()
        self.OBP0 = Palette()
        self.OBP1 = Palette()
        self.ly_window = -1
        self.alpha = 0xCC  # TODO: this needs a home

        mem.add_io_handler(0xFF40, self._LCDC)
        mem.add_io_handler(0xFF41, self._STAT)
        mem.add_io_handler(0xFF47, self.bg_palette)
        mem.add_io_handler(0xFF48, self.OBP0)
        mem.add_io_handler(0xFF49, self.OBP1)

        self.scancycle = 0
        self.vblank_toggle = False
        self.frames = 0
        #self.frame_start = time()

    def clock(self, cycles:int) -> None:
        scancycle = self.scancycle + cycles
        self.scancycle = scancycle
        if self._LCDC.screen_on:
            if self._STAT.mode != 1:
                if scancycle <= 80:
                    self._STAT.mode = 2  # Searching OAM
                    if self.mem.mem[0xFFFF] & 0b00010:
                        if self._STAT.mode_2_OAM_enable:
                            self.mem.mem[0xFF0F] |= 0b00010

                elif scancycle <= 248:  # TODO: this number is based on sprite count
                    self._STAT.mode = 3
                elif scancycle <= 456:
                    self._STAT.mode = 0  # HBLANK
                    if self.mem.mem[0xFFFF] & 0b00010:
                        if self._STAT.mode_0_hblank_enable:
                            self.mem.mem[0xFF0F] |= 0b00010
            if scancycle >= 456:
                self.scancycle = scancycle % 456
                scanline = self.io[0x44]
                if scanline < 144:
                    self.render_scanline(scanline)
                elif scanline == 144:
                    self.frame()
                    if self.mem.mem[0xFFFF] & 0b00001:
                        self.mem.mem[0xFF0F] |= 0b00001
                    if self.mem.mem[0xFFFF] & 0b00010:
                        if self._STAT.mode_1_vblank_enable:
                            self.mem.mem[0xFF0F] |= 0b00010
                    self._STAT.mode = 1

                elif scanline == 153:
                    self._STAT.mode = 2
                    scanline = -1
                    self.frames += 1
                self.io[0x44] = scanline + 1
                if scanline == self.io[0x45]:
                    self._STAT.lyc_eq_ly = True
                    if self.mem.mem[0xFFFF] & 0b00010:
                        if self._STAT.lyc_eq_ly_enabled:
                            self.mem.mem[0xFF0F] |= 0b00010
                else:
                    self._STAT.lyc_eq_ly = False
        else:
            self._STAT._value = 0
            self.io[0x44] = 0
            if self.scancycle > 69768:  # A whole frame has elapsed
                self.scancycle %= 69768
                self.clear_framebuffer()
                self.frames += 1
                self.frame()
            return

    def render_scanline_fastly(self, scanline:int) -> None:
        scx = self.io[0x43]        # SCX
        scy = self.io[0x42]        # SCY
        mapoffs = 0x1800 if self._LCDC.bg_tile_map_select == 0 else 0x1C00

        mapoffs+=(((scanline+scy)&255)>>3)<<5

        lineoffs=scx>>3

        x=scx & 7
        y=(scanline+scy)&7

        pixelOffset=0

        pixelOffset=scanline * 160

        tile=self.vram[mapoffs+lineoffs]

        if not self._LCDC.tile_data_select and tile < 128:
            tile += 256

        for _ in range(160):
            self._screenbuffer[pixelOffset] = self._tiles[(tile * 64) + (y * 8) + x]
            pixelOffset += 1

            x += 1
            if x==8:
                x=0
                lineoffs=(lineoffs+1)&31
                tile=self.vram[mapoffs+lineoffs]
                if not self._LCDC.tile_data_select and tile < 128:
                    tile += 256

    def render_scanline(self, y:int) -> None:
        scx = self.io[0x43]        # SCX
        scy = self.io[0x42]        # SCY
        wx = self.io[0x4B] - 7     # WX
        wy = self.io[0x4A]         # WY

        bg_off = 0x1800 if self._LCDC.bg_tile_map_select == 0 else 0x1C00
        win_off = 0x1800 if self._LCDC.windowmap_select == 0 else 0x1C00

        # Used for the half tile at the left side when scrolling
        offset = scx & 0b111

        if self._LCDC.window_enable and wy <= y and wx < 160:
            self.ly_window += 1

        sy = (22880 - (y*160))
        for x in range(160):
            if self._LCDC.window_enable and wy <= y and wx <= x:
                wt = self.vram[win_off + (self.ly_window) // 8 * 32 % 0x400 + (x-wx) // 8 % 32]
                # If using signed tile indices, modify index
                if not self._LCDC.tile_data_select:
                    # (x ^ 0x80 - 128) to convert to signed, then
                    # add 256 for offset (reduces to + 128)
                    wt = (wt ^ 0x80) + 128
                self._screenbuffer[sy+x] = self._tiles[(8*(8*wt + (self.ly_window) % 8)) + (x-wx) % 8]
            elif self._LCDC.bg_enable:
                bt = self.vram[bg_off + (y+scy) // 8 * 32 % 0x400 + (x+scx) // 8 % 32]
                # If using signed tile indices, modify index
                if not self._LCDC.tile_data_select:
                    # (x ^ 0x80 - 128) to convert to signed, then
                    # add 256 for offset (reduces to + 128)
                    bt = (bt ^ 0x80) + 128
                #self._screenbuffer[pos] = self._tilecache[8*bt + y % 8][x % 8]
                self._screenbuffer[sy+x] = self._tiles[(8*(8*bt + (y+scy) % 8)) + (x+offset) % 8]
            else:
                self._screenbuffer[sy+x] = self.bg_palette[0]

        # Render Sprites

        bgpkey = self.bg_palette[0]
        spriteheight = 16 if self._LCDC.sprite_height else 8
        
        for n in range(0x00, 0xA0, 4):
            obj_attr = self.OAM[n:n+4]
            ypos = obj_attr[0] - 16
            xpos = obj_attr[1] - 8
            tileindex = obj_attr[2]
            if spriteheight == 16:
                tileindex &= 0b11111110
            attr = obj_attr[3]
            flip_x = attr & 0b00100000
            flip_y = attr & 0b01000000
            objpriority = attr & 0b10000000
            sprites = (self._sprites1 if attr & 0b10000 else self._sprites0)

            if ypos <= y < ypos + spriteheight:
                ty = spriteheight - (y - ypos) - 1 if flip_y else y - ypos  # tile row
                tile_row = 8 * (8 * tileindex + ty)
                sy = 22880 - (y*160)  # screen position
                row = range(7, -1 , -1) if flip_x else range(8)  # row ordering
                for tx in row:
                    pos = sy + xpos

                    if 0 <= xpos < COLS:
                        pixel = sprites[tile_row + tx]
                        if objpriority and not self._screenbuffer[pos] == bgpkey:
                            pixel = self.alpha

                        if not pixel == self.alpha:
                            self._screenbuffer[pos] = pixel
                    xpos += 1

        if y == 143:
            self.ly_window = -1

    def clear_framebuffer(self) -> None:
        self._screenbuffer[:] = [self.bg_palette[0] for _ in range(160*144)]

    def frame(self) -> None:
        # TODO: separate out - is this something for mmu?
        for t in range(0x8000, 0x9800, 16):
            for k in range(0, 16, 2): # 2 bytes for each line
                byte1 = self.vram[t + k - 0x8000]
                byte2 = self.vram[t + k + 1 - 0x8000]
                y = (t+k-0x8000)*4

                for x in range(8):
                    colorcode = ((((byte2 >> (7-x)) & 0b1) << 1) + ((byte1 >> (7-x)) & 0b1))
                    pos = x+y

                    self._tiles[pos] = self.bg_palette.arr[colorcode]
                    if colorcode == 0:
                        self._sprites0[pos] = self.alpha
                        self._sprites1[pos] = self.alpha
                    else:
                        self._sprites0[pos] = self.OBP0.arr[colorcode]
                        self._sprites1[pos] = self.OBP1.arr[colorcode]

        self._ui.update_screen(self._screenbuffer)

class Palette(Register):

    def __init__(self) -> None:
        self._value = 0
        self.arr = (GLubyte * 4)(*(0xFF, 0xA0, 60, 00))

    def __getitem__(self, val:int) -> GLubyte:
        return self.arr[val]

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, val: int) -> None:
        if self._value == val:
            return

        self._value = val
        vals = [0] * 4
        for n in range(4):
            vals[n] = 255 - (85 * ((val >> n * 2) & 0b11))
        self.arr = (GLubyte * 4)(*(vals))