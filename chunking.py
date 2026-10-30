# -*- coding: utf-8 -*-
"""Розбиття тексту на шматки з перекриттям і локальна імітація паралельного пошуку.

Цю логіку пізніше буде перенесено в PARCS: master ріже текст, воркери шукають.
"""
from __future__ import print_function

from kmp import kmp_search


def split_with_overlap(text_len, pattern_len, num_chunks):
    """Повертає список кортежів (start, end, own_end).

    [start, own_end) — «власна» частина шматка; власні частини без проміжків
    покривають весь текст. [start, end) — шматок разом з перекриттям
    pattern_len - 1 символів праворуч (обрізаний по кінцю тексту).
    """
    if pattern_len < 1:
        raise ValueError("pattern_len must be >= 1")
    if num_chunks < 1:
        raise ValueError("num_chunks must be >= 1")
    if text_len == 0:
        return []
    # шматків не більше, ніж символів: порожні шматки воркерам ні до чого
    num_chunks = min(num_chunks, text_len)

    # перші `extra` шматків на 1 символ довші — розміри відрізняються максимум на 1
    base, extra = divmod(text_len, num_chunks)
    chunks = []
    start = 0
    for i in range(num_chunks):
        own_end = start + base + (1 if i < extra else 0)
        # m-1 символів праворуч достатньо, щоб дочитати входження,
        # яке почалося в останній позиції власної частини
        end = min(own_end + pattern_len - 1, text_len)
        chunks.append((start, end, own_end))
        start = own_end
    return chunks


def parallel_search_simulated(text, pattern, num_chunks):
    """Послідовно обробляє шматки так, як це робили б воркери, і об'єднує результат."""
    result = []
    for start, end, own_end in split_with_overlap(len(text), len(pattern), num_chunks):
        # у PARCS саме цей зріз master надсилатиме воркеру
        chunk = text[start:end]
        for local_pos in kmp_search(chunk, pattern):
            global_pos = start + local_pos
            # При перекритті рівно m-1 входження, що починається в зоні перекриття,
            # у шматок не вміщується, тож фільтр нічого не відкине. Лишаємо його
            # як страховку: він гарантує відсутність дублікатів за будь-якого перекриття.
            if global_pos < own_end:
                result.append(global_pos)
    # шматки йдуть зліва направо, тому result уже відсортований
    return result


if __name__ == "__main__":
    print(split_with_overlap(10, 3, 3))  # [(0, 6, 4), (4, 9, 7), (7, 10, 10)]
    print(parallel_search_simulated("abababa", "aba", 3))  # [0, 2, 4]
