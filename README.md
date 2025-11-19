
# Cosimulation with OpenPLC and Functional Mockup Units (FMU)

This repository provides helper scripts to build FMUs (.fmu files) from [OpenModelica](https://openmodelica.org) models (.mo files) and run them in a cosimulation with [OpenPLC](https://autonomylogic.com). The communication between the FMU simulation and the PLC uses ModbusTCP.

To install OpenModelica on a Linux system, you can use the `install-openmodelica.sh` script. This script is taken from the OpenModelica [installation instructions](https://openmodelica.org/download/download-linux/).

The `install-simulation.sh` script sets up a new local Python venv to run the simulations.

To build an FMU, use the `build-fmu.sh` script. For example, to build `Tanks.fmu` from `Tanks.mo`, run:

```
sh build-fmu.sh Tanks
```

Once the FMU is built, the simulation can be run with:

```
sh run-simulation.sh <FMU file> <ST file> [<step size>] [<duration>]
```

where ``ST file`` is the PLC program file generated from OpenPLC Editor for the OpenPLC runtime. Optionally, you can indicate a desired step size and duration of the simulation in seconds as a floating point value. Without a duration, the simulation executes until the process is killed.
