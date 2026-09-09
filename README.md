# DyCMAT
## Dynamic Cascading Failure Modelling and Analysis Tool (DyCMAT)

Dynamic Cascading Failure Modelling and Analysis Tool Using the DIgSILENT PowerFactory and Python API.

DyCMAT is a Python-based graphical interface developed for advanced cascading-failure analysis, dynamic security assessment, and resilience-oriented studies of converter-dominated power systems using the DIgSILENT PowerFactory API.

The tool provides an integrated framework for:
- RMS dynamic simulation automation
- Cascading contingency analysis
- Protection and relay modelling
- Dynamic cascading-failure workflows
- Converter-dominated grid resilience studies

-------------------------------------------------------------------------------

# Main Functionalities

## Initialization and Dynamic Simulation
- Automatic execution
- RMS dynamic simulation automation
- PowerFactory project/study-case activation

## Cascading Analysis
- Random N-k contingency generation
- Sequential outage-event creation
- Cascading-failure execution workflow
- Automatic PowerFactory output export
- Batch contingency simulations

## Dynamic Cascading Modelling
The tool supports automated installation and configuration of:
- Overloading relays
- Under-frequency load shedding 
- Generator frequency tripping
- Over-voltage tripping 
- Under-voltage tripping 

-------------------------------------------------------------------------------

# System Requirements

## Required Software
- Microsoft Windows 10/11
- DIgSILENT PowerFactory 2023
- Valid DIgSILENT PowerFactory license
- PowerFactory Python 3.10 API environment

## Important Note
Although distributed as an executable application (.exe), DyCFMAT operates as an external interface/controller for DIgSILENT PowerFactory and therefore requires an installed PowerFactory environment.


# How to Run

## Using the Executable
1. Install and activate DIgSILENT PowerFactory.
2. Open the desired PowerFactory project/study case.
3. Launch DyCFMAT.exe.
4. Configure the simulation settings.
5. Run the selected workflow.

-------------------------------------------------------------------------------

# Related Publications

If you use this software in academic work, please cite the following references:

## IEEE Access 2025
S. Hashemi, M. Asprou, L. Hadjidemetriou and M. Panteli,
"Quantifying and Mitigating Cascading Impacts in HVdc-Interconnected Power Grids,"
IEEE Access, vol. 13, pp. 154491-154507, 2025.
DOI: https://doi.org/10.1109/ACCESS.2025.3603695

## Sustainable Energy, Grids and Networks 2025
S. Hashemi, V. S. Rajkumar, A. Ştefanov, and M. Panteli,
"Cyber-physical-aware cascading mitigation in converter-dominated power systems,"
Sustainable Energy, Grids and Networks, vol. 44, p. 102065, 2025.
DOI: https://doi.org/10.1016/j.segan.2025.102065

-------------------------------------------------------------------------------

# License and Rights Reserved

Copyright © 2025.

All rights reserved.

This software interface, source code structure, workflows, and related implementations were developed for research activities associated with the University of Cyprus.

Redistribution, commercial use, or modification without permission from the developer/authors is not permitted.

DIgSILENT PowerFactory is a third-party software package and is not distributed with this repository.

-------------------------------------------------------------------------------

# Disclaimer

This software is intended for academic and research purposes only.

The developers/authors are not responsible for:
- incorrect engineering use,
- operational decisions,
- system-security violations,
- or damages resulting from misuse of the tool.

Users are responsible for validating all simulation results independently.

-------------------------------------------------------------------------------

# Contact

Developer:
Sina Hashemi
hashemi.seyedsina@ucy.ac.cy
hashemi.sina86@gmail.com

Mathaios Panteli
panteli.mathaios@ucy.ac.cy

Institution:
KIOS Research Center of Excellence, University of Cyprus

Research Areas:
- Power-system resilience
- Cascading-failure analysis
- Converter-dominated grids
- HVDC-interconnected systems
- IBR-integrated systems
