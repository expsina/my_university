# Часть 1, задания 1 и 3 (развёртка, графы, ЯПФ) - только в pr3.md

import threading
import time
import random

# Часть 1, задание 2: d[i] = a[i] * b[i] + c[i], последовательно и в 4 потока
n = 1000000
a = [random.random() for _ in range(n)]
b = [random.random() for _ in range(n)]
c = [random.random() for _ in range(n)]
d = [0] * n

def work(s, e):
    for i in range(s, e):
        d[i] = a[i] * b[i] + c[i]

# последовательная версия
t0 = time.perf_counter()
work(0, n)
t_seq = time.perf_counter() - t0
d_seq = d
d = [0] * n

# параллельная версия, 4 блока
t0 = time.perf_counter()
th = [threading.Thread(target=work, args=(k * n // 4, (k + 1) * n // 4)) for k in range(4)]
for t in th: t.start()
for t in th: t.join()
t_par = time.perf_counter() - t0
print("ПР3.1 задание 2:", round(t_seq, 3), round(t_par, 3), d == d_seq)

# Часть 2, задание 1: сдваивание (читаем old, пишем new)
m = 1000
x = [i for i in range(m)]
# последовательная версия для сравнения
seq = x.copy()
for i in range(2, m):
    seq[i] = seq[i - 2] * 2 + seq[i - 1] * 0.5

# параллельная версия со сдваиванием
old = x.copy()
new = x.copy()

def step(s, e):
    for i in range(max(s, 2), e):
        new[i] = old[i - 2] * 2 + old[i - 1] * 0.5

th = [threading.Thread(target=step, args=(k * m // 4, (k + 1) * m // 4)) for k in range(4)]
for t in th: t.start()
for t in th: t.join()
print("ПР3.2 задание 1:", new == seq)

# Часть 2, задание 2: красно-чёрное упорядочение, 4 потока
h = w = 400
img = [[random.random() for _ in range(w)] for _ in range(h)]
orig = [r[:] for r in img]

def rb(color, s, e):
    for i in range(s, e):
        for j in range(1, w - 1):
            if (i + j) % 2 == color:
                img[i][j] = (img[i - 1][j] + img[i][j - 1] + img[i][j] + img[i][j + 1] + img[i + 1][j]) / 5

# сначала красные клетки (0), затем чёрные (1)
for color in (0, 1):
    th = [threading.Thread(target=rb, args=(color, 1 + k * (h - 2) // 4, 1 + (k + 1) * (h - 2) // 4)) for k in range(4)]
    for t in th: t.start()
    for t in th: t.join()
# проверка: последовательный красно-чёрный проход
res_img = img
img = [r[:] for r in orig]
rb(0, 1, h - 1)
rb(1, 1, h - 1)
print("ПР3.2 задание 2:", img == res_img)

# Часть 2, задание 3: размер блока при суммировании, потоки 2/4/8
data = list(range(1000000))
res = [0] * 8

def part(t, T, ch):
    r = 0
    for st in range(t * ch, len(data), T * ch):
        r += sum(data[st:st + ch])
    res[t] = r

for T in (2, 4, 8):
    for ch in (10, 100, 1000, 10000, 100000, 1000000):
        t0 = time.perf_counter()
        th = [threading.Thread(target=part, args=(t, T, ch)) for t in range(T)]
        for t in th: t.start()
        for t in th: t.join()
        print("ПР3.2 задание 3:", T, ch, round(time.perf_counter() - t0, 4), sum(res[:T]) == sum(data))
