#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.scm import Git
from conan.tools.files import load, update_conandata, copy, collect_libs, get, replace_in_file, patch, mkdir, chdir
from conan.tools.microsoft.visual import check_min_vs
from conan.tools.system.package_manager import Apt
import os
import shutil


class KinectAzureSensorSDKConan(ConanFile):
    name = "kinect-azure-sensor-sdk"
    package_revision = "-r2"
    upstream_version = "1.4.1"
    version = "{0}{1}".format(upstream_version, package_revision)
    settings = "os", "compiler", "arch", "build_type"

    options = {
        "shared": [True, False]
    }
    default_options = {
        "shared": False,  # Must be present and must be build static (results in dynamic libraries)
        # "opencv/*:with_ffmpeg": False,
        "opencv/*:with_jpeg": "libjpeg-turbo",
    }

    exports = [
        "patches/**",
    ]
    url = "https://github.com/TUM-CONAN/conan-azure-kinect-sensor-sdk"

    def requirements(self):
        self.requires("opencv/4.5.5")

    def build_requirements(self):
        self.build_requires("ninja/1.11.1")

    def system_requirements(self):
        apt = Apt(self)
        apt.install([
                "libssl-dev",
                "uuid-dev",
                "libudev-dev",
                "libsoundio-dev",
                "nasm",
                "mono-devel",
            ])

    def export(self):
        update_conandata(self, {"sources": {
            "commit": "v%s" % self.upstream_version,
            "url": "https://github.com/microsoft/Azure-Kinect-Sensor-SDK.git"
            }}
            )

    def source(self):
        git = Git(self)
        sources = self.conan_data["sources"]
        git.clone(url=sources["url"], target=self.source_folder)
        git.checkout(commit=sources["commit"])
        # missing recursive

        if self.settings.os == "Linux":
            for p in [{"base_path": os.path.join(self.source_folder, "extern", "azure_c_shared", "src"),
                       "patch_file": "patches/fix_gcc11_compatibility_hmac.diff",
                       "strip": 0},
                      {"base_path": os.path.join(self.source_folder, "extern", "libebml", "src"),
                       "patch_file": "patches/fix_gcc11_compatibility_ebml.diff",
                       "strip": 0}, ]:
                patch(self, **p)

            replace_in_file(self, os.path.join(self.source_folder, "examples", "viewer", "opengl", "k4adepthpixelcolorizer.h"),
                            """#include <algorithm>""",
                            """#include <algorithm>\n#include <limits>""")

    def generate(self):
        tc = CMakeToolchain(self)

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str
            tc.variables[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def layout(self):
        cmake_layout(self, src_folder="source_subfolder")

    def build(self):
        # fetch nuget package to extract depthengine shared library
        mkdir(self, "nuget")
        with chdir(self, "nuget"):
            if self.settings.os == "Linux":
                get(self, "https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", "nuget.exe")
                self.run("mono nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.upstream_version)
            elif self.settings.os == "Windows":
                get(self, "https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", "nuget.exe")
                self.run("nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.upstream_version)
            else:
                raise NotImplementedError("unsupported platform")

        # Import common flags and defines
        sdk_source_dir = self.source_folder
        shutil.move("patches/CMakeProjectWrapper.txt", "CMakeLists.txt")

        # fix  build for vs2019
        replace_in_file(self,
                        os.path.join(self.source_folder, "tests", "Utilities", "ConnEx", "ConnEx.cpp"),
                        """#include <stdio.h>""",
                        """#include <stdio.h>\n#include <new>""")

        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        """add_subdirectory(tests)""",
                        """#add_subdirectory(tests)""")

        cmake = CMake(self)
        cmake.configure()
        # @todo how to do this per package in conan 2.0?
        # cmake.parallel = False ## seems that not all internal dependencies are specified correctly..
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        if self.settings.os == "Linux":
            copy(self, "libdepthengine.*", src=os.path.join("nuget", "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "linux", "lib", "native", "x64", "release"), dst="lib")
        if self.settings.os == "Windows":
            copy(self, "depthengine*.dll", src=os.path.join("nuget", "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "lib", "native", "amd64", "release"), dst="bin")

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)

