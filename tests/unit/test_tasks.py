import tempfile
from pathlib import Path

from src.database.models import TaskStatus
from src.database.repository import TaskRepository
from src.services.task_manager import TaskManager


def test_task_cancellation_and_persistence():
    with tempfile.TemporaryDirectory() as directory:
        repository = TaskRepository(f"sqlite:///{Path(directory) / 'tasks.db'}")
        manager = TaskManager(repository)
        task = manager.create(42, "مهمة تجريبية")
        manager.start(task.id)
        manager.progress(task.id, 50)
        cancelled = manager.cancel(task.id)
        assert cancelled.status == TaskStatus.CANCELLED
        assert manager.get(task.id).progress == 50
