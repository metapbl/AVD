# QThread 워커가 내장 finished/started 를 가리지 않는지 고정 (R§4 T2).

import importlib
import inspect
import pkgutil

import pytest
from PySide6.QtCore import QThread

import workers
from workers.playlist_probe_worker import PlaylistProbeWorker


def _worker_classes():
    for mod_info in pkgutil.iter_modules(workers.__path__):
        mod = importlib.import_module(f"workers.{mod_info.name}")
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if issubclass(cls, QThread) and cls.__module__ == mod.__name__:
                yield cls


@pytest.mark.parametrize("cls", list(_worker_classes()), ids=lambda c: c.__name__)
def test_worker_does_not_shadow_builtin_signals(cls):
    assert "finished" not in vars(cls)
    assert "started" not in vars(cls)


def test_playlist_probe_worker_has_probe_ready():
    assert "probe_ready" in vars(PlaylistProbeWorker)
