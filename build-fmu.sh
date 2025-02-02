#!/bin/sh

echo "loadFile(\"$1.mo\"); buildModelFMU($1,fmuType=\"cs\")" | OMShell-terminal

