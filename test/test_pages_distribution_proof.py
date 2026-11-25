import importlib.util
import pathlib
import unittest
spec = importlib.util.spec_from_file_location('proof', pathlib.Path(__file__).resolve().parents[1] / 'tools/pages_distribution_proof.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)

class ComparisonTest(unittest.TestCase):
    def test_dist_matches(self):
        r = proof.compare(b'base', b'generated', b'generated')
        self.assertFalse(r['source_equals_dist'])
        self.assertTrue(r['public_matches_dist'])
        self.assertFalse(r['public_matches_source'])
    def test_source_matches(self):
        r = proof.compare(b'base', b'generated', b'base')
        self.assertTrue(r['public_matches_source'])
        self.assertFalse(r['public_matches_dist'])
    def test_unavailable(self):
        r = proof.compare(b'base', b'generated', None)
        self.assertIsNone(r['public_matches_dist'])
        self.assertIsNone(r['public_sha256'])
    def test_equal(self):
        r = proof.compare(b'same', b'same', b'same')
        self.assertTrue(r['source_equals_dist'])
        self.assertTrue(r['public_matches_source'])
        self.assertTrue(r['public_matches_dist'])

if __name__ == '__main__':
    unittest.main()
