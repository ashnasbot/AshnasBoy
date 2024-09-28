$ErrorActionPreference = "Stop"

mypyc .\cpu.py .\gb.py .\reg.py .\ppu.py .\mbc.py .\mmu.py .\instruction.py
python -c "import gb"