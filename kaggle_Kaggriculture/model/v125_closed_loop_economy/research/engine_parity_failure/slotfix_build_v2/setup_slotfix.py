from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup
setup(name="kagsim-slotfix-local-audit",version="0.0.1",ext_modules=[Pybind11Extension("kagsim_slotfix",["python/kagsim.cpp"],cxx_std=17,extra_compile_args=["-O3"])],cmdclass={"build_ext":build_ext})
