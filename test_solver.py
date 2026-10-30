# -*- coding: utf-8 -*-
"""Тести solver_kmp.py. Запуск: python -m unittest -v test_solver"""
from __future__ import print_function

import os
import random
import shutil
import tempfile
import unittest

from kmp import prefix_function, kmp_search
from chunking import split_with_overlap
from solver_kmp import Solver
from run_solver_local import FakeWorker


def random_string(rng, alphabet, n):
    return "".join(rng.choice(alphabet) for _ in range(n))


class CopiesMatchOriginalsTest(unittest.TestCase):
    # solver_kmp.py містить копії функцій — перевіряємо, що вони не розійшлися з оригіналами

    def test_prefix_function(self):
        rng = random.Random(10)
        for _ in range(200):
            p = random_string(rng, "ab", rng.randint(0, 12))
            self.assertEqual(Solver.prefix_function(p), prefix_function(p))

    def test_iter_matches(self):
        rng = random.Random(11)
        for _ in range(300):
            t = random_string(rng, "ab", rng.randint(0, 60))
            p = random_string(rng, "ab", rng.randint(1, 6))
            self.assertEqual(list(Solver.iter_matches(t, p)), kmp_search(t, p))

    def test_split_with_overlap(self):
        for n in range(0, 30):
            for m in range(1, 6):
                for k in range(1, 12):
                    self.assertEqual(Solver.split_with_overlap(n, m, k), split_with_overlap(n, m, k))


class SolveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.input = os.path.join(self.tmp, "input.txt")
        self.output = os.path.join(self.tmp, "output.txt")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_solver(self, pattern, text, num_workers):
        with open(self.input, "w") as f:
            f.write(pattern + "\n" + text + "\n")
        Solver([FakeWorker() for _ in range(num_workers)], self.input, self.output).solve()
        result = {}
        with open(self.output) as f:
            for line in f:
                if not line.startswith("chunk "):
                    key, value = line.split()
                    result[key] = value
        return result

    def test_matches_sequential(self):
        rng = random.Random(12)
        for _ in range(60):
            text = random_string(rng, "ACGT", rng.randint(0, 200))
            pattern = random_string(rng, "ACGT", rng.randint(1, 4))
            expected = len(kmp_search(text, pattern))
            for workers in (1, 2, 3, 5, 8):
                out = self.run_solver(pattern, text, workers)
                self.assertEqual(int(out["matches"]), expected,
                                 "text=%r pattern=%r workers=%d" % (text, pattern, workers))

    def test_output_fields(self):
        out = self.run_solver("aa", "aaaa", 2)
        self.assertEqual(out["matches"], "3")
        self.assertEqual(out["text_len"], "4")
        self.assertEqual(out["workers"], "2")
        for key in ("read_time_s", "parallel_time_s", "total_time_s", "max_worker_search_s"):
            self.assertTrue(float(out[key]) >= 0)

    def test_more_workers_than_chars(self):
        out = self.run_solver("a", "aaa", 10)
        self.assertEqual(out["matches"], "3")
        self.assertEqual(out["chunks"], "3")

    def test_empty_text(self):
        out = self.run_solver("abc", "", 3)
        self.assertEqual(out["matches"], "0")

    def test_windows_line_endings(self):
        with open(self.input, "wb") as f:
            f.write(b"aba\r\nabababa\r\n")
        Solver([FakeWorker()], self.input, self.output).solve()
        with open(self.output) as f:
            self.assertEqual(f.readline(), "matches 3\n")


if __name__ == "__main__":
    unittest.main()
