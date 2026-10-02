from __future__ import annotations

import contextlib
import importlib
import importlib.util
import io
import os
import sys
import types
from pathlib import Path

SERVICES = Path(__file__).parents[1] / "services"


class StubMqttClient:
    def __init__(self, *args, **kwargs):
        self.published = []
        self.subscriptions = []
        self.on_message = None

    def connect(self, *args, **kwargs):
        return 0

    def publish(self, topic, payload=None, qos=0, **kwargs):
        self.published.append({"topic": topic, "payload": payload, "qos": qos})
        return 0

    def subscribe(self, topic, **kwargs):
        self.subscriptions.append(topic)
        return 0, 1

    def loop_start(self):
        pass

    def loop_stop(self):
        pass

    def disconnect(self):
        pass


def stub_mqtt():
    if "paho.mqtt.client" in sys.modules:
        return

    class CallbackAPIVersion:
        VERSION1 = 1
        VERSION2 = 2

    paho = types.ModuleType("paho")
    mqtt = types.ModuleType("paho.mqtt")
    client = types.ModuleType("paho.mqtt.client")
    client.Client = StubMqttClient
    client.CallbackAPIVersion = CallbackAPIVersion
    paho.mqtt = mqtt
    mqtt.client = client
    sys.modules.update({"paho": paho, "paho.mqtt": mqtt, "paho.mqtt.client": client})


def stub_db_env():
    # Settings() is constructed at import time and requires credentials.
    # create_engine() is lazy, so no connection is attempted.
    os.environ.setdefault("POSTGRES_USER", "test-user")
    os.environ.setdefault("POSTGRES_PASSWORD", "test-password")


def silence_stdout(test_case):
    """Redirect stdout for the duration of one test.

    The services log progress with emoji banners, which raise UnicodeEncodeError
    when stdout is a cp1252 console. Capturing into StringIO keeps the tests
    independent of the terminal's encoding and off the test report.
    """
    redirect = contextlib.redirect_stdout(io.StringIO())
    redirect.__enter__()
    test_case.addCleanup(redirect.__exit__, None, None, None)


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, SERVICES / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_app_package(name: str, service: str):
    """Load services/<service>/app under a unique name.

    erp-api and wms-api both expose a package literally called `app`, so importing
    either by its real name would let whichever loaded first shadow the other.
    """
    app_dir = SERVICES / service / "app"
    spec = importlib.util.spec_from_file_location(
        name, app_dir / "__init__.py", submodule_search_locations=[str(app_dir)]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return importlib.import_module(f"{name}.main")


class Row:
    """A plain stand-in for a mapped row."""

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        return f"Row({self.__dict__})"


def _matches(row, criterion) -> bool:
    actual = getattr(row, criterion.left.name)
    expected = criterion.right.value
    operator = criterion.operator.__name__
    if operator == "eq":
        return actual == expected
    if operator == "ge":
        return actual >= expected
    raise NotImplementedError(f"FakeSession cannot evaluate {operator!r}")


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *criteria):
        return _FakeQuery([row for row in self._rows if all(_matches(row, c) for c in criteria)])

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class FakeSession:
    """A session that evaluates real SQLAlchemy criteria against seeded rows.

    Filtering normally happens in Postgres. Interpreting the criteria here means a
    query only yields a row that genuinely satisfies the predicate the service
    wrote, so tests exercise the service's rules rather than a canned answer.
    """

    def __init__(self):
        self._rows = {}
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def seed(self, model, rows):
        self._rows[model] = list(rows)
        return self

    def query(self, model):
        return _FakeQuery(self._rows.get(model, []))

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True

    def flush(self):
        pass

    def refresh(self, instance):
        pass
