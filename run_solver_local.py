# -*- coding: utf-8 -*-
"""Локальний запуск solver_kmp.py без PARCS — щоб зловити помилки до завантаження в хмару.

Воркери імітуються послідовно, тож час тут не показовий; перевіряється лише логіка.
Приклад: python run_solver_local.py data/small.txt --workers 4
"""
from __future__ import print_function

import argparse

from solver_kmp import Solver


class FakeResult(object):
    # асинхронний проксі Pyro4 повертає об'єкт, результат якого лежить у .value
    def __init__(self, value):
        self.value = value


class FakeWorker(object):
    def mymap(self, chunk, pattern, own_len):
        return FakeResult(Solver.mymap(chunk, pattern, own_len))


def main():
    parser = argparse.ArgumentParser(description="Локальний запуск solver_kmp.py")
    parser.add_argument("input", help="вхідний файл")
    parser.add_argument("--workers", type=int, default=3, help="кількість імітованих воркерів")
    parser.add_argument("-o", "--output", default="output_local.txt", help="вихідний файл")
    args = parser.parse_args()

    workers = [FakeWorker() for _ in range(args.workers)]
    Solver(workers, args.input, args.output).solve()
    with open(args.output) as f:
        print(f.read())


if __name__ == "__main__":
    main()
