# -*- coding: utf-8 -*-
"""Послідовний пошук підрядка алгоритмом Кнута-Морріса-Пратта (KMP)."""
from __future__ import print_function


def prefix_function(pattern):
    """pi[i] — довжина найдовшого власного префікса pattern[:i+1],
    який одночасно є його суфіксом."""
    m = len(pattern)
    pi = [0] * m
    k = 0
    for i in range(1, m):
        # відкочуємось по вже порахованих значеннях, а не починаємо з нуля —
        # саме це дає лінійний час
        while k > 0 and pattern[i] != pattern[k]:
            k = pi[k - 1]
        if pattern[i] == pattern[k]:
            k += 1
        pi[i] = k
    return pi


def iter_matches(text, pattern):
    """Генератор позицій початку всіх входжень pattern у text."""
    # порожній зразок формально «входить» у кожну позицію, для задачі це безглуздо
    if not pattern:
        raise ValueError("pattern must be non-empty")
    pi = prefix_function(pattern)
    m = len(pattern)
    k = 0
    # enumerate, а не range(len(text)): у Python 2 range для 100 МБ тексту
    # створив би список на 100 млн елементів
    for i, c in enumerate(text):
        while k > 0 and c != pattern[k]:
            k = pi[k - 1]
        if c == pattern[k]:
            k += 1
        if k == m:
            yield i - m + 1
            # не обнуляємо k, а відкочуємось — так знаходяться перекривні входження
            k = pi[k - 1]


def kmp_search(text, pattern):
    """Список позицій початку всіх входжень (включно з перекривними)."""
    return list(iter_matches(text, pattern))


def kmp_count(text, pattern):
    """Кількість входжень без зберігання списку позицій."""
    count = 0
    for _ in iter_matches(text, pattern):
        count += 1
    return count


if __name__ == "__main__":
    print(kmp_search("abababa", "aba"))  # [0, 2, 4]
    print(kmp_count("aaaa", "aa"))       # 3
