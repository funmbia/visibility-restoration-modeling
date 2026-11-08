"""Run the DEL02 visibility experiment and save its outputs."""

from __future__ import annotations
from pathlib import Path

from collect_data import save_outputs
from model import CONDITIONS, VisibilityModel, VisibilityScenario

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" # default


# --- RUN THE SIMULATION ---
def run_experiments(
    replications = 10, # aka simulation runs
    seed = 42,
    output_dir: Path | str = OUTPUT_DIR,
):
    """Run the three conditions (reference/baseline/alternative) 
        over 'replications' number of times,
        and save outputs to 'output_dir'
    """
    if replications < 1:
        raise ValueError("replications must be at least 1")

    scenario = VisibilityScenario()
    daily_rows: list[dict] = []

    # Nested FOR LOOP: run the model for the 3 conditions over # replications 
    for replication in range(1, replications + 1):
        run_seed = seed + replication - 1 # diff seed for each replication
        
        for condition in CONDITIONS:
            model = VisibilityModel(condition, seed=run_seed, scenario=scenario)
            model.run_model()

            records = model.datacollector.get_model_vars_dataframe().to_dict("records")
            for record in records:
                row = {
                    "replication": replication,
                    "seed": run_seed,
                    "condition": condition,
                    "day": int(record["day"]),
                    "total_presentation_slots": int(
                        record["total_presentation_slots"]
                    ), # in total, how many slots did the three videos receive that day
                }
                daily_rows.append(row)

    # Delegate to collect_data.py to save outputs
    save_outputs(
        daily_rows, scenario, replications, output_dir
    )
    print("-" * 30)
    print(f"Completed {replications} replications per condition.")
    print(f"Saved results to: {Path(output_dir).resolve()}")


# --- MAIN EXECUTION ---
def main() -> None:
    run_experiments()

if __name__ == "__main__":
    main()
