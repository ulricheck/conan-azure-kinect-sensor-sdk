#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from conans import CMake, ConanFile, AutoToolsBuildEnvironment, tools

class KinectAzureSensorSDKConan(ConanFile):
    name = "kinect-azure-sensor-sdk"
    package_revision = "-r1"
    upstream_version = "1.4.1"
    version = "{0}{1}".format(upstream_version, package_revision)
    generators = "cmake"
    settings =  "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False]}
    default_options = "shared=False" # Must be present and must be build static (results in dynamic libraries)
    exports = [
        # "patches/CMakeLists.txt",
        "patches/CMakeProjectWrapper.txt",
        # "patches/FindIconv.cmake",
        # "patches/FindLibXml2.cmake",
        # "patches/xmlversion.h.patch"
    ]
    url = "https://github.com/ulricheck/conan-azure-kinect-sensor-sdk"
    source_subfolder = "source_subfolder"
    build_subfolder = "build_subfolder"
    short_paths = True

    scm = {
        "type": "git",
        "subfolder": source_subfolder,
        "url": "http://github.com/microsoft/Azure-Kinect-Sensor-SDK.git",
        "revision": "v%s" % upstream_version,
        "submodule": "recursive",
     }

    def configure(self):
        # del self.settings.compiler.libcxx
        # if 'CI' not in os.environ:
        #     os.environ["CONAN_SYSREQUIRES_MODE"] = "verify"
        pass

    def requirements(self):
        pass

    def build_requirements(self):
        self.build_requires("ninja/1.10.1")

    def system_requirements(self):
        if tools.os_info.is_linux:
            pack_names = [
                "libssl-dev",
                "uuid-dev",
                "libudev-dev",
                "libsoundio-dev",
                "nasm",
                "mono-devel",
            ]
            installer = tools.SystemPackageTool()
            for p in pack_names:
                installer.install(p)

    def configure(self):
        # del self.settings.compiler.libcxx
        # if self.settings.os == "Windows" and not self.options.shared:
        #     self.output.warn("Warning! Static builds in Windows are unstable")
        pass

    def build(self):
        # fetch nuget package to extract depthengine shared library
        tools.mkdir("nuget")
        with tools.chdir("nuget"):
            if tools.os_info.is_linux:
                tools.download("https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", "nuget.exe")
                self.run("mono nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.upstream_version)
            elif tools.os_info.is_windows:
                tools.download("https://dist.nuget.org/win-x86-commandline/latest/nuget.exe", "nuget.exe")
                self.run("nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.upstream_version)
            else:
                raise NotImplementedError("unsupported platform")


        # Import common flags and defines
        sdk_source_dir = os.path.join(self.source_folder, self.source_subfolder)
        shutil.move("patches/CMakeProjectWrapper.txt", "CMakeLists.txt")
        # shutil.move("patches/CMakeLists.txt", "%s/CMakeLists.txt" % libxml2_source_dir)
        # shutil.move("patches/FindIconv.cmake", "%s/FindIconv.cmake" % libxml2_source_dir)
        # tools.patch(libxml2_source_dir, "patches/xmlversion.h.patch")

        # fix  build for vs2019
        tools.replace_in_file(os.path.join(self.source_folder, "source_subfolder", "tests","Utilities","ConnEx","ConnEx.cpp"),
            """#include <stdio.h>""",
            """#include <stdio.h>
#include <new>""")

        cmake = CMake(self, generator='Ninja')
        cmake.parallel = False ## seems that not all internal dependencies are specified correctly..
        
        cmake.configure(build_folder=self.build_subfolder)
        cmake.build()
        cmake.install()

    def package(self):
        if tools.os_info.is_linux:
            self.copy("libdepthengine.*", symlinks=True, src=os.path.join("nuget", "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "linux", "lib", "native", "x64", "release"), dst="lib")
        if tools.os_info.is_windows:
            self.copy("depthengine*.dll", symlinks=True, src=os.path.join("nuget", "Microsoft.Azure.Kinect.Sensor.%s" % self.upstream_version, "lib", "native", "amd64", "release"), dst="bin")
        # self.copy("FindLibXml2.cmake", src="patches", dst=".", keep_path=False)
        pass

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        # if self.settings.os == "Linux" or self.settings.os == "Macos":
        #     self.cpp_info.libs.append('m')
   
