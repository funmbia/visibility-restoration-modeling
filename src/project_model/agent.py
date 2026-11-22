"""Defines video and moderator agents."""

from __future__ import annotations
import mesa


class VideoAgent(mesa.Agent):
    """One synthetic video and its state in the simulation."""

    def __init__(
            self, 
            model, 
            video_id: str, 
            category: str, 
            base_selection_weight: float
        ):
        super().__init__(model)
        self.video_id = video_id
        self.category = category
        self.base_selection_weight = float(base_selection_weight)
        self.available = True
        self.daily_presentations = 0
        self.cumulative_presentations = 0

        self.removal_day: int | None = None
        self.removal_duration = 0
        self.reinstatement_day: int | None = None
        self.boost_expiry_day: int | None = None  # Exclusive end day
        self.removed_today = False
        self.reinstated_today = False

    def plan_removal(self, day: int, duration: int):
        self.removal_day = day
        self.removal_duration = duration
        self.reinstatement_day = day + duration
        self.boost_expiry_day = self.reinstatement_day + duration

    def remove(self) -> None:
        """Make this video unavailable for presentation."""
        self.available = False
        self.removed_today = True

    def reinstate(self) -> None:
        """Make this video available for presentation again."""
        self.available = True
        self.reinstated_today = True

    def reset_daily_count(self) -> None:
        self.daily_presentations = 0
        self.removed_today = False
        self.reinstated_today = False

    def record_presentation(self) -> None:
        self.daily_presentations += 1
        self.cumulative_presentations += 1


class ModeratorAgent(mesa.Agent):
    """Moderator remove videos randomly according to their category risk & stores in a video removal schedule"""

    def choose_removals(self, videos: dict[str, VideoAgent], rng):
        schedule = {}
        scenario = self.model.scenario
        for video in videos.values():
            risk = scenario.category_removal_risk[video.category]
            if rng.random() < risk:
                duration = scenario.category_removal_duration[video.category]
                schedule[video.video_id] = (scenario.removal_day, duration)
        return schedule
