#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from conans import CMake, ConanFile, AutoToolsBuildEnvironment, tools

class KinectAzureSensorSDKConan(ConanFile):
    name = "kinect-azure-sensor-sdk"
    package_revision = ""
    upstream_version = "1.2.0"
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
        "revision": "v%s" % version,
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
        pass

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
                self.run("mono nuget.exe install Microsoft.Azure.Kinect.Sensor -Version %s" % self.version)
            elif tools.os_info.is_windows:
                raise NotImplementedError("need to download the nuget package with dotnet/nuget..")
            else:
                raise NotImplementedError("unsupported platform")


        # Import common flags and defines
        sdk_source_dir = os.path.join(self.source_folder, self.source_subfolder)
        shutil.move("patches/CMakeProjectWrapper.txt", "CMakeLists.txt")
        # shutil.move("patches/CMakeLists.txt", "%s/CMakeLists.txt" % libxml2_source_dir)
        # shutil.move("patches/FindIconv.cmake", "%s/FindIconv.cmake" % libxml2_source_dir)
        # tools.patch(libxml2_source_dir, "patches/xmlversion.h.patch")

        cmake = CMake(self)
        cmake.parallel = False ## seems that not all internal dependencies are specified correctly..
        
        cmake.configure(build_folder=self.build_subfolder)
        cmake.build()
        cmake.install()

    def package(self):
        if tools.os_info.is_linux:
            self.copy("libdepthengine.*", src=os.path.join("nuget", "Microsoft.Azure.Kinect.Sensor.%s" % self.version, "linux", "lib", "native", "x64", "release"), dst="lib")
        # self.copy("FindLibXml2.cmake", src="patches", dst=".", keep_path=False)
        pass

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        # if self.settings.os == "Linux" or self.settings.os == "Macos":
        #     self.cpp_info.libs.append('m')
   
