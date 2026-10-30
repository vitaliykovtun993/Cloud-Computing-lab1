# -*- coding: utf-8 -*-
"""Тести KMP і розбиття на шматки. Запуск: python -m unittest -v test_kmp"""
from __future__ import print_function

import random
import unittest

from kmp import prefix_function, kmp_search, kmp_count
from chunking import split_with_overlap, parallel_search_simulated


def naive_search(text, pattern):
    result = []
    pos = text.find(pattern)
    while pos != -1:
        result.append(pos)
        # +1, а не +len(pattern): потрібні й перекривні входження
        pos = text.find(pattern, pos + 1)
    return result


def random_string(rng, alphabet, n):
    return "".join(rng.choice(alphabet) for _ in range(n))


class PrefixFunctionTest(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(prefix_function("abacaba"), [0, 0, 1, 0, 1, 2, 3])
        self.assertEqual(prefix_function("aaaa"), [0, 1, 2, 3])
        self.assertEqual(prefix_function("abcd"), [0, 0, 0, 0])
        self.assertEqual(prefix_function("aabaaab"), [0, 1, 0, 1, 2, 2, 3])
        self.assertEqual(prefix_function("a"), [0])
        self.assertEqual(prefix_function(""), [])


class KmpSearchTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(kmp_search("hello world", "o"), [4, 7])
        self.assertEqual(kmp_search("GATTACAGATTACA", "TACA"), [3, 10])
        self.assertEqual(kmp_search("abc", "d"), [])

    def test_overlapping(self):
        self.assertEqual(kmp_search("aaaa", "aa"), [0, 1, 2])
        self.assertEqual(kmp_search("abababa", "aba"), [0, 2, 4])
        self.assertEqual(kmp_search("aabaabaab", "aabaab"), [0, 3])

    def test_edge_cases(self):
        self.assertEqual(kmp_search("", "a"), [])
        self.assertEqual(kmp_search("ab", "abc"), [])
        self.assertEqual(kmp_search("abc", "abc"), [0])
        self.assertEqual(kmp_search("a", "a"), [0])

    def test_empty_pattern_raises(self):
        self.assertRaises(ValueError, kmp_search, "abc", "")
        self.assertRaises(ValueError, kmp_count, "abc", "")

    def test_random_against_naive(self):
        rng = random.Random(1)
        # малі алфавіти дають багато часткових збігів — саме там KMP легко зламати
        for alphabet in ("ab", "abc", "ACGT"):
            for _ in range(300):
                text = random_string(rng, alphabet, rng.randint(0, 80))
                pattern = random_string(rng, alphabet, rng.randint(1, 6))
                self.assertEqual(kmp_search(text, pattern), naive_search(text, pattern),
                                 "text=%r pattern=%r" % (text, pattern))

    def test_count_matches_search(self):
        rng = random.Random(2)
        for _ in range(300):
            text = random_string(rng, "ab", rng.randint(0, 80))
            pattern = random_string(rng, "ab", rng.randint(1, 5))
            self.assertEqual(kmp_count(text, pattern), len(kmp_search(text, pattern)),
                             "text=%r pattern=%r" % (text, pattern))


class SplitWithOverlapTest(unittest.TestCase):
    def check_split(self, text_len, pattern_len, num_chunks):
        chunks = split_with_overlap(text_len, pattern_len, num_chunks)
        msg = "n=%d m=%d k=%d chunks=%r" % (text_len, pattern_len, num_chunks, chunks)
        self.assertEqual(len(chunks), min(num_chunks, text_len), msg)
        expected_start = 0
        for start, end, own_end in chunks:
            # власні частини йдуть впритул, без проміжків і накладань
            self.assertEqual(start, expected_start, msg)
            self.assertTrue(start < own_end <= end <= text_len, msg)
            self.assertEqual(end, min(own_end + pattern_len - 1, text_len), msg)
            expected_start = own_end
        self.assertEqual(expected_start, text_len, msg)
        if chunks:
            sizes = [own_end - start for start, _, own_end in chunks]
            self.assertTrue(max(sizes) - min(sizes) <= 1, msg)

    def test_many_combinations(self):
        for text_len in range(0, 40):
            for pattern_len in range(1, 8):
                for num_chunks in range(1, 12):
                    self.check_split(text_len, pattern_len, num_chunks)

    def test_example(self):
        self.assertEqual(split_with_overlap(10, 3, 3), [(0, 6, 4), (4, 9, 7), (7, 10, 10)])

    def test_more_chunks_than_chars(self):
        self.assertEqual(split_with_overlap(3, 1, 10), [(0, 1, 1), (1, 2, 2), (2, 3, 3)])

    def test_empty_text(self):
        self.assertEqual(split_with_overlap(0, 3, 4), [])

    def test_invalid_args(self):
        self.assertRaises(ValueError, split_with_overlap, 10, 0, 2)
        self.assertRaises(ValueError, split_with_overlap, 10, 3, 0)


class ParallelSimulatedTest(unittest.TestCase):
    def assert_same_as_sequential(self, text, pattern, chunk_range=range(1, 11)):
        expected = kmp_search(text, pattern)
        for num_chunks in chunk_range:
            self.assertEqual(parallel_search_simulated(text, pattern, num_chunks), expected,
                             "text=%r pattern=%r chunks=%d" % (text, pattern, num_chunks))

    def test_random_against_sequential(self):
        rng = random.Random(3)
        for alphabet in ("ab", "ACGT"):
            for _ in range(200):
                text = random_string(rng, alphabet, rng.randint(0, 60))
                pattern = random_string(rng, alphabet, rng.randint(1, 8))
                self.assert_same_as_sequential(text, pattern)

    def test_dense_overlapping(self):
        # кожна позиція — входження, і кожне друге перетинає якусь межу
        self.assert_same_as_sequential("a" * 50, "a")
        self.assert_same_as_sequential("a" * 50, "aa")
        self.assert_same_as_sequential("a" * 50, "aaaaa")
        self.assert_same_as_sequential("ab" * 25, "abab")

    def test_chunks_shorter_than_pattern(self):
        # власна частина (2 символи) коротша за зразок: перекриття сягає кількох сусідніх шматків
        self.assert_same_as_sequential("a" * 20, "a" * 7, range(1, 21))
        self.assert_same_as_sequential("ab" * 10, "ababab", range(1, 21))

    def test_edge_cases(self):
        self.assert_same_as_sequential("", "abc")
        self.assert_same_as_sequential("ab", "abc")
        self.assert_same_as_sequential("abc", "abc")
        self.assert_same_as_sequential("abcabc", "c")
        self.assertEqual(parallel_search_simulated("abc", "abc", 10), [0])
        self.assertEqual(parallel_search_simulated("aaa", "a", 100), [0, 1, 2])

    def test_occurrence_on_chunk_boundary(self):
        pattern = "GATTACA"
        m = len(pattern)
        n = 100
        for num_chunks in range(2, 11):
            chunks = split_with_overlap(n, m, num_chunks)
            for _, _, boundary in chunks[:-1]:
                # d = 1..m-1 — входження перетинає межу; d = 0 — починається рівно на межі
                # (належить правому шматку); d = m — повністю в лівому шматку
                for d in range(0, m + 1):
                    pos = boundary - d
                    # заповнювач 'T' не утворює зайвих входжень GATTACA
                    text = "T" * pos + pattern + "T" * (n - pos - m)
                    self.assertEqual(parallel_search_simulated(text, pattern, num_chunks), [pos],
                                     "chunks=%d boundary=%d d=%d" % (num_chunks, boundary, d))

    def test_overlapping_occurrences_on_boundary(self):
        # "ATATATA" містить "ATATA" на позиціях p і p+2: одне входження може
        # дістатися лівому шматку, друге правому — жодне не має загубитись чи задвоїтись
        pattern = "ATATA"
        block = "ATATATA"
        n = 100
        for num_chunks in range(2, 11):
            chunks = split_with_overlap(n, len(pattern), num_chunks)
            for _, _, boundary in chunks[:-1]:
                for d in range(0, len(block) + 1):
                    pos = boundary - d
                    text = "C" * pos + block + "C" * (n - pos - len(block))
                    self.assertEqual(parallel_search_simulated(text, pattern, num_chunks),
                                     [pos, pos + 2],
                                     "chunks=%d boundary=%d d=%d" % (num_chunks, boundary, d))

    def test_no_match_starts_in_overlap(self):
        # підтверджує коментар у chunking.py: при перекритті m-1 фільтр за own_end
        # нічого не відкидає, бо входження з зони перекриття не вміщується в шматок
        rng = random.Random(4)
        for _ in range(200):
            text = random_string(rng, "ab", rng.randint(1, 60))
            pattern = random_string(rng, "ab", rng.randint(1, 6))
            for num_chunks in range(1, 11):
                for start, end, own_end in split_with_overlap(len(text), len(pattern), num_chunks):
                    for local_pos in kmp_search(text[start:end], pattern):
                        self.assertTrue(start + local_pos < own_end)


if __name__ == "__main__":
    unittest.main()
