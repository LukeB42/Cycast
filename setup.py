from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        "audio_buffer",
        ["audio_buffer.pyx"],
        extra_compile_args=['-O3', '-march=native', '-ffast-math'],
        language="c"
    ),
    Extension(
        "stream_broadcaster",
        ["stream_broadcaster.pyx"],
        extra_compile_args=['-O3', '-march=native'],
        language="c"
    ),
]

setup(
    name="Cycast Cython Modules",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': 3,
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
            'embedsignature': True,
        }
    ),
)
