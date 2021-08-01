import time

import pyglet # TODO: reclass exceptions

from mbc import MBC
from cpu import CPU
from interface import Interface
from mmu import MMU
from ppu import PPU

print("name", __name__)

def nop(dt: float) -> None:
    pass

def gb() -> None:
    for _ in range(50):
        try:
            interface = Interface(320, 288, vsync=False)
            break
        except (pyglet.window.NoSuchConfigException, pyglet.gl.ContextException):
            time.sleep(0.1)
    else:
        raise Exception("Failed to create window")
    print("Window OK")

    crt = MBC("poke.gb")
    mem = MMU(interface, crt)
    ppu = PPU(interface, mem)
    cpu = CPU(mem, ppu, interface)

    crt.load_rom(boot=True)
    cpu.boot()
    interface.set_caption("AshnasGB - " + crt.get_rom_name())


    pyglet.clock.schedule_interval(cpu.advance_frame, 1/59.7)
    pyglet.clock.schedule(nop)  # speedhack
    pyglet.clock.schedule_interval(interface.update_fps, 1.0)
    #import cProfile, pstats, io
    #from pstats import SortKey
    #pr = cProfile.Profile()
    #pr.enable()
    pyglet.app.run()
    #pr.disable()
    #s = io.StringIO()
    #sortby = SortKey.CUMULATIVE
    #ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    #ps.print_stats()
    #print(s.getvalue())

gb()
