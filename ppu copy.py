import functools
import time
from array import array

import pyglet
pyglet.options['shadow_window']=False
#from PIL import Image

ROWS, COLS = 144, 160
TILES = 384

#@functools.lru_cache()
def color_code(byte1, byte2, offset):
    return (((byte2 >> (offset)) & 0b1) << 1) + ((byte1 >> (offset)) & 0b1)

class PPU():
    def __init__(self, vram, OAM, io) -> None:
        self.vram = vram
        self.oam = OAM
        self.io = io
        win = None
        for i in range(50):
            try:
                win = pyglet.window.Window(160, 144)
                break
            except pyglet.window.NoSuchConfigException:
                time.sleep(0.1)

        base = array("B", [0xFF] * (160*144))

        from pyglet.gl import GLubyte
        self._screenbuffer_raw = (GLubyte * (160*144))(*base)
        self._screen = pyglet.image.ImageData(160, 144, 'L', self._screenbuffer_raw, -160)
        self._tilecache_raw = array("B", [0xFF] * (TILES*8*8*4))

        v = memoryview(self._tilecache_raw).cast('B')
        self._tilecache = [v[i:i + 8] for i in range(0, TILES * 8 * 8, 8)]

        self.color_palette = [255, 160, 96, 00]

        self._window = win  # keep a reference
        tex = self._screen.get_texture()
        tex.tex_coords = ((0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0))
        self._screen._current_texture = tex

        @win.event
        def on_draw():
            self._window.clear()
            self._screen.set_data('L', -160, self._screenbuffer_raw)
            #imageData = pyglet.image.ImageData(256, 256, 'L', self._screenbuffer_raw, -256)
            self._screen.blit(0, 0)
            #self._fps_display.draw()

    def render_scanline(self, y):
        if y <= 143:
            for x in range(160):
                bt = self.vram[0x1800 + y // 8 * 32 % 0x400 + x // 8 % 32]
                # If using signed tile indices, modify index
                if False:
                    # (x ^ 0x80 - 128) to convert to signed, then
                    # add 256 for offset (reduces to + 128)
                    bt = (bt ^ 0x80) + 128
                pos = y*160 + x
                self._screenbuffer_raw[pos] = self._tilecache[8*bt + y % 8][x % 8]


                    #std::vector<u8> pixel_line = get_pixel_line(pixels_1, pixels_2);

                    #for (uint x = 0; x < TILE_WIDTH_PX; x++) {
                    #    buffer[pixel_index(x, tile_line)] = get_color(pixel_line[x]);
            
        elif y == 144:
            for t in range(0x8000, 0x9800, 16):
                for k in range(0, 16, 2): # 2 bytes for each line
                    byte1 = self.vram[t + k - 0x8000]
                    byte2 = self.vram[t + k + 1 - 0x8000]
                    y = (t+k-0x8000) // 2

                    for x in range(8):
                        colorcode = color_code(byte1, byte2, 7 - x)
                        #colorcode = ((((byte2 >> (x)) & 0b1) << 1) + ((byte1 >> (x)) & 0b1))

                        self._tilecache[y][x] = self.color_palette[colorcode]
            pyglet.clock.tick()

            for window in pyglet.app.windows:
                window.switch_to()
                window.dispatch_events()
                window.dispatch_event('on_draw')
                window.flip()
        return
