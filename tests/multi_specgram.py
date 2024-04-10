import asyncio
import random
import time
from concurrent.futures import ProcessPoolExecutor

from src.fingerprint_mining import get_fingerprint


async def main():
    record_names: list[str] = []
    record_amps: list[list[int]] = []
    for num in range(0, 400):
        record_name = str(random.randint(0, 10000))
        amps = [random.randint(-32000, 32000) for _ in range(0, 8000)]
        record_names.append(record_name)
        record_amps.append(amps)
    results = []
    times = []
    use_process = True
    use_map = False
    executor = ProcessPoolExecutor(max_workers=8)

    for rec in range(0, 100):
        if use_process and use_map:
            start_time = time.time()
            for result in executor.map(get_fingerprint, record_names, record_amps):
                results.append(result)

            print(f'len results ={len(results)}')
            print(f'time={time.time() - start_time}')
            if rec > 0:
                times.append(time.time() - start_time)
        elif use_process:
            start_time = time.time()
            tasks = []
            for name, amps in zip(record_names, record_amps):
                task = asyncio.get_running_loop().run_in_executor(executor, get_fingerprint, name, amps)
                tasks.append(task)

            for task in asyncio.as_completed(tasks):
                results.append(await task)

            print(f'len results ={len(results)}')
            print(f'time={time.time() - start_time}')
            if rec > 0:
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


if __name__ == '__main__':
    asyncio.run(main())
