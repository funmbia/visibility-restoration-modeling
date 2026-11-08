from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

import mesa
from agent import VideoAgent

Condition = Literal["reference", "baseline", "alternative"]
CONDITIONS: tuple[Condition, ...] = ("reference", "baseline", "alternative")

@dataclass
class VisibilityScenario:
    """Define parameters for the del02 slice"""

    n_videos: int = 10
    n_days: int = 5
    slots_per_day: int = 20
    category_a_count: int = 5
    category_weights: dict[str, float] = field(
        default_factory=lambda: {"Category A": 1.0, "Category B": 2.0}
    )
    removed_video_ids: tuple[str, ...] = ("V01", "V02", "V06") # V06 in Category B
    removal_day: int = 2
    reinstatement_day: int = 4
    boost_duration_days: int = 2
    boost_multiplier: float = 2.0

    # Error indicators --- take out later
    def __post_init__(self) -> None:
        if min(self.n_videos, self.n_days, self.slots_per_day) < 1:
            raise ValueError("Video, day, and slot counts must be positive")
        if not 0 <= self.category_a_count <= self.n_videos:
            raise ValueError("category_a_count must be between 0 and n_videos")
        if set(self.category_weights) != {"Category A", "Category B"}:
            raise ValueError("Provide weights for Category A and Category B")
        if any(weight <= 0 for weight in self.category_weights.values()):
            raise ValueError("Category weights must be positive")
        if not self.removed_video_ids or len(set(self.removed_video_ids)) != len(self.removed_video_ids):
            raise ValueError("removed_video_ids must be non-empty and unique")
        if not 1 <= self.removal_day < self.reinstatement_day <= self.n_days:
            raise ValueError("Days must satisfy 1 <= removal < reinstatement <= n_days")
        if self.boost_duration_days < 1 or self.boost_multiplier < 1:
            raise ValueError("Boost duration must be positive and multiplier must be >= 1")


class VisibilityModel(mesa.Model):
    """Run one condition of the model
      * reference: no removal
      * baseline: removal and reinstatement, with no boost
      * alternative: same removal/reinstatement, with a boost_multiplier multiplier for reinstated videos
      For del02 slice, 2x on Days 4 and 5
    """

    def __init__(
        self,
        condition: Condition = "baseline",
        seed: int | None = 42,
        scenario: VisibilityScenario | None = None,
    ):
        super().__init__(seed=seed)
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition: {condition}")

        self.condition = condition
        self.scenario = scenario or VisibilityScenario()
        self.day = 0
        video_ids = [f"V{i:02d}" for i in range(1, self.scenario.n_videos + 1)]
        unknown_ids = set(self.scenario.removed_video_ids) - set(video_ids)
        if unknown_ids:
            raise ValueError(f"Unknown removed video IDs: {sorted(unknown_ids)}")

        # Create video agents, assign catgeories, save in a dict (key=video_id)
        self.videos: dict[str, VideoAgent] = {}
        for index, video_id in enumerate(video_ids):
            category = (
                "Category A"
                if index < self.scenario.category_a_count
                else "Category B"
            )
            self.videos[video_id] = VideoAgent(
                self, video_id, category, self.scenario.category_weights[category]
            )

        # Collect data about the 3 videos scheduled for removal ("affected videos")
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "day": "day",
                "total_presentation_slots": "total_presentation_slots",
            }
        )

    @property
    def total_presentation_slots(self) -> int:
        return sum(
            self.videos[video_id].daily_presentations
            for video_id in self.scenario.removed_video_ids
        )

    def _update_video_availability(self) -> None:
        """Apply the fixed removal and reinstatement schedule for this day, if appl"""
        
        if self.condition == "reference":
            return

        if self.day == self.scenario.removal_day:
            for video_id in self.scenario.removed_video_ids:
                self.videos[video_id].remove()
        elif self.day == self.scenario.reinstatement_day:
            for video_id in self.scenario.removed_video_ids:
                self.videos[video_id].reinstate()


    def _get_daily_selection_weights(self, available_videos: list[VideoAgent]) -> list[float]:
        """Return video weights in the same order as available_videos."""
        
        boost_active = (
            self.condition == "alternative"
            and self.scenario.reinstatement_day
            <= self.day
            < self.scenario.reinstatement_day + self.scenario.boost_duration_days
        )

        return [
            video.base_selection_weight
            * (
                self.scenario.boost_multiplier
                if boost_active and video.video_id in self.scenario.removed_video_ids
                else 1.0
            )
            for video in available_videos
        ]

    def step(self) -> None:
        """Advance the simulation by one day and collect data"""
        # if self.day >= self.scenario.n_days:
        #     self.running = False
        #     return

        self.day += 1
        for video in self.videos.values():
            video.reset_daily_count()

        # Perform necessary events before the presentation slots are filled
        self._update_video_availability()
        available_videos = [v for v in self.videos.values() if v.available]
        if not available_videos:
            raise RuntimeError("No videos are available for presentation")

        # --- Presentation-selection-rule
        # Select one available video for each slot using weighted random selection. 
        # A video can be selected more than once per day.
        weights = self._get_daily_selection_weights(available_videos)
        for _ in range(self.scenario.slots_per_day):
            selected = self.random.choices(available_videos, weights=weights, k=1)[0]
            selected.record_presentation()

        self.datacollector.collect(self)

        if self.day >= self.scenario.n_days:
            self.running = False

    def run_model(self) -> None:
        """Run the model - all simulation days"""
        while self.day < self.scenario.n_days:
            self.step()
