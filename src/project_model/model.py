from __future__ import annotations
from dataclasses import dataclass, field, replace
from random import Random
from typing import Literal
from mesa.experimental.scenarios import Scenario

import mesa
from agent import ModeratorAgent, VideoAgent

Condition = Literal["reference", "baseline", "alternative"]
CONDITIONS: tuple[Condition, ...] = ("reference", "baseline", "alternative")


@dataclass
class VisibilityScenario(Scenario):
    """Synthetic assumptions. The defaults unless changed by Solara"""

    n_videos: int = 40
    n_days: int = 7
    slots_per_day: int = 60
    removal_day: int = 2 # for simplicity, all removals occur on the same day
    boost_multiplier: float = 2.5  
    
    category_weights: dict[str, float] = field(
        default_factory=lambda: {"Category A": 1.0, "Category B": 2.0, "Category C": 1.5} 
    ) # prob of being chosen for presentation
    category_removal_risk: dict[str, float] = field(
        default_factory=lambda: {"Category A": 0.10, "Category B": 0.30, "Category C": 0.20} 
    ) # prob of moderator removing
    category_removal_duration: dict[str, int] = field(
        default_factory=lambda: {"Category A": 1, "Category B": 3, "Category C": 2}
    ) # period removed for (if applicable)

class VisibilityModel(mesa.Model):
    """Run one condition of the model
      * reference: no removal
      * baseline: removal and reinstatement, with no boost
      * alternative: same removal/reinstatement, with a boost_multiplier for reinstated videos
    """

    def __init__(
        self,
        condition: Condition = "baseline",
        seed: int | None = 42,
        scenario: VisibilityScenario | None = None,
        removal_schedule: dict[str, tuple[int, int]] | None = None,
        n_videos: int | None = None,
        n_days: int | None = None,
        boost_multiplier: float | None = None,
        slots_per_day: int | None = None,
    ):
        super().__init__(seed=seed)
        if condition not in CONDITIONS:
            raise ValueError(f"Unknown condition: {condition}")
        self.condition = condition or "baseline"
        self.run_seed = seed or 42
        
        # Solara changes override these variables...
        changes = {}
        if n_videos is not None:
            changes["n_videos"] = n_videos
        if n_days is not None:
            changes["n_days"] = n_days
        if boost_multiplier is not None:
            changes["boost_multiplier"] = boost_multiplier
        if slots_per_day is not None:
            changes["slots_per_day"] = slots_per_day
        self.scenario = replace(scenario or VisibilityScenario(), **changes)
        self.day = 0

        # Create video agents, assign catgeories, save in a dict (key=video_id)
        categories = list(self.scenario.category_weights)
        self.videos: dict[str, VideoAgent] = {}
        for i in range(self.scenario.n_videos):
            video_id = f"V{i + 1:02d}"
            category = categories[i % len(categories)]
            self.videos[video_id] = VideoAgent(
                self, video_id, category, self.scenario.category_weights[category]
            )

        # Create moderator agent, generate removal schedule 
        self.moderator = ModeratorAgent(self)
        if removal_schedule is None:
            self.removal_schedule = self.moderator.choose_removals(self.videos, Random(seed))
        else:
            self.removal_schedule = dict(removal_schedule)
        for video_id, (day, duration) in self.removal_schedule.items():
            if video_id not in self.videos or not 1 <= day <= self.scenario.n_days or duration < 1:
                raise ValueError(f"Invalid removal plan for {video_id}")
            self.videos[video_id].plan_removal(day, duration)

        # Store the data 
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "day": "day",
                "presentation_slots": "presentation_slots",
                "removed_today": "removed_today_count",
                "reinstated_today": "reinstated_today_count",
            }
        )

    @property
    def presentation_slots(self) -> int:
        return sum(
            self.videos[video_id].daily_presentations 
            for video_id in self.removal_schedule
        )

    @property
    def removed_today_count(self) -> int:
        return sum(video.removed_today for video in self.videos.values())

    @property
    def reinstated_today_count(self) -> int:
        return sum(video.reinstated_today for video in self.videos.values())

    def _update_video_availability(self):
        """Apply the moderator's planned removals and reinstatements."""
        if self.condition == "reference":
            return
        
        for video in self.videos.values():
            if video.removal_day == self.day:
                video.remove()
            elif video.reinstatement_day == self.day:
                video.reinstate()

    def _selection_multiplier(self, video: VideoAgent) -> float:
        if (
            self.condition != "alternative"
            or not video.available
            or video.reinstatement_day is None
            or not (video.reinstatement_day <= self.day < video.boost_expiry_day)
        ):
            return 1.0
        
        return self.scenario.boost_multiplier

    def _get_daily_selection_weights(self, available_videos: list[VideoAgent]) -> list[float]:
        return [v.base_selection_weight * self._selection_multiplier(v) for v in available_videos]

    def step(self):
        """Advance the simulation by one day and collect data"""
        if not self.running:
            return
        
        self.day += 1
        for video in self.videos.values():
            video.reset_daily_count()
        
        # Perform necessary events before the presentation slots are filled
        self._update_video_availability()
        available_videos = [video for video in self.videos.values() if video.available]
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

    def run_model(self):
        """Run the model - all simulation days"""
        while self.day < self.scenario.n_days:
            self.step()
