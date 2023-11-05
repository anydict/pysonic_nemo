import random
import time

from src.fingerprint_mining import get_fingerprint

if __name__ == '__main__':
    record_names: list[str] = []
    record_amps: list[list[int]] = []
    for num in range(0, 400):
        record_name = str(random.randint(0, 10000))
        amps = [random.randint(-32000, 32000) for a in range(0, 8000)]
        record_names.append(record_name)
        record_amps.append(amps)
    results = []
    times = []
    use_process = True
    if use_process:
        import concurrent.futures

        executor = concurrent.futures.ProcessPoolExecutor(max_workers=8)

    for rec in range(0, 10):
        if use_process:
            start_time = time.time()
            # multiprocess
            for result in executor.map(get_fingerprint, record_names, record_amps):  # noqa
                results.append(result)

            # =print(f"results ={results}")
            print(f'len results ={len(results)}')
            print(f'time={time.time() - start_time}')
            times.append(time.time() - start_time)
        else:
            start_time = time.time()
            # only one thread
            for result in map(get_fingerprint, record_names, record_amps):
                results.append(result)

            # =print(f"results ={results}")
            print(f'len results ={len(results)}')
            print(f'time={time.time() - start_time}')
            times.append(time.time() - start_time)

    print(f"avg times={sum(times) / len(times)}")
