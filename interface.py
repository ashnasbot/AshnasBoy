from typing import Any, ByteString

import pyglet
pyglet.options['shadow_window'] = False
from pyglet.gl import GL_NEAREST
from pyglet.math import Mat4



class Interface(pyglet.window.Window):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.frame_ready = False
        self.frames = 0
        self._direction = 0xF
        self._button = 0xF
        self.direction_enable = False
        self.button_enable = False
        pyglet.image.Texture.default_mag_filter = GL_NEAREST
        self.projection = Mat4.orthogonal_projection(
            0, 320, 0, 288, -255, 255
        )
        self.fps = 0.0

        self._game_caption = ""
        self.view = self.view.scale((2, 2, 1))

        icon = pyglet.image.load('icon.png')
        self.set_icon(icon)

    def update_screen(self, screen: ByteString) -> None:
        self.buf = pyglet.image.ImageData(160, 144, 'L', screen)
        self.frame_ready = True

    def update_fps(self, dt: float) -> None:
        self.fps = self.frames / dt
        self.frames = 0
        if self._game_caption:
            self.set_caption(f"{self.fps:.2f} {self._game_caption} ")
        else:
            self._game_caption = self.caption

    def on_draw(self) -> None:
        pass

    def do_drawing(self, dt: float) -> None:
        if not self.frame_ready:
            return
        self.buf.blit(0, 0)

        self.frames += 1
        self.frame_ready = False
        return

    def on_close(self) -> None:
        pyglet.app.exit()

    # Buttons
    # Bit 7 - Not used
    # Bit 6 - Not used
    # Bit 5 - P15 Select Button Keys      (0=Select)
    # Bit 4 - P14 Select Direction Keys   (0=Select)
    # Bit 3 - P13 Input Down  or Start    (0=Pressed) (Read Only)
    # Bit 2 - P12 Input Up    or Select   (0=Pressed) (Read Only)
    # Bit 1 - P11 Input Left  or Button B (0=Pressed) (Read Only)
    # Bit 0 - P10 Input Right or Button A (0=Pressed) (Read Only)

    def on_key_press(self, symbol: int, _: int) -> None:
        if symbol == 65363:  # RIGHT
            self._direction &= ~0x1
        elif symbol == 65361:  # LEFT
            self._direction &= ~0x2
        elif symbol == 65362:  # UP
            self._direction &= ~0x4
        elif symbol == 65364:  # DOWN
            self._direction &= ~0x8

        elif symbol == 122:  # A
            self._button &= ~0x1
        elif symbol == 120:  # B
            self._button &= ~0x2
        elif symbol == 65293:  # SELECT
            self._button &= ~0x4
        elif symbol == 32:  # START
            self._button &= ~0x8

    def on_key_release(self, symbol: int, _: int) -> None:
        if symbol == 65363:  # RIGHT
            self._direction |= 0x1
        elif symbol == 65361:  # LEFT
            self._direction |= 0x2
        elif symbol == 65362:  # UP
            self._direction |= 0x4
        elif symbol == 65364:  # DOWN
            self._direction |= 0x8

        elif symbol == 122:  # A
            self._button |= 0x1
        elif symbol == 120:  # B
            self._button |= 0x2
        elif symbol == 65293:  # SELECT
            self._button |= 0x4
        elif symbol == 32:  # START
            self._button |= 0x8
        elif symbol == 65307:  # ESC
            pyglet.app.exit()

    @property
    def input(self) -> int:
        buttons = 0x00
        if self.direction_enable:
            buttons |= self._direction

        if self.button_enable:
            buttons |= self._button

        buttons |= (not self.direction_enable) << 4
        buttons |= (not self.button_enable) << 5

        return buttons

    @input.setter
    def input(self, val: int) -> None:
        self.direction_enable = val & (1 << 4) == 0
        self.button_enable = val & (1 << 5) == 0
