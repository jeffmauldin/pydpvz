# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
from spack.package import *


class PyDpvz(PythonPackage):
    """Python wrappers for the DPvz C++ parallel I/O library."""

    homepage = "https://github.com/sandialabs/dpvz"
    git = "https://github.com/sandialabs/dpvz.git"
    
    # For local iterative development, comment out the git url above
    # and uncomment the local file URL below:
    # git = f"file://{os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))}"

    version("main", branch="main")

    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-pybind11", type=("build", "link", "run"))
    depends_on("cmake", type="build")
    depends_on("mpi")
