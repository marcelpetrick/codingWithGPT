# Test to create a webserver, which serves the homepage as pure C++

Friend: "I'm a full-stack developer."  
Me: "Cool, I write C++. Me too."  
He laughed.  
  
I wrote a C++ program serving my homepage—no idiomatic #HTML in sight.  
  
Q.E.D.  

## constraints
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

## base64 encoder online to convert whatever page you want to display
See https://www.base64encode.org/

## last remarks
Works as expected. Of course, the major part of the links are dead, because they are relative. But the homepage was re-created 1:1. So now I am a #fullstackdeveloper, lol.
