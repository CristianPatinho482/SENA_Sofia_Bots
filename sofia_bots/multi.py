from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")
R = TypeVar("R")


def run_parallel(items: Iterable[T], worker: Callable[[T], R], max_workers: int) -> list[R]:
    if max_workers <= 1:
        return [worker(item) for item in items]

    results: list[R] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, item) for item in items]
        for future in as_completed(futures):
            results.append(future.result())
    return results

