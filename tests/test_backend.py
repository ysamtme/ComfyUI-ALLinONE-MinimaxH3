import asyncio
import builtins
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


class _Routes:
    def get(self, _path):
        return lambda fn: fn

    post = get
    delete = get


class _Response:
    def __init__(self, data=None, status=200, text=""):
        self.data = data
        self.status = status
        self.text = text


class _MultipartField:
    name = "file"

    def __init__(self, filename, content):
        self.filename = filename
        self._chunks = [content, b""]

    async def read_chunk(self, _size):
        return self._chunks.pop(0)


class _MultipartReader:
    def __init__(self, field):
        self._fields = [field, None]

    async def next(self):
        return self._fields.pop(0)


class _UploadRequest:
    def __init__(self, filename, content):
        self._reader = _MultipartReader(_MultipartField(filename, content))

    async def multipart(self):
        return self._reader


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.input = cls.root / "input"
        cls.output = cls.root / "output"
        cls.temp_dir = cls.root / "temp"
        cls.user = cls.root / "user"
        for path in (cls.input, cls.output, cls.temp_dir, cls.user):
            path.mkdir()

        folder_paths = types.ModuleType("folder_paths")
        folder_paths.get_input_directory = lambda: str(cls.input)
        folder_paths.get_output_directory = lambda: str(cls.output)
        folder_paths.get_temp_directory = lambda: str(cls.temp_dir)
        folder_paths.get_user_directory = lambda: str(cls.user)
        folder_paths.get_filename_list = lambda _key: []
        folder_paths.get_annotated_filepath = lambda name: str(cls.input / name)
        folder_paths.folder_names_and_paths = {}
        sys.modules["folder_paths"] = folder_paths
        sys.modules["node_helpers"] = types.ModuleType("node_helpers")

        server = types.ModuleType("server")
        server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=_Routes()))
        sys.modules["server"] = server

        web = types.SimpleNamespace(
            json_response=lambda data, status=200: _Response(data, status),
            Response=lambda status=200, text="": _Response(status=status, text=text),
            FileResponse=lambda path: _Response({"path": path}),
        )
        aiohttp = types.ModuleType("aiohttp")
        aiohttp.web = web
        sys.modules["aiohttp"] = aiohttp

        path = Path(__file__).resolve().parents[1] / "nodes.py"
        spec = importlib.util.spec_from_file_location("h3_nodes_for_test", path)
        cls.nodes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.nodes)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        for folder in (self.input, self.output, self.temp_dir, self.user):
            for path in sorted(folder.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

    def test_upload_names_are_unique_and_atomic(self):
        first = asyncio.run(self.nodes.upload_file(_UploadRequest("same.mp4", b"one")))
        second = asyncio.run(self.nodes.upload_file(_UploadRequest("same.mp4", b"two")))
        self.assertEqual(first.status, 200)
        self.assertNotEqual(first.data["filename"], second.data["filename"])
        self.assertEqual((first.data["type"], first.data["subfolder"], first.data["kind"]), ("input", "", "video"))
        self.assertEqual((self.input / first.data["filename"]).read_bytes(), b"one")
        self.assertFalse(list(self.input.glob("*.part")))

    def test_media_paths_are_scoped(self):
        managed = self.output / self.nodes.SUBFOLDER
        managed.mkdir(parents=True)
        good = managed / "clip.mp4"
        good.write_bytes(b"x")
        self.assertEqual(Path(self.nodes._resolve_media_path("clip.mp4", self.nodes.SUBFOLDER, "output")), good)
        with self.assertRaises(ValueError):
            self.nodes._resolve_media_path("clip.mp4", "elsewhere", "output")
        with self.assertRaises(ValueError):
            self.nodes._resolve_media_path("clip.mp4", "../outside", "temp")

    def test_staging_reuses_and_cleans_old_files(self):
        managed = self.output / self.nodes.SUBFOLDER
        managed.mkdir(parents=True)
        source = managed / "source.mp4"
        source.write_bytes(b"video")
        name1, reused1 = self.nodes._stage_media(str(source), source.name)
        name2, reused2 = self.nodes._stage_media(str(source), source.name)
        self.assertFalse(reused1)
        self.assertTrue(reused2)
        self.assertEqual(name1, name2)
        old = self.input / "h3_src_old.mp4"
        old.write_bytes(b"old")
        os.utime(old, (1, 1))
        self.nodes._cleanup_staged_inputs(now=25 * 60 * 60)
        self.assertFalse(old.exists())
        self.assertTrue((self.input / name1).exists())

    def test_cache_fingerprint_does_not_read_media(self):
        media = self.input / "large.mp4"
        media.write_bytes(b"not actually large")
        fingerprint = json.dumps({"files": [{"type": "video", "name": media.name}]})
        original_open = builtins.open

        def guarded_open(path, *args, **kwargs):
            if Path(path) == media:
                raise AssertionError("media contents were read")
            return original_open(path, *args, **kwargs)

        with mock.patch("builtins.open", guarded_open):
            digest = self.nodes.H3CacheBust.IS_CHANGED(fingerprint)
        self.assertEqual(len(digest), 64)

    def test_legacy_favorite_migrates_to_media_key(self):
        managed = self.output / self.nodes.SUBFOLDER
        managed.mkdir(parents=True)
        (managed / "favorite.mp4").write_bytes(b"x")
        self.nodes._save_favorites({"favorite.mp4"})
        response = asyncio.run(self.nodes.get_gallery(None))
        item = response.data["videos"][0]
        self.assertTrue(item["favorite"])
        self.assertEqual(self.nodes._load_favorites(), {item["media_key"]})


if __name__ == "__main__":
    unittest.main()
