## Simplifications from the Civil Violence model
The Civil Violence example was used as a starting point for the project structure. The Citizen and Cop agents were replaced with a Video Agent. 

The grid, movement, neighbourhood interactions, and arrests were removed; replaced with relevant functions like video removal, restoration, and weight calculations. 

## Files
The project_model is structured similarly to the Mesa civil_violence folder.
- *app.py* runs the simulation. It delegates the output file creation to *collect_data.py*
- *agent.py* defines ```VideoAgent``` and its relevant attributes and actions
- *model.py* defines the steps for the model e.g. creating video agents, assigning them categories and weights, etc.  
