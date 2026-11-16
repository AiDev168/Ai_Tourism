import io
import uuid
import zipfile
from types import SimpleNamespace

from app.modules.catalog import archive_ingest


class _Cursor:
    def __init__(self):
        self.last = None
        self.candidate_count = 0
        self.candidate_hash = None
        self.last_params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.last = sql
        self.last_params = params
        if "has_catalogue_review_capability" in sql:
            self.result = {"allowed": True}
        elif "INSERT INTO operations.dataset_import_batches" in sql:
            self.result = {
                "dataset_import_batch_id": uuid.UUID(int=1),
                "source_checksum": params[1],
                "data_class": "user_supplied_unverified",
            }
        elif "INSERT INTO operations.dataset_import_files" in sql:
            self.result = {"file_id": uuid.uuid4()}
        elif "INSERT INTO knowledge.destination_candidates" in sql:
            if self.candidate_hash is None:
                self.candidate_hash = params[4]
                self.candidate_count += 1
                self.result = {"candidate_id": uuid.uuid4()}
            else:
                self.result = None
        elif "SELECT row_sha256 FROM knowledge.destination_candidates" in sql:
            self.result = {"row_sha256": self.candidate_hash}
        else:
            self.result = None

    def fetchone(self):
        return self.result


class _Connection:
    def __init__(self):
        self.cursor_value = _Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.cursor_value


def _archive() -> bytes:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as nested:
        nested.writestr(
            "poi.csv",
            "destination_key,name_fa,province,latitude,longitude\npoi-1,نمونه,گیلان,37.2,49.6\n",
        )
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("delivery-a.zip", inner.getvalue())
        archive.writestr("delivery-b.zip", inner.getvalue())
    return outer.getvalue()


def test_archive_stage_deduplicates_identical_nested_deliveries_and_never_publishes(monkeypatch):
    connection = _Connection()
    monkeypatch.setattr(archive_ingest.psycopg, "connect", lambda **_kwargs: connection)
    settings = SimpleNamespace(
        database_host="localhost",
        database_port=5432,
        database_name="test",
        database_user="ai_tourism_app",
        database_password=SimpleNamespace(get_secret_value=lambda: "x"),
        database_connect_timeout_seconds=2,
    )
    user = SimpleNamespace(user_id=uuid.UUID(int=10))
    result = archive_ingest.stage_archive(_archive(), user, settings)
    assert result["csv_files"] == 2
    assert (
        result["rows_staged"] == 1
    )  # byte-identical repeated delivery yields one review candidate
    assert result["publication_approved"] is False
