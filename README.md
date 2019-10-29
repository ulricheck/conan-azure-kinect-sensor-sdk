# conan-azure-kinect-sensor-sdk

Conan package for Microsoft Azure Kinect Sensor SDK library

- Install Mono for Kinect SDK build
  ```
  $ sudo apt-get install -y --no-install-recommends gnupg ca-certificates
  $ sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
  $ sudo echo "deb https://download.mono-project.com/repo/ubuntu stable-bionic main" | sudo tee /etc/apt/sources.list.d/mono-official-stable.list
  $ sudo apt update --fix-missing && sudo  apt-get install -y --no-install-recommends mono-devel
  ```
