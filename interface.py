import sys

import pyglet
pyglet.options['shadow_window']=False
from pyglet.gl import *

# Buttons
# Bit 7 - Not used
# Bit 6 - Not used
# Bit 5 - P15 Select Button Keys      (0=Select)
# Bit 4 - P14 Select Direction Keys   (0=Select)
# Bit 3 - P13 Input Down  or Start    (0=Pressed) (Read Only)
# Bit 2 - P12 Input Up    or Select   (0=Pressed) (Read Only)
# Bit 1 - P11 Input Left  or Button B (0=Pressed) (Read Only)
# Bit 0 - P10 Input Right or Button A (0=Pressed) (Read Only)

class Interface(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._direction = 0xF
        self._button = 0xF
        self.direction_enable = False
        self.button_enable = False
        self.exit_triggered = False
        # match projection to window resolution (could be in reshape callback)
        glMatrixMode(GL_PROJECTION)
        glOrtho(0, 320, 0, 288, -1, 1)
        glMatrixMode(GL_MODELVIEW)

        # creating a texture
        texs = (GLuint * 1) ()
        glGenTextures(1, texs)
        self.tex = texs[0]
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    def update_screen(self, screen):
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE, 160, 144, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, screen)
        glBindTexture(GL_TEXTURE_2D, 0)

    def on_draw(self):
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glEnable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        glTexCoord2i(0, 0); glVertex2i(0, 0)
        glTexCoord2i(0, 1); glVertex2i(0, 288)
        glTexCoord2i(1, 1); glVertex2i(320, 288)
        glTexCoord2i(1, 0); glVertex2i(320, 0)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        glFlush()
        
    def on_close(self):
        self.exit_triggered = True

    def on_key_press(self, symbol, modifiers):
        if symbol == 65363: # RIGHT
            self._direction &= ~0x1
        elif symbol == 65361: # LEFT
            self._direction &= ~0x2
        elif symbol == 65362: # UP
            self._direction &= ~0x4
        elif symbol == 65364: # DOWN
            self._direction &= ~0x8

        elif symbol == 122: # A
            self._button &= ~0x1
        elif symbol == 120: # B
            self._button &= ~0x2
        elif symbol == 65293: # SELECT
            self._button &= ~0x4
        elif symbol == 32: # START
            self._button &= ~0x8
        elif symbol == 65307: # ESC
            self.exit_triggered = True

    def on_key_release(self, symbol, modifiers):
        if symbol == 65363: # RIGHT
            self._direction |= 0x1
        elif symbol == 65361: # LEFT
            self._direction |= 0x2
        elif symbol == 65362: # UP
            self._direction |= 0x4
        elif symbol == 65364: # DOWN
            self._direction |= 0x8

        elif symbol == 122: # A
            self._button |= 0x1
        elif symbol == 120: # B
            self._button |= 0x2
        elif symbol == 65293: # SELECT
            self._button |= 0x4
        elif symbol == 32: # START
            self._button |= 0x8


    @property
    def input(self):
        buttons = 0x00
        if self.direction_enable:
            buttons |= self._direction

        if self.button_enable:
            buttons |= self._button

        buttons |= (not self.direction_enable) << 4
        buttons |= (not self.button_enable) << 5

        return buttons

    @input.setter
    def input(self, val):
        self.direction_enable = val & (1 << 4) == 0
        self.button_enable = val & (1 << 5) == 0
