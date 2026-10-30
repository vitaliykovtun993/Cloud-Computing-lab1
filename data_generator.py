# -*- coding: utf-8 -*-
"""Генератор вхідних даних.

Формат файлу: перший рядок — зразок, другий — текст (без переносів усередині).
"""
from __future__ import print_function

import argparse
import os
import random
import time

# пишемо блоками по 1 МБ, щоб не тримати в пам'яті весь текст
BLOCK_SIZE = 1024 * 1024
MB = 1024 * 1024


def random_block(alphabet, size, rnd):
    n = len(alphabet)
    # rnd() замість random.choice: помітно швидше, а це сотні мільйонів викликів
    return "".join([alphabet[int(rnd() * n)] for _ in range(size)])


def write_random(out, alphabet, size, rnd):
    while size > 0:
        block = min(size, BLOCK_SIZE)
        out.write(random_block(alphabet, block, rnd).encode("ascii"))
        size -= block


def insertion_positions(text_len, pattern_len, count, rnd):
    """Відсортовані позиції count неперекривних копій зразка в тексті."""
    free = text_len - count * pattern_len
    if free < 0:
        raise ValueError("text is too short to insert the pattern %d times" % count)
    # випадкові точки у «вільному» місці + зсув i*m: копії гарантовано не накладаються
    offsets = sorted(int(rnd() * (free + 1)) for _ in range(count))
    return [off + i * pattern_len for i, off in enumerate(offsets)]


def generate(path, size, alphabet, pattern, insert_count, seed):
    """Записує файл і повертає позиції вставлених копій зразка."""
    rnd = random.Random(seed).random
    positions = insertion_positions(size, len(pattern), insert_count, rnd)

    # бінарний режим: на Windows текстовий режим записав би \r\n,
    # а читати файл будуть під Linux у PARCS
    with open(path, "wb") as out:
        out.write((pattern + "\n").encode("ascii"))
        written = 0
        for pos in positions:
            write_random(out, alphabet, pos - written, rnd)
            out.write(pattern.encode("ascii"))
            written = pos + len(pattern)
        write_random(out, alphabet, size - written, rnd)
        out.write(b"\n")
    return positions


def check_ascii_line(name, value):
    if "\n" in value or "\r" in value:
        raise ValueError("%s must not contain line breaks" % name)
    try:
        value.encode("ascii")
    except UnicodeError:
        # не-ASCII символи займали б кілька байт, і «розмір у МБ» перестав би збігатися
        raise ValueError("%s must contain only ASCII characters" % name)


def main():
    parser = argparse.ArgumentParser(description="Генератор тексту і зразка для KMP")
    size_group = parser.add_mutually_exclusive_group(required=True)
    size_group.add_argument("--size", type=int, help="довжина тексту в символах")
    size_group.add_argument("--size-mb", type=float, help="довжина тексту в МБ (1 МБ = 2^20 символів)")
    parser.add_argument("--alphabet", default="ACGT", help="алфавіт тексту (за замовчуванням ACGT)")
    parser.add_argument("--pattern", help="зразок; якщо не задано — випадковий з алфавіту")
    parser.add_argument("--pattern-length", type=int, default=8,
                        help="довжина випадкового зразка (якщо --pattern не задано)")
    parser.add_argument("--insert", type=int, default=0,
                        help="скільки разів гарантовано вставити зразок у текст")
    parser.add_argument("--seed", type=int, default=42, help="seed генератора")
    parser.add_argument("-o", "--output", default=os.path.join("data", "input.txt"),
                        help="вихідний файл (за замовчуванням data/input.txt)")
    args = parser.parse_args()

    size = args.size if args.size is not None else int(args.size_mb * MB)
    if size < 0:
        parser.error("size must be >= 0")
    if not args.alphabet:
        parser.error("alphabet must be non-empty")
    if args.insert < 0:
        parser.error("--insert must be >= 0")

    pattern = args.pattern
    if pattern is None:
        if args.pattern_length < 1:
            parser.error("--pattern-length must be >= 1")
        # окремий Random, щоб зразок не зсував послідовність, з якої генерується текст;
        # цілий seed і random() (а не рядок і choice) дають однаковий зразок у Python 2 і 3
        pattern = random_block(args.alphabet, args.pattern_length,
                               random.Random(args.seed + 1).random)
    if not pattern:
        parser.error("pattern must be non-empty")

    try:
        check_ascii_line("alphabet", args.alphabet)
        check_ascii_line("pattern", pattern)
    except ValueError as e:
        parser.error(str(e))

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    t0 = time.time()
    try:
        positions = generate(args.output, size, args.alphabet, pattern, args.insert, args.seed)
    except ValueError as e:
        parser.error(str(e))
    elapsed = time.time() - t0

    print("Файл:        %s" % args.output)
    print("Текст:       %d символів (%.2f МБ)" % (size, size / float(MB)))
    print("Алфавіт:     %s" % args.alphabet)
    print("Зразок:      %s (довжина %d)" % (pattern, len(pattern)))
    print("Вставлено:   %d копій (реальних входжень може бути більше)" % len(positions))
    print("Час:         %.2f с" % elapsed)


if __name__ == "__main__":
    main()
