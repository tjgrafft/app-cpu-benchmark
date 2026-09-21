import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import benchmark

class BenchmarkTests(unittest.TestCase):
    def test_brainlife_edited_numeric_fields(self):
        config = benchmark.validate({'tasks': '256', 'iterations': '250000', 'repeats': '3',
                                     'memory_mb_per_worker': '16', 'seed': '42'})
        self.assertEqual(config['tasks'], 256)
        self.assertEqual(config['iterations'], 250000)
        self.assertTrue(all(type(config[k]) is int for k in config if k != 'workers'))
        self.assertEqual(benchmark.integer(' 256.0 ', 'tasks', 1, 2048), 256)
        for value in ['', 'abc', '1.5', 'NaN', 'Infinity', '-1', '2049', True, None, [], float('inf')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                benchmark.integer(value, 'tasks', 1, 2048)

    def test_invalid_requests(self):
        for config in [{'workers':'2,4'}, {'workers':'1,0'}, {'workers':'1,2','tasks':1}, {'repeats':True}, {'iterations':1000.5}, {'workers':'1,x'}, {'tasks':2048,'iterations':2000000}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                benchmark.validate(config)

    def test_end_to_end_parallel_determinism_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp)
            config={'workers':'1,2','tasks':'4','iterations':'1000','repeats':'2','memory_mb_per_worker':'1','seed':'17'}
            (p/'config.json').write_text(json.dumps(config))
            subprocess.run([sys.executable,str(ROOT/'benchmark.py')],cwd=p,check=True,capture_output=True,text=True)
            data=json.loads((p/'report/results.json').read_text())
            self.assertTrue(data['consistent'])
            self.assertEqual(len(data['trials']),4)
            self.assertEqual(len({t['checksum'] for t in data['trials']}),1)
            self.assertEqual(data['summary'][0]['speedup'],1)
            self.assertTrue(all(t['kernel_cpu_seconds']>0 and t['wall_seconds']>0 for t in data['trials']))
            self.assertIn('Result consistency:',(p/'report/index.html').read_text())
            self.assertTrue((p/'report/html').is_dir())
            self.assertEqual(len((p/'report/trials.csv').read_text().splitlines()),5)

if __name__=='__main__':
    unittest.main()
