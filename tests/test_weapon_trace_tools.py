"""Evidence integrity checks; no game or mod installation is required."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from capture_weapon_trace import parse_runs, select_run, pose
from analyze_native_flights import analyze

HEADER = 'Stratagem and C4 Trajectory 1.1.1-test.15, loader 1.4.1, api 3\n'
SHOT = 'weapon direction 1 shot t=5 world=4 kind=9f80d67a12a7e40f hand=20 root-height=0.3\n'
POSE = 'dt=-0.02 muzzle=1 2 3 root=0 1 2 forward=1 0 0 camera=0 0 0 camera-forward=0 1 0'


class TraceIntegrity(unittest.TestCase):
    def test_repeated_shot_numbers_in_different_runs_are_not_merged(self):
        runs = parse_runs(HEADER + SHOT + 'weapon direction 1 root-forward 1 0 0\n' +
                         HEADER + SHOT + 'weapon direction 1 root-forward 0 1 0\n')
        self.assertEqual(len(runs), 2)
        self.assertEqual(select_run(runs)['shots']['1']['vectors']['root-forward'], [0., 1., 0.])

    def test_requested_build_and_newest_empty_run_do_not_fall_back(self):
        runs = parse_runs(HEADER + SHOT)
        with self.assertRaises(ValueError):
            select_run(runs, '1.1.1-test.16')
        with self.assertRaises(ValueError):
            select_run(parse_runs(HEADER + SHOT + HEADER))

    def test_pre_click_pose_is_preserved_separately_from_recoil(self):
        text = HEADER + SHOT + 'weapon direction 1 pre-shot ' + POSE + '\n'
        text += 'weapon direction 1 sync ' + POSE.replace('dt=-0.02', 'dt=0.04') + '\n'
        row = select_run(parse_runs(text))['shots']['1']
        self.assertEqual(row['pre_shot'][0]['dt'], -.02)
        self.assertEqual(row['sync'][0]['dt'], .04)
        self.assertEqual(row['pre_shot'][0]['camera-forward'], [0., 1., 0.])

    def test_incomplete_or_nonfinite_pose_is_rejected(self):
        with self.assertRaises(ValueError):
            pose(POSE.split(' camera-forward=')[0])
        with self.assertRaises(ValueError):
            pose(POSE.replace('muzzle=1 2 3', 'muzzle=nan 2 3'))

    def test_duplicate_shot_header_is_not_silently_overwritten(self):
        with self.assertRaises(ValueError):
            parse_runs(HEADER + SHOT + SHOT)

    def test_all_candidate_series_and_sample_completion_are_preserved(self):
        text = HEADER + SHOT
        for n in (1, 2):
            text += f'weapon direction 1 candidate {n} kind=4fd8795ed60f5579; association unverified\n'
            text += f'weapon direction 1 track={n} dt=0.03 position={n} 2 3\n'
        text += 'weapon direction 1 sample-end candidates=2 discovery-scans=4\n'
        row = select_run(parse_runs(text))['shots']['1']
        self.assertEqual(set(row['tracks']), {'1', '2'})
        self.assertEqual(row['tracks']['2'], [[.03, 2., 2., 3.]])
        self.assertIn('sample_end', row)

    def test_saved_native_flight_still_exposes_bad_prone_correction(self):
        rows = {r['shot']: r for r in analyze()}
        self.assertEqual(rows['3']['samples'], 9)
        self.assertEqual(rows['4']['samples'], 4)
        self.assertLess(abs(rows['4']['root_yaw_error_deg']), .03)
        self.assertGreater(abs(rows['4']['displayed_yaw_error_deg']), .6)
        self.assertFalse(rows['1']['stationary_click'])
        self.assertTrue(rows['4']['stationary_click'])
        self.assertTrue(rows['4']['pose_comparisons'])


if __name__ == '__main__':
    unittest.main()
