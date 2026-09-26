# Problem Understanding

## The Requirement

Build a web-based interactive 3D visualization platform that integrates numerical ocean model
outputs with in-situ observations.

## The Real Gap

The gap is not "ocean data is not visualized in 3D." It is that **model output and observation
data live in separate worlds**, and no single interactive environment lets an operational
oceanographer bring them together.

Model output — temperature, salinity, current vectors, chlorophyll — arrives as three-dimensional
fields spanning multiple depth levels, spatial grids and time steps. Observations arrive as
profiles along a float's track: irregular in space, irregular in time, unequal in depth. Correlating
one against the other is the daily work of validating a forecast, and today it requires moving
between disconnected tools.

## Identified Gaps

| # | Gap | Consequence |
|---|---|---|
| 1 | No browser-native 3D rendering of ocean model fields with depth-resolved volume views | Desktop-bound tools, platform dependence, no shared access |
| 2 | No unified view of Argo float and glider profiles alongside model fields | Forecaster toggles between packages to correlate prediction with evidence |
| 3 | No interactive controls for variable selection, depth navigation, time animation, custom colorbars | Slow exploration; fixed views that do not answer ad-hoc operational questions |
| 4 | No modular path for additional data sources or variables | Every new instrument or model requires re-engineering |
| 5 | No tooling for rapid intuition about complex 3D ocean phenomena | Delays hazard assessment, search-and-rescue support, fishery advisories, climate monitoring |

## What This Project Does Not Claim

INCOIS is not lacking in visualization or validation capability — it runs mature operational
systems. The contribution here is the **integrated, interactive, browser-native 3D workflow**
the problem statement asks for: one environment where a model field and an instrument profile can
be seen, matched and questioned together, with the provenance and quality of every value exposed
rather than hidden.
