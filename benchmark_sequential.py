# -*- coding: utf-8 -*-
"""Базова лінія: послідовний KMP на файлі з data_generator.py.

Результати виводяться в консоль і дописуються рядком у results/sequential.csv.
"""
from __future__ import print_function

import argparse
import csv
import os
import platform
import sys
import time

from kmp import kmp_count, kmp_search


def read_input(path):
    """Повертає (pattern, text). Перший рядок файлу — зразок, решта — текст."""
    with open(path, "r") as f:
        # rstrip("\r\n"), а не strip(): пробіли можуть бути частиною зразка,
        # а \r лишається, якщо файл з Windows читають під Linux
        pattern = f.readline().rstrip("\r\n")
        text = f.read().rstrip("\r\n")
    return pattern, text


def open_for_append(path):
    # модуль csv у Python 2 хоче бінарний режим, у Python 3 — текстовий з newline=""
    if sys.version_info[0] >= 3:
        return open(path, "a", newline="")
    return open(path, "ab")


CSV_HEADER = ["datetime", "host", "python", "input_file", "text_len", "pattern_len",
              "matches", "mode", "repeat", "read_time_s", "search_time_min_s",
              "search_time_avg_s"]


def append_csv(path, row):
    out_dir = os.path.dirname(path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    with open_for_append(path) as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(CSV_HEADER)
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Послідовний бенчмарк KMP")
    parser.add_argument("input", help="вхідний файл (формат як у data_generator.py)")
    parser.add_argument("--mode", choices=["count", "search"], default="count",
                        help="count — лише кількість (kmp_count), search — список позицій (kmp_search)")
    parser.add_argument("--repeat", type=int, default=1,
                        help="скільки разів повторити пошук (у звіт іде мінімум і середнє)")
    parser.add_argument("--csv", default=os.path.join("results", "sequential.csv"),
                        help="куди дописати результат")
    parser.add_argument("--no-csv", action="store_true", help="не записувати CSV")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")

    t0 = time.time()
    pattern, text = read_input(args.input)
    read_time = time.time() - t0
    if not pattern:
        parser.error("pattern (first line of the file) is empty")

    times = []
    matches = 0
    for _ in range(args.repeat):
        t0 = time.time()
        if args.mode == "count":
            matches = kmp_count(text, pattern)
        else:
            matches = len(kmp_search(text, pattern))
        times.append(time.time() - t0)
    search_min = min(times)
    search_avg = sum(times) / len(times)

    print("Файл:              %s" % args.input)
    print("Python:            %s" % platform.python_version())
    print("Довжина тексту:    %d" % len(text))
    print("Довжина зразка:    %d" % len(pattern))
    print("Входжень:          %d" % matches)
    print("Режим:             %s, повторів: %d" % (args.mode, args.repeat))
    print("Час читання:       %.4f с" % read_time)
    print("Час пошуку (min):  %.4f с" % search_min)
    print("Час пошуку (avg):  %.4f с" % search_avg)

    if not args.no_csv:
        append_csv(args.csv, [
            time.strftime("%Y-%m-%d %H:%M:%S"),
            platform.node(),
            platform.python_version(),
            os.path.basename(args.input),
            len(text),
            len(pattern),
            matches,
            args.mode,
            args.repeat,
            "%.4f" % read_time,
            "%.4f" % search_min,
            "%.4f" % search_avg,
        ])
        print("Результат дописано в %s" % args.csv)


if __name__ == "__main__":
    main()
