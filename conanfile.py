#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.scm import Git
from conan.tools.files import update_conandata, copy, collect_libs, download, replace_in_file, patch, mkdir, chdir, rename
from conan.tools.system.package_manager import Apt
import os
import glob

class KinectAzureSensorSDKConan(ConanFile):
    name = "kinect-azure-sensor-sdk"
    package_revision = "-r3"
    upstream_version = "1.4.1"
    version = "{0}{1}".format(upstream_version, package_revision)
    settings = "os", "compiler", "arch", "build_type"

    options = {
        "shared": [True, False],
        "with_jpeg": [False, "libjpeg", "libjpeg-turbo"],
    }
    default_options = {
        "shared": False,  # Must be present and must be build static (results in dynamic libraries)
        # "opencv/*:with_ffmpeg": False,
        "with_jpeg": "libjpeg",
    }

    exports = [
        "patches/**",
    ]
    url = "https://github.com/TUM-CONAN/conan-azure-kinect-sensor-sdk"

    def requirements(self):
        self.requires("openssl/1.1.1t")

        # if self.options.with_jpeg == "libjpeg":
        #     self.requires("libjpeg/9e")
        # elif self.options.with_jpeg == "libjpeg-turbo":
        #     self.requires("libjpeg-turbo/3.0.0")

        # self.requires("yuv/1749@camposs/stable")

    # def configure(self):
    #     if bool(self.options.with_jpeg):
    #         self.options["yuv"].with_jpeg = self.options.with_jpeg

    def build_requirements(self):
        self.build_requires("ninja/1.11.1")

    def system_requirements(self):
        apt = Apt(self)
        apt.install([
                #"libssl-dev",
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
        git.clone(url=sources["url"], target=self.source_folder, args=["--recursive", ])
        git.checkout(commit=sources["commit"])

    def generate(self):
        tc = CMakeToolchain(self, generator='Ninja')

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str
            tc.variables[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        # tc.variables["OpenCV_DIR"] = self.dependencies["opencv"].package_folder
        # tc.variables["OpenCV_LIBS"] = self.dependencies["opencv"].package_folder

        tc.generate()

        deps = CMakeDeps(self)

        deps.set_property("openssl", "cmake_find_mode", "module")
        deps.set_property("openssl", "cmake_file_name", "OpenSSL")
        deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")

        # deps.set_property("opencv", "cmake_find_mode", "module")
        # deps.set_property("opencv", "cmake_file_name", "OpenCV")
        # deps.set_property("opencv", "cmake_target_name", "OpenCV::OpenCV")

        # deps.set_property("yuv", "cmake_find_mode", "module")

        deps.generate()

    def layout(self):
        cmake_layout(self, src_folder="source_subfolder")

    def build(self):
        # apply patches
        if self.settings.os == "Linux":
            for p in [{"base_path": os.path.join(self.source_folder, "extern", "azure_c_shared", "src"),
                       "patch_file": os.path.join(self.recipe_folder, "patches", "fix_gcc11_compatibility_hmac.diff"),
                       "strip": 0},
                      {"base_path": os.path.join(self.source_folder, "extern", "libebml", "src"),
                       "patch_file": os.path.join(self.recipe_folder, "patches", "fix_gcc11_compatibility_ebml.diff"),
                       "strip": 0}, ]:
                patch(self, **p)

            replace_in_file(self, os.path.join(self.source_folder, "examples", "viewer", "opengl", "k4adepthpixelcolorizer.h"),
                            """#include <algorithm>""",
                            """#include <algorithm>\n#include <limits>""")

        # fix  build for vs2019
        replace_in_file(self,
                        os.path.join(self.source_folder, "tests", "Utilities", "ConnEx", "ConnEx.cpp"),
                        """#include <stdio.h>""",
                        """#include <stdio.h>\n#include <new>""")

        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        """add_subdirectory(tests)""",
                        """#add_subdirectory(tests)""")

        replace_in_file(self, os.path.join(self.source_folder, "include", "k4ainternal", "k4aplugin.h"),
            "#define K4A_PLUGIN_DYNAMIC_LIBRARY_NAME \"depthengine\"",
            "#define K4A_PLUGIN_DYNAMIC_LIBRARY_NAME \"depthengine_k4a\"")

        # replace_in_file(self, os.path.join(self.source_folder, "extern", "libyuv", "CMakeLists.txt"),
        #                 """if (NOT TARGET yuv)""",
        #                 """find_package(yuv REQUIRED)\nif (NOT TARGET yuv::yuv)""")
        # replace_in_file(self, os.path.join(self.source_folder, "extern", "libyuv", "CMakeLists.txt"),
        #                 """add_library(libyuv::libyuv ALIAS yuv)""",
        #                 """add_library(libyuv::libyuv ALIAS yuv::yuv)""")

        # fetch nuget package to extract depthengine shared library
        nuget_dir = os.path.join(self.build_folder, "nuget")
        mkdir(self, nuget_dir)
        with chdir(self, nuget_dir):
            if self.settings.os == "Linux":
                download(self, "https://dist.nuget.org/win-x86-commandline/v6.5.0/nuget.exe", "nuget.exe", md5="81352c26f518ec6d42d23517233d1912")
                self.run("mono nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.upstream_version)
            elif self.settings.os == "Windows":
                download(self, "https://dist.nuget.org/win-x86-commandline/v6.5.0/nuget.exe", "nuget.exe", md5="81352c26f518ec6d42d23517233d1912")
                self.run("nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.upstream_version)
            else:
                raise NotImplementedError("unsupported platform")

        cmake = CMake(self)
        cmake.configure()
        # @todo how to do this per package in conan 2.0?
        # cmake.parallel = False ## seems that not all internal dependencies are specified correctly..
        cmake.build()

    def _rename_depthengine_libs(self, folder, pattern):
        self.output.info("Renaming depthengine libraries in {0} with pattern {1}".format(folder, pattern))
        filenames = glob.glob(os.path.join(folder, pattern))
        for filename in filenames:
            self.output.info("Rename depthengine libname: {0} to {1}".format(filename, filename.replace("depthengine", "depthengine_k4a")))
            rename(self, filename, filename.replace("depthengine", "depthengine_k4a"))


    def package(self):
        copy(self, pattern="LICENSE", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        nuget_dir = os.path.join(self.build_folder, "nuget")
        
        if self.settings.os == "Linux":
            if self.settings.arch == "armv8":
                copy(self, "libdepthengine.*", 
                    src=os.path.join(nuget_dir, "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "linux", "lib", "native", "arm64", "release"), 
                    dst=os.path.join(self.package_folder, "lib"))
                self._rename_depthengine_libs(
                    os.path.join(self.package_folder, "lib"), 
                    "libdepthengine.*"
                    )
            elif self.settings.arch == "x86_64":
                copy(self, "libdepthengine.*", 
                    src=os.path.join(nuget_dir, "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "linux", "lib", "native", "x64", "release"), 
                    dst=os.path.join(self.package_folder, "lib"))
                self._rename_depthengine_libs(
                    os.path.join(self.package_folder, "lib"), 
                    "libdepthengine.*"
                    )
            else:
                raise NotImplementedError("unsupported platform")
        if self.settings.os == "Windows":
            copy(self, "depthengine*.dll", 
                src=os.path.join(nuget_dir, "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "lib", "native", "amd64", "release"), 
                dst=os.path.join(self.package_folder, "bin"))
            self._rename_depthengine_libs(
                os.path.join(self.package_folder, "bin"), 
                "depthengine*.dll"
                )

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.append_path("DYLD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

