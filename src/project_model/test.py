"""Tests for the DEL02 slice to ensure it behaves as expected."""

import tempfile
import unittest
from pathlib import Path

from collect_data import save_outputs
from model import CONDITIONS, VisibilityModel, VisibilityScenario


class VisibilityModelTests(unittest.TestCase):
    def test_removal_and_reinstatement_schedule(self):
        model = VisibilityModel(condition="baseline", seed=7)
        model.step()  # Day 1
        self.assertEqual(sum(v.available for v in model.videos.values()), 10)
        model.step()  # Day 2: three videos removed before the slots
        self.assertEqual(sum(v.available for v in model.videos.values()), 7)
        self.assertEqual(model.total_presentation_slots, 0)
        model.step()  # Day 3
        self.assertEqual(sum(v.available for v in model.videos.values()), 7)
        model.step()  # Day 4: all three reinstated before the slots
        self.assertEqual(sum(v.available for v in model.videos.values()), 10)

    def test_each_day_has_twenty_selections(self):
        model = VisibilityModel(condition="baseline", seed=8)
        model.step()
        self.assertEqual(sum(v.daily_presentations for v in model.videos.values()), 20)

    def test_reference_never_removes_target_videos(self):
        model = VisibilityModel(condition="reference", seed=9)
        model.step()
        model.step()
        self.assertTrue(all(v.available for v in model.videos.values()))

    def test_alternative_doubles_target_weights_after_reinstatement(self):
        model = VisibilityModel(condition="alternative", seed=10)
        for _ in range(4):
            model.step()
        available = [v for v in model.videos.values() if v.available]
        weights = model._get_daily_selection_weights(available)
        weight_by_id = {v.video_id: weight for v, weight in zip(available, weights)}
        for video_id in model.scenario.removed_video_ids:
            video = model.videos[video_id]
            self.assertEqual(weight_by_id[video_id], video.base_selection_weight * 2)

    def test_baseline_keeps_original_target_weights(self):
        model = VisibilityModel(condition="baseline", seed=11)
        for _ in range(4):
            model.step()
        available = [v for v in model.videos.values() if v.available]
        weights = model._get_daily_selection_weights(available)
        weight_by_id = {v.video_id: weight for v, weight in zip(available, weights)}
        for video_id in model.scenario.removed_video_ids:
            self.assertEqual(
                weight_by_id[video_id], model.videos[video_id].base_selection_weight
            )

    def test_collector_records_only_day_and_target_total(self):
        model = VisibilityModel(condition="baseline", seed=12)
        model.run_model()
        frame = model.datacollector.get_model_vars_dataframe()
        self.assertEqual(list(frame.columns), ["day", "total_presentation_slots"])
        self.assertEqual(len(frame), 5)
        self.assertEqual(frame.loc[1, "total_presentation_slots"], 0)
        self.assertEqual(frame.loc[2, "total_presentation_slots"], 0)

    def test_output_files_use_both_naming_for_shared_comparisons(self):
        scenario = VisibilityScenario()
        rows = []
        for condition in CONDITIONS:
            model = VisibilityModel(condition, seed=20, scenario=scenario)
            model.run_model()
            for record in model.datacollector.get_model_vars_dataframe().to_dict("records"):
                rows.append({
                    "replication": 1,
                    "seed": 20,
                    "condition": condition,
                    "day": int(record["day"]),
                    "total_presentation_slots": int(record["total_presentation_slots"]),
                })

        with tempfile.TemporaryDirectory() as temp_dir:
            save_outputs(rows, scenario, 1, temp_dir)
            td = Path(temp_dir)
            self.assertTrue((td / "reference_raw_00_daily_presentation_slots.csv").exists())
            self.assertTrue((td / "baseline_raw_00_daily_presentation_slots.csv").exists())
            self.assertTrue((td / "alternative_raw_00_daily_presentation_slots.csv").exists())
            self.assertTrue((td / "BOTH_processed_02_summary_list.csv").exists())


if __name__ == "__main__":
    unittest.main()
