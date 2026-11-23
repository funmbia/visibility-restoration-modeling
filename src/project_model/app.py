"""Run the Solara visualization and save its outputs."""
from __future__ import annotations
import csv
import importlib
from pathlib import Path

import solara
from matplotlib.figure import Figure
from mesa.visualization import Slider, SolaraViz
from mesa.visualization.utils import update_counter

from model import CONDITIONS, VisibilityModel

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# for the video grid
AVAILABLE = "🟡"
REMOVED = "🔴"
BOOSTED = "🟢"

CONDITION_COLORS = { # for the graphs
    "reference": "#626E77",  
    "baseline": "#1f77b4",     
    "alternative": "#7b2ca0", 
}

# --- HELPER FUNCTION ---
def write_csv(path: Path, rows: list[dict]):
    """Save a list of records as a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

@solara.component
def VideoGrid(model: VisibilityModel):
    """Video statuses as grid, updated after every simulation step(day)."""
    update_counter.get()

    with solara.Card("Video Status", style={"width": "100%"}):
        with solara.Column(
            style={"overflow-y": "auto","overflow-x": "hidden", "padding": "6px",}
        ):
            with solara.GridFixed(columns=5):
                for video in model.videos.values():
                    if not video.available:
                        color = REMOVED
                    elif model.condition == "alternative" and model._selection_multiplier(video) > 1:
                        color = BOOSTED
                    else:
                        color = AVAILABLE

                    with solara.Column(
                        style={"align-items": "center", "gap": "1px"}
                    ):
                        solara.Text(color)
                        solara.Text(video.video_id)


@solara.component
def PresentationGraph(model: VisibilityModel):
    """Graph and save the results under all three conditions."""
    update_counter.get()

    with solara.Card("Results", style={"width": "100%"}):
        if model.day == 0:
            solara.Info("Press Step or Play to start the simulation. Graphs will appear here.")
            return

        total_slots = {}

        # 1. Daily presentation slots for videos selected for removal.
        fig = Figure(figsize=(8, 4))
        ax = fig.subplots()

        for condition in CONDITIONS:
            if condition == model.condition:
                comparison = model
            else:
                comparison = VisibilityModel( # Make models for the other conditions to get their results
                    condition=condition,
                    seed=model.run_seed,
                    scenario=model.scenario,
                    removal_schedule=model.removal_schedule,
                )
                for _ in range(model.day):
                    comparison.step()

            records = comparison.datacollector.get_model_vars_dataframe()
            if records.empty:
                total_slots[condition] = 0
                continue

            ax.plot(
                records["day"],
                records["presentation_slots"],
                marker="o",
                linewidth=2,
                color=CONDITION_COLORS[condition],
                label=condition.capitalize(),
            )
            
            records.to_csv(OUTPUT_DIR / f"{condition}_raw_00_daily_presentation_slots.csv", index=False)
            total_slots[condition] = records["presentation_slots"].sum()

        ax.set(
            xlabel="Simulated Day",
            ylabel="Presentation Slots",
            title=f"Daily Presentation Slots Received by the {len(model.removal_schedule)} Videos",
        )
        ax.set_xticks(range(1, model.scenario.n_days + 1))
        ax.set_xlim(1, max(2, model.scenario.n_days))
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.text(0.5,0.01,
            "Assumption: All videos are removed on Day 2 and all removed videos are eventually reinstated",
            ha="center", fontsize=8,
        )
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "ALL_processed_00_daily_presentation_slots.png", dpi=180)

        # 2. Total presentation slots for videos selected for removal.
        fig2 = Figure(figsize=(7.5, 4))
        ax2 = fig2.subplots()
        ax2.bar(
            [c.capitalize() for c in CONDITIONS],
            [total_slots.get(c, 0) for c in CONDITIONS],
            color=[CONDITION_COLORS[c] for c in CONDITIONS],
        )
        ax2.set(
            title=f"Total Presentation Slots Received Over {model.day} Simulated Days",
            ylabel="Presentation Slots",
        )
        ax2.grid(axis="y", alpha=0.3)
        fig2.tight_layout()
        fig2.savefig(OUTPUT_DIR / "ALL_processed_01_total_presentation_slots.png", dpi=180)

        # 3. Save a summary for the displayed run.
        reference, baseline, alternative = (total_slots[c] for c in CONDITIONS)
        missed = reference - baseline
        recovered = alternative - baseline
        gap = reference - alternative

        summary_list = [{
            "n_videos": model.scenario.n_videos,
            "n_days": model.scenario.n_days,
            "slots_per_day": model.scenario.slots_per_day,
            "boost_multiplier": model.scenario.boost_multiplier,
            "videos_removed": len(model.removal_schedule),
            "reference_slots": round(reference, 4),
            "baseline_slots": round(baseline, 4),
            "alternative_slots": round(alternative, 4),
            "reference_minus_baseline": round(missed, 4),
            "alternative_minus_baseline": round(recovered, 4),
            "reference_minus_alternative": round(gap, 4),
            "recovery_percent": round(100 * recovered / missed, 2) if missed > 0 else "N/A",
        }]
        write_csv(OUTPUT_DIR / "ALL_raw_00_summary_list.csv", summary_list)

        # 4. Show the graphs together in their own card
        with solara.Column(style={"overflow-y": "auto"}):
            solara.FigureMatplotlib(fig)
            solara.FigureMatplotlib(fig2)
            solara.Markdown(f"*Recovery Percentage: {round(100 * recovered / missed, 2) if missed > 0 else "0.0"}%*")


@solara.component
def SummaryDashboard(model: VisibilityModel):
    """Page 0 is the intro page with short description & instructions"""
    with solara.Card("About"):
        solara.Markdown(
            """
            This simulation compares the presentation opportunities received by videos under three conditions:

            - **Reference:** No videos are removed.
            - **Baseline:** Selected videos are removed, then reinstated.
            - **Alternative:** Selected videos are removed, then reinstated with a temporary visibility boost.

            **How to run:** Go to **Page 1**. Press **Step** to advance one day or **Play** to run all days.    
            Use **Reset** after changing model parameters in the sidebar.
            """
        )


@solara.component
def LiveDashboard(model: VisibilityModel):
    """Page 1: video statuses on the left, graphs on the right"""
    update_counter.get()
    with solara.Card(f"Day {model.day} of {model.scenario.n_days}"):
        solara.Text("🟡 Available    🔴 Removed    🟢 Boosted")
        solara.Markdown(
            f"""
            The moderator agent randomly removes **{len(model.removal_schedule)}** videos on Day 2.   
            When they are reinstated, they will receive a ***temporary*** visibility boost.    
            Click **Reset** after adjusting the sidebar parameters.
            """
        )

    with solara.ColumnsResponsive(12, medium=[5, 7], style={"width": "100%"}):
        VideoGrid(model)
        PresentationGraph(model)


model_params = {
    "condition": "alternative",  # Display the alternative in the live grid, but run the rest in the bg for the graphs
    "n_videos": Slider("Number of Videos", 40, 10, 50, 10),
    "n_days": Slider("Simulation Days", 7, 5, 10, 1),
    "slots_per_day": Slider("Presentation Slots per day", 60, 20, 100, 20),
    "boost_multiplier": {
        "type": "Select",
        "value": 2.5,
        "values": [2.0, 2.5, 3.0],
        "label": "Boost Multiplier",
    },
}


# Adjust Mesa's default dashboard layout
mesa_solara_viz = importlib.import_module("mesa.visualization.solara_viz")
_original_grid_layout = mesa_solara_viz.make_initial_grid_layout

def full_width_grid_layout(num_components):
    if num_components == 1:
        return [{"i": 0, "w": 12, "h": 30, "moved": False, "x": 0, "y": 0}]
    return _original_grid_layout(num_components)

mesa_solara_viz.make_initial_grid_layout = full_width_grid_layout
page = SolaraViz(
    VisibilityModel(condition="alternative", seed=42),
    components=[(SummaryDashboard, 0), (LiveDashboard, 1)],
    model_params=model_params,
    name="DEL03 - YouTube Visibility Model",
    play_interval=1000,
    render_interval=1,
)
