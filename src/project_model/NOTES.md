## Changes from DEL02 → DEL03

[DEL02_version](https://github.com/funmbia/visibility-restoration-modeling/tree/del02_version)   
[DEL03_version](https://github.com/funmbia/visibility-restoration-modeling/tree/del03_version)


| Component | DEL02 | DEL03 |
|---|---|---|
| **Model scale** | 10 videos, 5 days, 20 presentation slots per day | Default of 40 videos, 7 days, 60 presentation slots per day; adjustable through Solara |
| **Video categories** | Two categories (A and B) | Three categories (A, B, and C), each with distinct selection weights, removal risks, and removal durations |
| **Moderation** | Three videos (V01, V02, V06) were predetermined for removal | A `ModeratorAgent` now randomly selects videos for removal using category-specific risks |
| **Reinstatement** | Removed videos returned on Day 4 | All removed videos have an assigned removal day and duration |
| **Visibility boost** | 2x  | Default 2.5x, adjustable to 2x or 3x in Solara |
| **Experiment setup** | 10 replications and averaged outputs | One interactive simulation run through Mesa's `SolaraViz` |
| **Visualization** | Results inspected mainly through saved CSVs and graphs | Parameters can be adjusted in Solara; Live line and bar graphs are displayed (and also saved locally) |
