"""
Prozess-Pool für unabhängige Rechenaufgaben (BSSA-Mehrfachstarts, später Screening,
Dmax-Scan, Messserien).

Windows-Besonderheiten (Start-Modus `spawn`):
- Ein neuer Prozess importiert normalerweise das Hauptmodul erneut (`__mp_main__`). In
  der App wäre das `scatter_plot.py` (PySide6, matplotlib …), unter `python -m unittest`
  sogar der Test-Runner. Deshalb werden alle Worker **beim Anlegen des Pools**
  gestartet, während `__main__.__file__`/`__spec__` kurz ausgeblendet sind. Die Worker
  importieren dann nur die Analysemodule, die sie für ihre Aufgabe brauchen.
- BLAS/OpenMP werden pro Worker auf einen Thread begrenzt (Umgebungsvariablen beim
  Prozessstart), sonst überbelegen n Worker × m BLAS-Threads die Kerne.
- Worker-Funktionen müssen auf Modulebene definiert sein (picklebar), kein Qt.

Reproduzierbarkeit: Zufallsströme hängen an den Aufgaben (Seeds), nicht an den Workern.
Ergebnisse sind daher unabhängig von der Worker-Zahl bitgleich (siehe Tests).

Fortschritt und Abbruch: Jeder Worker erhält beim Start eine gemeinsame Queue (Fortschritt)
und ein Event (Abbruch). Aufgaben melden über `report_progress()` und prüfen
`cancel_requested()`.
"""

import atexit
import multiprocessing as mp
import os
import queue as _queue
import sys
import threading
from contextlib import contextmanager
from typing import Callable, Iterable, List, Optional

_BLAS_VARS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')

# Im Worker gesetzt (siehe _init_worker)
_PROGRESS_QUEUE = None
_CANCEL_EVENT = None


class TasksCancelled(Exception):
    """Abbruch während einer Pool-Ausführung."""


def default_workers():
    """Standard: Kerne − 1 (mind. 1), höchstens 8."""
    return max(1, min(8, (os.cpu_count() or 2) - 1))


@contextmanager
def _limited_blas_env():
    saved = {v: os.environ.get(v) for v in _BLAS_VARS}
    try:
        for v in _BLAS_VARS:
            os.environ[v] = '1'
        yield
    finally:
        for v, val in saved.items():
            if val is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = val


@contextmanager
def _hidden_main():
    """Blendet __main__.__file__/__spec__ aus, damit spawn-Kinder das Hauptmodul nicht
    erneut ausführen (siehe multiprocessing.spawn.get_preparation_data)."""
    main = sys.modules.get('__main__')
    saved = {}
    try:
        if main is not None:
            for attr in ('__spec__', '__file__'):
                if attr in main.__dict__:
                    saved[attr] = main.__dict__[attr]
            if '__spec__' in saved:
                main.__spec__ = None
            if '__file__' in saved:
                del main.__file__
        yield
    finally:
        if main is not None:
            for attr, val in saved.items():
                setattr(main, attr, val)


def _init_worker(progress_queue, cancel_event, extra_path):
    global _PROGRESS_QUEUE, _CANCEL_EVENT
    _PROGRESS_QUEUE = progress_queue
    _CANCEL_EVENT = cancel_event
    for p in extra_path:
        if p not in sys.path:
            sys.path.insert(0, p)


def report_progress(item):
    """Aus einer Aufgabe heraus: Fortschritt an den Hauptprozess melden (nicht blockierend)."""
    if _PROGRESS_QUEUE is not None:
        try:
            _PROGRESS_QUEUE.put_nowait(item)
        except Exception:        # Fortschritt ist optional
            pass


def cancel_requested():
    return _CANCEL_EVENT is not None and _CANCEL_EVENT.is_set()


def _ping(_):
    return os.getpid(), 'PySide6' in sys.modules, '__mp_main__' in sys.modules


class WorkerPool:
    """Persistenter Pool mit n Prozessen (spawn)."""

    def __init__(self, n_workers: int):
        self.n_workers = int(n_workers)
        ctx = mp.get_context('spawn')
        self._progress = ctx.Queue()
        self._cancel = ctx.Event()
        # Projektwurzel für die Imports der Aufgaben (analysis.gift …)
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with _limited_blas_env(), _hidden_main():
            self._pool = ctx.Pool(self.n_workers, initializer=_init_worker,
                                  initargs=(self._progress, self._cancel, [root]))
        self._lock = threading.Lock()

    def worker_info(self):
        """(pid, PySide6 importiert?, __mp_main__ vorhanden?) je Worker — für Tests."""
        return self._pool.map(_ping, range(self.n_workers), chunksize=1)

    def run(self, fn: Callable, tasks: Iterable, progress: Optional[Callable] = None,
            poll_interval: float = 0.05) -> List:
        """Führt fn(task) für alle Aufgaben aus; Ergebnisse in Aufgabenreihenfolge.

        progress(item) wird im aufrufenden Thread für jede Fortschrittsmeldung aufgerufen;
        gibt er False zurück, wird abgebrochen (TasksCancelled).
        """
        tasks = list(tasks)
        with self._lock:              # ein Lauf zur Zeit (gemeinsame Queue/Event)
            self._cancel.clear()
            self._drain()
            async_result = self._pool.map_async(fn, tasks, chunksize=1)
            cancelled = False
            while not async_result.ready():
                async_result.wait(poll_interval)
                for item in self._drain():
                    if progress is not None and progress(item) is False and not cancelled:
                        cancelled = True
                        self._cancel.set()
            for item in self._drain():
                if progress is not None and not cancelled:
                    progress(item)
            results = async_result.get()
            self._cancel.clear()
            if cancelled:
                raise TasksCancelled()
            return results

    def _drain(self):
        items = []
        while True:
            try:
                items.append(self._progress.get_nowait())
            except _queue.Empty:
                return items

    def close(self):
        try:
            self._pool.terminate()
            self._pool.join()
        except Exception:
            pass


_POOL: Optional[WorkerPool] = None
_POOL_LOCK = threading.Lock()


def get_pool(n_workers: Optional[int] = None) -> WorkerPool:
    """Gemeinsamer, wiederverwendeter Pool (wird bei geänderter Worker-Zahl neu angelegt)."""
    global _POOL
    n = default_workers() if n_workers is None else max(1, int(n_workers))
    with _POOL_LOCK:
        if _POOL is None or _POOL.n_workers != n:
            if _POOL is not None:
                _POOL.close()
            _POOL = WorkerPool(n)
        return _POOL


def shutdown_pool():
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            _POOL.close()
            _POOL = None


atexit.register(shutdown_pool)
