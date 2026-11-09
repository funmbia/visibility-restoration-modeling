"""Save raw results and plots for DEL02."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
import matplotlib.pyplot as plt

from model import CONDITIONS, VisibilityScenario

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" # default

# --- HELPER FUNCTION ---
def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# --- MAIN FUNCTION ---
def save_outputs(
    daily_rows: list[dict],
    scenario: VisibilityScenario,
    replications: int,
    output_dir: Path | str = OUTPUT_DIR,
) -> dict[str, Path]:
    """
    
        reference condition files: reference_xxx
        baseline condition files: baseline_xxx
        alternative condition files: alternative_xxx
        files that display reference, baseline and alternative: ALL_xxx
    """

    if not daily_rows:
        raise ValueError("daily_rows cannot be empty")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 0. Save all generated raw data
    write_csv(OUTPUT_DIR / "all_data.csv", daily_rows)

    # --- 1. Save the data from each condition: one each for reference, baseline, alternative
    raw_paths = {
        condition: output_dir / f"{condition}_raw_00_daily_presentation_slots.csv"
        for condition in CONDITIONS
    }
    for condition, path in raw_paths.items():
        write_csv(path, [row for row in daily_rows if row["condition"] == condition])


    # --- 2A. Find the avg value for each day per condition
    values_by_day: dict[tuple[str, int], list[int]] = defaultdict(list)
    totals_by_run: dict[tuple[int, str], int] = defaultdict(int)
    for row in daily_rows:
        key = (row["condition"], int(row["day"]))
        value = int(row["total_presentation_slots"])
        values_by_day[key].append(value)
        totals_by_run[(int(row["replication"]), row["condition"])] += value

    daily_avgs: list[dict] = []
    for condition in CONDITIONS:
        for day in range(1, scenario.n_days + 1):
            avg = mean(values_by_day[(condition, day)])
            daily_avgs.append(
                {
                    "condition": condition,
                    "day": day,
                    "avg_presentation_slots": round(avg, 4)
                }
            )
        tmp = condition + "_raw_01_avg_daily_presentation_slots.csv"
        write_csv(output_dir / tmp, [row for row in daily_avgs if row["condition"] == condition])

    # --- 2B. Graph 2A
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for condition in CONDITIONS:
        rows = [row for row in daily_avgs if row["condition"] == condition]
        ax.plot(
            [row["day"] for row in rows],
            [row["avg_presentation_slots"] for row in rows],
            marker="o",
            linewidth=2,
            label=condition.capitalize(),
        )
    ax.set_title("Average Presentation Slots Received by the Affected Videos")
    ax.set_xlabel("Simulated day")
    ax.set_ylabel("Avg Presentation Slots Received")
    ax.set_xticks(range(1, scenario.n_days + 1))
    ax.grid(True, alpha=0.3)
    ax.legend(title="Condition")
    fig.tight_layout()
    daily_plot = output_dir / "ALL_processed_00_daily_presentation_slots.png"
    fig.savefig(daily_plot, dpi=180)
    plt.close(fig)


    # --- 3A. Find the avg value for each condition across all 5 days
    totals_by_condition: dict[str, list[int]] = defaultdict(list)
    for (_, condition), total in totals_by_run.items():
        totals_by_condition[condition].append(total)

    comparison: list[dict] = []
    key = f"avg_presentation_slots_over_{scenario.n_days}_days"
    for condition in CONDITIONS:
        avg= mean(totals_by_condition[condition])
        comparison.append(
            {
                "condition": condition,
                "replications": replications,
                key: round(avg, 4)
            }
        )
    write_csv(output_dir / "ALL_raw_00_combined_presentation_slots.csv", comparison)


    comparison_by_condition = {row["condition"]: row for row in comparison}
    
    # --- 3B. Graph 3A
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ax.bar(
        [condition.capitalize() for condition in CONDITIONS],
        [comparison_by_condition[condition][key] for condition in CONDITIONS],
    )
    ax.set_title("Average Presentation Slots Received over All 5 Days")
    ax.set_ylabel("Avg Presentation Slots Received")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "ALL_processed_01_combined_presentation_slots.png")
    plt.close(fig)

    # 4. Calculate the difference across conditions
    reference = comparison_by_condition["reference"][key]
    baseline = comparison_by_condition["baseline"][key]
    alternative = comparison_by_condition["alternative"][key]
    missed = reference - baseline 
    recovered = alternative - baseline
    
    summary_list = [{
        "reference_avg": round(reference, 4),
        "baseline_avg": round(baseline, 4),
        "alternative_avg": round(alternative, 4),
        "reference_minus_baseline": round(missed, 4),
        "alternative_minus_baseline": round(recovered, 4),
        "recovery_percent": (
            round(100 * recovered / missed, 2) if missed > 0 else "negative recovery, the alternative did not make up for missed presentation slots"
        ),
    }]
    write_csv(output_dir / "ALL_processed_02_summary_list.csv", summary_list)
    