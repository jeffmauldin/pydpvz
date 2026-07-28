import os
import sys
from setuptools import setup, find_packages
from pybind11.setup_helpers import Pybind11Extension, build_ext
import mpi4py

sources = [
    "src/main_bindings.cpp",
    "../dpvz/src/DPvzErr.C",
    "../dpvz/src/DPvzFile.C",
    "../dpvz/src/DPvzGlobal.C",
    "../dpvz/src/DPvzMetadata.C",
    "../dpvz/src/DPvzMode.C",
    "../dpvz/src/DPvzRankToc.C",
    "../dpvz/src/DPvzToc.C",
    "../dpvz/src/DPvzTocEntry.C",
    "../dpvz/src/DPvzTocIndex.C",
    "../dpvz/src/DPvzUtil.C",
    "../dpvz/src/DPvzVtk.C",
    "../dpvz/src/DPvzVtkData.C",
]

ext_modules = [
    Pybind11Extension(
        "pydpvz._pydpvz",
        sources,
        include_dirs=[
            "../dpvz/src",
            "/usr/include/x86_64-linux-gnu/mpich",
            mpi4py.get_include(),
        ],
        define_macros=[("DPVZ_MPI", "1")],
        libraries=["mpichcxx", "mpich", "z"],
        library_dirs=["/usr/lib/x86_64-linux-gnu"],
        extra_compile_args=["-std=c++17", "-O3"],
        extra_link_args=[
            "-Wl,-rpath,/usr/lib/x86_64-linux-gnu",
        ],
    ),
]

setup(
    name="pydpvz",
    version="0.1.0",
    packages=find_packages(),
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
