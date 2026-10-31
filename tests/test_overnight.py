"""Timeouts must kill the worker, save a failure, and continue with the next CV."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import run_overnight


class OvernightTests(unittest.TestCase):
    def test_expired_batch_does_not_start_another_worker(self):
        config = {'repetitions': 1, 'inputs': [{'id': 'CV001'}]}
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(run_overnight, 'PROJECT_ROOT', Path(temporary)), \
                patch.object(run_overnight, 'prepare_config', return_value=config), \
                patch.object(run_overnight, 'capture_environment', return_value={}), \
                patch.object(run_overnight.time, 'monotonic', side_effect=[0, 28801]), \
                patch.object(run_overnight.subprocess, 'Popen') as start:
            run_overnight.run_batch(Path('unused'), 8, 840)
            start.assert_not_called()
            directory = next((Path(temporary) / 'results').iterdir())
            summary = json.loads((directory / 'summary.json').read_text())
            self.assertEqual(summary['attempt_count'], 0)
            self.assertEqual(summary['stop_reason'], 'batch_time_limit')

    def test_timeout_is_checkpointed_and_next_document_runs(self):
        config = {
            'repetitions': 1, 'monitoring': {},
            'inputs': [{'id': 'CV001'}, {'id': 'CV002'}],
            'stages': [{'name': 'structure_cv', 'method': 'vlm_structuring'}],
        }
        processes = [Mock(), Mock()]
        for process in processes:
            process.wait.side_effect = [subprocess.TimeoutExpired('worker', 1), 0]
            process.poll.return_value = None
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(run_overnight, 'PROJECT_ROOT', Path(temporary)), \
                patch.object(run_overnight, 'prepare_config', return_value=config), \
                patch.object(run_overnight, 'capture_environment', return_value={}), \
                patch.object(run_overnight.subprocess, 'Popen', side_effect=processes):
            run_overnight.run_batch(Path('unused'), 8, 1)
            directory = next((Path(temporary) / 'results').iterdir())
            summary = json.loads((directory / 'summary.json').read_text())
            self.assertEqual(summary['attempt_count'], 2)
            self.assertEqual(summary['stop_reason'], 'completed')
            for cv_id, process in zip(('CV001', 'CV002'), processes):
                process.kill.assert_called_once()
                report = json.loads((directory / 'documents' / cv_id / 'repeat_001/report.json').read_text())
                self.assertEqual(report['status'], 'error')
                self.assertEqual(report['stages'][0]['error']['type'], 'TimeoutError')


if __name__ == '__main__':
    unittest.main()
