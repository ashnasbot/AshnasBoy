import functools
from array import array

import pyglet

from reg import LCDC

ROWS, COLS = 144, 160
TILES = 384

@functools.lru_cache()
def color_code(byte1, byte2, offset):
    return (((byte2 >> (offset)) & 0b1) << 1) + ((byte1 >> (offset)) & 0b1)

class PPU():
    def __init__(self, interface, mem) -> None:
        self.vram = mem._vram
        self.oam = mem.OAM
        self.io = mem.IO
        self.mem = mem
        self._interface = interface

        base = bytearray([0xFF] * (160*144))

        from pyglet.gl import GLubyte
        self._screenbuffer = (GLubyte * (160*144))(*base)
        self._tiles = array("B", [0xFF] * (TILES*8*8))

        self.color_palette = (GLubyte * 4)(*(0xFF, 160, 96, 00))
        self._LCDC = LCDC()
        self._STAT = STAT()
        self.ly_window = -1

        mem.add_io_handler(0xFF40, self._LCDC)
        mem.add_io_handler(0xFF41, self._STAT)

        self.scancycle = 0
        self.vblank_toggle = False
        self.frames = 0
        self.frame_start = time()

    def clock(self, cycles):
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
                    tgt = self.frame_start + (1/59.7)

                    while tgt >= time():  # Crude frame limiter
                        continue
                    self.frame_start = time()
                self.io[0x44] = scanline + 1
                if scanline == self.io[0x45]:
                    self._STAT.lyc_eq_ly = True
                    if self.mem.mem[0xFFFF] & 0b00010:
                        if self._STAT.lyc_eq_ly_enabled:
                            self.mem.mem[0xFF0F] |= 0b00010
                else:
                    self._STAT.lyc_eq_ly = False
        else:
            if self.scancycle > 69768:  # A whole frame has elapsed
                self.scancycle %= 69768
                self.clear_framebuffer()
                self.frames += 1
                tgt = self.frame_start + (1/59.7)

                while tgt >= time():  # Crude frame limiter
                    continue
                self.frame()
                self.frame_start = time()

    def render_scanline(self, y):
        scx = self.io[0x43]        # SCX
        scy = self.io[0x42]        # SCY
        wx = self.io[0x4B] - 7     # WX
        wy = self.io[0x4A]         # WY

        bg_off = 0x1800 if self._LCDC.backgroundmap_select == 0 else 0x1C00

        # Used for the half tile at the left side when scrolling
        offset = scx & 0b111

        for x in range(160):
            pos = (22880 - (y*160)) + x
            if self._LCDC.background_enable:
                bt = self.vram[bg_off + (y+scy) // 8 * 32 % 0x400 + (x+scx) // 8 % 32]
                # If using signed tile indices, modify index
                if not self._LCDC.tiledata_select:
                    # (x ^ 0x80 - 128) to convert to signed, then
                    # add 256 for offset (reduces to + 128)
                    bt = (bt ^ 0x80) + 128
                #self._screenbuffer_raw[pos] = self._tilecache[8*bt + y % 8][x % 8]
                self._screenbuffer_raw[pos] = self._tilecache_raw[(8*(8*bt + (y+scy) % 8)) + (x+offset) % 8]
            else:
                self._screenbuffer_raw[pos] = self.color_palette[0]

    def frame(self):
        # TODO: separate out - is this something for mmu?
        for t in range(0x8000, 0x9800, 16):
            for k in range(0, 16, 2): # 2 bytes for each line
                byte1 = self.vram[t + k - 0x8000]
                byte2 = self.vram[t + k + 1 - 0x8000]
                y = (t+k-0x8000) // 2

                for x in range(8):
                    colorcode = ((((byte2 >> (7-x)) & 0b1) << 1) + ((byte1 >> (7-x)) & 0b1))

                    self._tiles[(y*8) + x] = self.color_palette[colorcode]

        self._interface.update_screen(self._screenbuffer)
        pyglet.clock.tick()

        for window in pyglet.app.windows:
            window.switch_to()
            window.dispatch_events()
            if window.exit_triggered:
                import sys
                sys.exit(0)
            window.dispatch_event('on_draw')
            window.flip()
