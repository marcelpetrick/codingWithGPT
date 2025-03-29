# Test to create a webserver, which serves the homepage as pure C++
* least extensions possible
* cpp20
* goal: no directly visible html (encode ... maybe bas64?)

## build
```sh
mkdir build
cd build
cmake ..
make -j12
```

## run - sudo needed to bind the port
```sh
sudo ./marcelpetrick.it.webserver
```
