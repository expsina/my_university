import time 
import threading 
import numpy as np
import matplotlib.pyplot as plt 


from multiprocessing import Queue, Process, Array

def amdahl_speedup(P, N):
    return 1 / ((1 - P) + P / N)

def worker(arr, start, end, queue: Queue):
    local_summary = sum(arr[start:end])
    queue.put(local_summary)

def parallel_sum(arr, num_processes):
    queue      = Queue()
    processes  = []
    chunk_size = len(arr) // num_processes

    for i in range(num_processes):
        start = i * chunk_size
        end   = start + chunk_size if i != num_processes - 1 else len(arr)
        p     = Process(target=worker, args=(arr, start, end, queue))
        
        processes.append(p)
        p.start()

    total = 0

    for i in range(num_processes):
        total += queue.get()

    for p in processes:
        p.join()

    return total

def calculate_fibonacci(n):

    n1 = 1
    n2 = 1

    for i in range(2, n):
        temporal_var = n2

        n2 = n1 + n2 
        n1 = temporal_var

    return n2

if __name__ == "__main__":

    print('\nPART I. Check threading of Non-parallelic algorithm\n')

    N              = 200_000
    threads_number = 4

    for i in range(2, threads_number + 1):
        print('=' * 30)
        print(f'Запуск с количеством потоков: {i}')

        start_time = time.perf_counter()

        for k in range(i):
            calculate_fibonacci(N)

        single_thread_time = time.perf_counter() - start_time

        start_time = time.perf_counter()

        threadings = []

        for k in range(i):
            thread = threading.Thread(target=calculate_fibonacci, args=(N, ))
            threadings.append(thread)
            thread.start()

        for thread in threadings:
            thread.join()

        multi_thread_time = (time.perf_counter() - start_time)

        print(single_thread_time)
        print(multi_thread_time)


    print('\nPART II. Add Multiprocessing\n')

    number_processes = 4
    test_array       = np.random.randint(low=0, high=10_000, size=10_000_000)


    for i in range(2, number_processes + 1):

        print('=' * 30)
        print(f'Запуск с количеством процессов: {i}')

        start = time.perf_counter()

        sum(test_array)

        non_parallelism_summary_time = time.perf_counter() - start     

        start = time.perf_counter()

        parallel_sum(test_array, i)

        with_parallelism_summary_time = time.perf_counter() - start

        print(f'Время суммирования без multiprocessing: {non_parallelism_summary_time}')
        print(f'Время суммирования с применением Multiprocessing: {with_parallelism_summary_time}')

    print('\nPART II.i Multiprocessing on Fibonacci numbers\n')

    N              = 200_000
    threads_number = 4

    for i in range(2, threads_number + 1):
        print('=' * 30)
        print(f'Запуск с количеством процессов: {i}')

        start_time = time.perf_counter()

        for k in range(i):
            calculate_fibonacci(N)

        single_thread_time = time.perf_counter() - start_time

        start_time = time.perf_counter()

        processes = []

        for k in range(i):
            process = Process(target=calculate_fibonacci, args=(N, ))
            processes.append(process)
            process.start()

        for process in processes:
            process.join()

        multi_process_time = (time.perf_counter() - start_time)

        print(f'{single_thread_time:1f}')
        print(f'{multi_process_time:1f}')

    print('\nPART IV. Visualization of Amdahl Law\n')

    n_values = np.arange(1, 17)
    p_values = [.5, .8, .95, .99]

    for p in p_values:
        s_values = [amdahl_speedup(p, n) for n in n_values]
        plt.plot(n_values, s_values, label=f'P={p}')

    plt.xlabel('Number of Threads')
    plt.ylabel('Speedup (S)')
    plt.title("Amdahl's Law")
    plt.legend()
    plt.grid(True)
    plt.show()



