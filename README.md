# LiuD_Kaleidoscope
LiuD demo: Kaleidoscope

keywords: LiuD, LLVM, llvmlite, mandelbrot

need
  - Python 2.x
  - https://github.com/Bookaa/LiuD
  - llvmlite

refer to https://github.com/eliben/pykaleidoscope/blob/master/chapter6.py

how to run:
  - clone https://github.com/Bookaa/LiuD, and generate file Ast_Ks.py by:
        python LiuD/MainGen.py Syntax_Kaleidoscope.py py > Ast_Ks.py
  - cp LiuD/lib.py .
  - python main.py
