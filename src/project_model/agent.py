"""Video agents for the visibility-restoration model."""

from __future__ import annotations
import mesa

class VideoAgent(mesa.Agent):
    """One synthetic video and its state in the simulation."""

    def __init__(
        self,
        model: "VisibilityModel",
        video_id: str,
        category: str,
        base_selection_weight: float,
    ):
        super().__init__(model)
        self.video_id = video_id
        self.category = category
        self.base_selection_weight = float(base_selection_weight)
        self.available = True
        self.daily_presentations = 0

    def remove(self) -> None:
        """Make this video unavailable for presentation."""
        self.available = False

    def reinstate(self) -> None:
        """Make this video available for presentation again."""
        self.available = True

    def reset_daily_count(self) -> None:
        self.daily_presentations = 0

    def record_presentation(self) -> None:
        self.daily_presentations += 1
