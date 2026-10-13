import io
import json
from dataclasses import replace
import pytest
from cloudlayer.aws import AwsAdapter
from src.config import load


class Storage:
    def upload_file(self, path, bucket, key):
        self.bucket, self.key = bucket, key
        self.content = open(path, "rb").read()

    def download_file(self, bucket, key, path):
        assert (bucket, key) == (self.bucket, self.key)
        with open(path, "wb") as f:
            f.write(self.content)


def test_storage_prefix_and_bytes(tmp_path, monkeypatch):
    adapter = AwsAdapter(replace(load(False), blob_uri="s3://test-bucket/course", region="test"))
    storage = Storage()
    monkeypatch.setattr(adapter, "client", lambda _: storage)
    path = tmp_path / "in"
    path.write_bytes(b"a\x00b")
    uri = adapter.upload(str(path), "lab5/probe")
    assert uri == "s3://test-bucket/course/lab5/probe"
    adapter.download(uri, str(tmp_path / "out"))
    assert (tmp_path / "out").read_bytes() == path.read_bytes()


def test_invoke_requires_model_version(monkeypatch):
    class Runtime:
        def invoke_endpoint(self, **kwargs):
            assert json.loads(kwargs["Body"]) == {"temp_c": 80}
            return {"Body": io.BytesIO(b'{"probability":0.2}')}

    adapter = AwsAdapter(load(False))
    monkeypatch.setattr(adapter, "client", lambda _: Runtime())
    with pytest.raises(ValueError, match="versioned"):
        adapter.invoke("endpoint", {"temp_c": 80})
