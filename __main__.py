import time

import pyglet # TODO: reclass exceptions

from cpu import CPU
from interface import Interface
from mmu import MMU
from ppu import PPU

if __name__ == "__main__":
    for i in range(50):
        try:
            interface = Interface(320, 288, vsync=False)
            break
        except (pyglet.window.NoSuchConfigException, pyglet.gl.ContextException):
            time.sleep(0.1)
    else:
        raise Exception("Failed to create window")
    print("Window OK")

    mem = MMU(interface)
    ppu = PPU(interface, mem)
    cpu = CPU(mem, ppu)

    cpu.boot("poke.gb")

    cpu.run()