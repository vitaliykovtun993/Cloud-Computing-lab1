# -*- coding: utf-8 -*-
"""Паралельний пошук підрядка (KMP) для PARCS-Python.

Це єдиний файл, який завантажується в PARCS як Solution File. PARCS надсилає
воркерам лише його, тому KMP і розбиття на шматки скопійовані сюди з kmp.py
і chunking.py, а не імпортуються.

Вхідний файл: перший рядок — зразок, другий — текст (як у data_generator.py).
"""
from __future__ import print_function

import time

try:
    from Pyro4 import expose
except ImportError:
    # локально Pyro4 може не бути — декоратор тоді нічого не робить
    def expose(func):
        return func


class Solver:
    def __init__(self, workers=None, input_file_name=None, output_file_name=None):
        # на воркерах PARCS створює Solver() без аргументів, тому всі параметри необов'язкові
        self.input_file_name = input_file_name
        self.output_file_name = output_file_name
        self.workers = workers

    def solve(self):
        t_start = time.time()
        pattern, text = self.read_input()
        t_read = time.time() - t_start
        n = len(text)
        m = len(pattern)
        print("Job started: text %d, pattern %d, workers %d" % (n, m, len(self.workers)))

        chunks = Solver.split_with_overlap(n, m, len(self.workers))

        # Спочатку роздаємо роботу ВСІМ воркерам і лише потім читаємо .value:
        # виклики асинхронні, а перше ж звернення до .value чекає на результат.
        t_map = time.time()
        futures = []
        for i, (start, end, own_end) in enumerate(chunks):
            futures.append(self.workers[i].mymap(text[start:end], pattern, own_end - start))

        results = [f.value for f in futures]
        t_parallel = time.time() - t_map

        total = sum(r[0] for r in results)
        t_total = time.time() - t_start
        self.write_output(n, m, total, chunks, results, t_read, t_parallel, t_total)
        print("Job finished: %d matches, parallel part %.3f s" % (total, t_parallel))

    @staticmethod
    @expose
    def mymap(chunk, pattern, own_len):
        """Рахує входження, що починаються в перших own_len символах шматка.

        Повертає (кількість, час пошуку на воркері) — список позицій не пересилаємо,
        бо для великих текстів це дорого.
        """
        t0 = time.time()
        count = 0
        for pos in Solver.iter_matches(chunk, pattern):
            # при перекритті m-1 ця умова завжди виконується, лишаємо як страховку від дублікатів
            if pos < own_len:
                count += 1
        return count, time.time() - t0

    # ---- KMP (копія з kmp.py) ----

    @staticmethod
    def prefix_function(pattern):
        m = len(pattern)
        pi = [0] * m
        k = 0
        for i in range(1, m):
            while k > 0 and pattern[i] != pattern[k]:
                k = pi[k - 1]
            if pattern[i] == pattern[k]:
                k += 1
            pi[i] = k
        return pi

    @staticmethod
    def iter_matches(text, pattern):
        if not pattern:
            raise ValueError("pattern must be non-empty")
        pi = Solver.prefix_function(pattern)
        m = len(pattern)
        k = 0
        # enumerate, а не range(len(text)): у Python 2 range створив би величезний список
        for i, c in enumerate(text):
            while k > 0 and c != pattern[k]:
                k = pi[k - 1]
            if c == pattern[k]:
                k += 1
            if k == m:
                yield i - m + 1
                k = pi[k - 1]

    # ---- розбиття (копія з chunking.py) ----

    @staticmethod
    def split_with_overlap(text_len, pattern_len, num_chunks):
        if pattern_len < 1:
            raise ValueError("pattern_len must be >= 1")
        if num_chunks < 1:
            raise ValueError("num_chunks must be >= 1")
        if text_len == 0:
            return []
        num_chunks = min(num_chunks, text_len)
        base, extra = divmod(text_len, num_chunks)
        chunks = []
        start = 0
        for i in range(num_chunks):
            own_end = start + base + (1 if i < extra else 0)
            end = min(own_end + pattern_len - 1, text_len)
            chunks.append((start, end, own_end))
            start = own_end
        return chunks

    # ---- введення/виведення ----

    def read_input(self):
        with open(self.input_file_name, "r") as f:
            # rstrip("\r\n"): файл могли створити на Windows
            pattern = f.readline().rstrip("\r\n")
            text = f.read().rstrip("\r\n")
        if not pattern:
            raise ValueError("pattern (first line of the input file) is empty")
        return pattern, text

    def write_output(self, n, m, total, chunks, results, t_read, t_parallel, t_total):
        # PARCS показує тривалість задачі цілими секундами, тому точні часи пишемо сюди
        with open(self.output_file_name, "w") as f:
            f.write("matches %d\n" % total)
            f.write("text_len %d\n" % n)
            f.write("pattern_len %d\n" % m)
            f.write("workers %d\n" % len(self.workers))
            f.write("chunks %d\n" % len(chunks))
            f.write("read_time_s %.4f\n" % t_read)
            f.write("parallel_time_s %.4f\n" % t_parallel)
            f.write("total_time_s %.4f\n" % t_total)
            worker_times = [r[1] for r in results]
            f.write("max_worker_search_s %.4f\n" % (max(worker_times) if worker_times else 0.0))
            for i, ((start, end, own_end), (count, wt)) in enumerate(zip(chunks, results)):
                f.write("chunk %d: [%d, %d) own_end %d, matches %d, search %.4f s\n"
                        % (i, start, end, own_end, count, wt))
