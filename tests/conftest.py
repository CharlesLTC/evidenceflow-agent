import shutil

import pytest

from evidenceflow.agent_graph import AgentService
from evidenceflow.config import ROOT, Settings


@pytest.fixture
def service_factory(tmp_path):
    (tmp_path / "data").mkdir()
    shutil.copyfile(ROOT / "data/documents.json", tmp_path / "data/documents.json")
    services = []

    def create(model=None, **settings):
        service = AgentService(Settings(root=tmp_path, **settings), model=model)
        services.append(service)
        return service

    yield create
    for service in services:
        service.sessions.close()
