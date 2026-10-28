# %% [markdown]
# Задание 1. Читатели-писатели с приоритетом писателей

# %%
import threading
import time
import random
from contextlib import contextmanager


class WriterPriorityReadWriteLock:
    def __init__(self):
        self.mutex = threading.Lock()
        self.readers_can_proceed = threading.Condition(self.mutex)
        self.writer_can_proceed = threading.Condition(self.mutex)
        self.active_readers = 0
        self.writer_is_active = False
        self.waiting_writers = 0

    def acquire_read(self):
        with self.mutex:
            while self.writer_is_active or self.waiting_writers > 0:
                self.readers_can_proceed.wait()
            self.active_readers += 1

    def release_read(self):
        with self.mutex:
            self.active_readers -= 1
            if self.active_readers == 0:
                self.writer_can_proceed.notify()

    def acquire_write(self):
        with self.mutex:
            self.waiting_writers += 1
            while self.writer_is_active or self.active_readers > 0:
                self.writer_can_proceed.wait()
            self.waiting_writers -= 1
            self.writer_is_active = True

    def release_write(self):
        with self.mutex:
            self.writer_is_active = False
            if self.waiting_writers > 0:
                self.writer_can_proceed.notify()
            else:
                self.readers_can_proceed.notify_all()

    @contextmanager
    def read_locked(self):
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_locked(self):
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()

# %%
event_log = []
event_log_guard = threading.Lock()
priority_lock = WriterPriorityReadWriteLock()


def record_event(message):
    with event_log_guard:
        event_log.append(message)


def demo_reader(name, start_delay, reading_time):
    time.sleep(start_delay)
    record_event(f"{name} ждёт")
    with priority_lock.read_locked():
        record_event(f"{name} читает")
        time.sleep(reading_time)
        record_event(f"{name} закончил чтение")


def demo_writer(name, start_delay, writing_time):
    time.sleep(start_delay)
    record_event(f"{name} ждёт")
    with priority_lock.write_locked():
        record_event(f"{name} пишет")
        time.sleep(writing_time)
        record_event(f"{name} закончил запись")


scenario = [
    threading.Thread(target=demo_reader, args=("читатель 1", 0.0, 0.6)),
    threading.Thread(target=demo_reader, args=("читатель 2", 0.1, 0.6)),
    threading.Thread(target=demo_writer, args=("писатель", 0.2, 0.3)),
    threading.Thread(target=demo_reader, args=("читатель 3", 0.3, 0.2)),
    threading.Thread(target=demo_reader, args=("читатель 4", 0.4, 0.2)),
]

for thread in scenario:
    thread.start()
for thread in scenario:
    thread.join()

for event in event_log:
    print(event)

writer_finished_at = event_log.index("писатель закончил запись")
assert event_log.index("читатель 3 читает") > writer_finished_at
assert event_log.index("читатель 4 читает") > writer_finished_at
assert event_log.index("читатель 2 читает") < event_log.index("читатель 1 закончил чтение")
print("приоритет писателя соблюдён, читатели 1 и 2 читали одновременно")

# %%
stress_lock = WriterPriorityReadWriteLock()
state_guard = threading.Lock()
readers_inside = 0
writers_inside = 0
violations = []
shared_value = 0


def stress_reader(iterations):
    global readers_inside
    for _ in range(iterations):
        with stress_lock.read_locked():
            with state_guard:
                readers_inside += 1
                if writers_inside > 0:
                    violations.append("читатель вошёл при активном писателе")
            time.sleep(random.random() * 0.002)
            with state_guard:
                readers_inside -= 1


def stress_writer(iterations):
    global writers_inside, shared_value
    for _ in range(iterations):
        with stress_lock.write_locked():
            with state_guard:
                writers_inside += 1
                if writers_inside > 1 or readers_inside > 0:
                    violations.append("писатель вошёл не в одиночку")
            current = shared_value
            time.sleep(random.random() * 0.002)
            shared_value = current + 1
            with state_guard:
                writers_inside -= 1


stress_threads = (
    [threading.Thread(target=stress_reader, args=(40,)) for _ in range(8)]
    + [threading.Thread(target=stress_writer, args=(20,)) for _ in range(4)]
)

for thread in stress_threads:
    thread.start()
for thread in stress_threads:
    thread.join()

print("нарушений:", len(violations))
print("значение:", shared_value, "ожидается:", 4 * 20)
assert not violations
assert shared_value == 80

# %% [markdown]
# Задание 2. Пул потоков с методом wait()

# %%
import queue
import threading


class ThreadPool:
    def __init__(self, worker_count):
        self.task_queue = queue.Queue()
        self.pending_task_count = 0
        self.pending_tasks_condition = threading.Condition()
        self.collected_errors = []
        self.is_shut_down = False
        self.workers = [
            threading.Thread(target=self.worker_loop, daemon=True)
            for _ in range(worker_count)
        ]
        for worker in self.workers:
            worker.start()

    def submit(self, function, *args, **kwargs):
        with self.pending_tasks_condition:
            if self.is_shut_down:
                raise RuntimeError("пул остановлен")
            self.pending_task_count += 1
        self.task_queue.put((function, args, kwargs))

    def worker_loop(self):
        while True:
            task = self.task_queue.get()
            if task is None:
                return
            function, args, kwargs = task
            try:
                function(*args, **kwargs)
            except Exception as error:
                with self.pending_tasks_condition:
                    self.collected_errors.append(error)
            finally:
                with self.pending_tasks_condition:
                    self.pending_task_count -= 1
                    if self.pending_task_count == 0:
                        self.pending_tasks_condition.notify_all()

    def wait(self):
        with self.pending_tasks_condition:
            while self.pending_task_count > 0:
                self.pending_tasks_condition.wait()
            if self.collected_errors:
                first_error = self.collected_errors[0]
                self.collected_errors.clear()
                raise first_error

    def shutdown(self):
        with self.pending_tasks_condition:
            if self.is_shut_down:
                return
            self.is_shut_down = True
        for _ in self.workers:
            self.task_queue.put(None)
        for worker in self.workers:
            worker.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.shutdown()

# %%
completed_tasks = []
completed_tasks_guard = threading.Lock()


def slow_task(task_number):
    time.sleep(random.random() * 0.1)
    with completed_tasks_guard:
        completed_tasks.append(task_number)


def task_that_spawns_children(task_number, pool):
    for child in range(3):
        pool.submit(slow_task, task_number * 10 + child)


def failing_task():
    raise ValueError("ошибка в задаче")


pool = ThreadPool(4)

for number in range(10):
    pool.submit(slow_task, number)
pool.wait()
print("после первого wait выполнено задач:", len(completed_tasks))
assert len(completed_tasks) == 10

for number in range(100, 105):
    pool.submit(task_that_spawns_children, number, pool)
pool.wait()
print("после второго wait выполнено задач:", len(completed_tasks))
assert len(completed_tasks) == 10 + 15

pool.submit(failing_task)
try:
    pool.wait()
except ValueError as error:
    print("wait пробросил ошибку:", error)

pool.submit(slow_task, 999)
pool.wait()
assert 999 in completed_tasks
print("пул продолжает работать после wait")

pool.shutdown()

# %% [markdown]
# Задание 3. Параллельная быстрая сортировка

# %%
import random
import time


def partition_three_way(items, low, high):
    pivot = items[random.randint(low, high)]
    less_end = low
    scan_index = low
    greater_start = high
    while scan_index <= greater_start:
        if items[scan_index] < pivot:
            items[less_end], items[scan_index] = items[scan_index], items[less_end]
            less_end += 1
            scan_index += 1
        elif items[scan_index] > pivot:
            items[scan_index], items[greater_start] = items[greater_start], items[scan_index]
            greater_start -= 1
        else:
            scan_index += 1
    return less_end, greater_start


def sequential_quick_sort(items, low, high):
    while low < high:
        less_end, greater_start = partition_three_way(items, low, high)
        if less_end - low < high - greater_start:
            sequential_quick_sort(items, low, less_end - 1)
            low = greater_start + 1
        else:
            sequential_quick_sort(items, greater_start + 1, high)
            high = less_end - 1


def parallel_quick_sort_range(pool, items, low, high, sequential_threshold):
    if high - low + 1 <= sequential_threshold:
        sequential_quick_sort(items, low, high)
        return
    less_end, greater_start = partition_three_way(items, low, high)
    pool.submit(parallel_quick_sort_range, pool, items, low, less_end - 1, sequential_threshold)
    pool.submit(parallel_quick_sort_range, pool, items, greater_start + 1, high, sequential_threshold)


def parallel_quick_sort(pool, items, sequential_threshold=2000):
    if len(items) > 1:
        pool.submit(parallel_quick_sort_range, pool, items, 0, len(items) - 1, sequential_threshold)
        pool.wait()
    return items

# %%
sorting_pool = ThreadPool(4)

test_cases = {
    "пустой": [],
    "один элемент": [5],
    "случайный": [random.randint(0, 10**6) for _ in range(50000)],
    "много повторов": [random.randint(0, 5) for _ in range(50000)],
    "уже отсортирован": list(range(50000)),
    "обратный порядок": list(range(50000, 0, -1)),
}

for name, data in test_cases.items():
    expected = sorted(data)
    result = parallel_quick_sort(sorting_pool, list(data), sequential_threshold=500)
    assert result == expected, name
    print("ok:", name)

big_data = [random.random() for _ in range(300000)]

started_at = time.perf_counter()
parallel_result = parallel_quick_sort(sorting_pool, list(big_data))
parallel_time = time.perf_counter() - started_at

started_at = time.perf_counter()
sequential_result = list(big_data)
sequential_quick_sort(sequential_result, 0, len(sequential_result) - 1)
sequential_time = time.perf_counter() - started_at

assert parallel_result == sequential_result == sorted(big_data)
print(f"параллельная: {parallel_time:.2f} с, последовательная: {sequential_time:.2f} с")

sorting_pool.shutdown()


