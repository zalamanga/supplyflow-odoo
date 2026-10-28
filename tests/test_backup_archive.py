import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("supplyflow_restore", ROOT / "scripts/container/restore.py")
RESTORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESTORE)
ADDON_VERSION = "19.0.1.0.0"


class BackupArchiveValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="supplyflow-archive-test-")
        self.addCleanup(temporary.cleanup)
        self.archive = Path(temporary.name) / "archive.zip"

    def make_archive(self, mutate=None, extra=None):
        payload = {
            "database.dump": b"PGDMPsynthetic-validation-only",
            "filestore/ab/abcdef": b"synthetic training attachment",
        }
        manifest = {
            "format": RESTORE.FORMAT,
            "format_version": 1,
            "database": "supplyflow",
            "odoo_series": "19.0",
            "addon_version": ADDON_VERSION,
            "postgres_version_num": 170006,
            "created_at": "2026-10-28T00:00:00+00:00",
            "files": [
                {"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in payload.items()
            ],
        }
        if mutate:
            mutate(manifest, payload)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w") as archive:
                for name, data in payload.items():
                    archive.writestr(name, data)
                archive.writestr("manifest.json", json.dumps(manifest))
                if extra:
                    extra(archive)
        return self.archive

    def assert_invalid(self, mutate=None, extra=None):
        self.make_archive(mutate=mutate, extra=extra)
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            RESTORE.validate_archive(self.archive, ADDON_VERSION)

    def assert_invalid_path(self, name):
        self.assert_invalid(extra=lambda archive: archive.writestr(name, b"invalid"))

    def test_valid_archive(self):
        self.make_archive()
        manifest = RESTORE.validate_archive(self.archive, ADDON_VERSION)
        self.assertEqual(manifest["database"], "supplyflow")
        self.assertEqual(len(manifest["files"]), 2)

    def test_reject_parent_path(self):
        self.assert_invalid_path("../escape")

    def test_reject_absolute_path(self):
        self.assert_invalid_path("/absolute")

    def test_reject_filestore_parent_path(self):
        self.assert_invalid_path("filestore/../escape")

    def test_reject_backslash_path(self):
        self.assert_invalid_path("filestore\\escape")

    def test_reject_colon_path(self):
        self.assert_invalid_path("filestore/C:escape")

    def test_reject_empty_path_component(self):
        self.assert_invalid_path("filestore//empty")

    def test_reject_dot_path_component(self):
        self.assert_invalid_path("filestore/./dot")

    def test_reject_unexpected_file(self):
        self.assert_invalid_path("unexpected.txt")

    def test_reject_explicit_directory(self):
        self.assert_invalid_path("filestore/directory/")

    def test_reject_duplicate_name(self):
        self.assert_invalid(extra=lambda archive: archive.writestr("database.dump", b"duplicate"))

    def test_reject_case_duplicate_name(self):
        self.assert_invalid(extra=lambda archive: archive.writestr("DATABASE.DUMP", b"duplicate"))

    def test_reject_symlink(self):
        def extra(archive):
            info = zipfile.ZipInfo("filestore/ab/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "/etc/passwd")

        self.assert_invalid(extra=extra)

    def test_reject_changed_payload(self):
        self.assert_invalid(mutate=lambda manifest, payload: payload.update({"database.dump": b"PGDMPchanged"}))

    def test_reject_format_version_mismatch(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest.update(format_version=2))

    def test_reject_boolean_format_version(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest.update(format_version=True))

    def test_reject_wrong_database(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest.update(database="other"))

    def test_reject_wrong_addon(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest.update(addon_version="19.0.2.0.0"))

    def test_reject_wrong_postgres(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest.update(postgres_version_num=180001))

    def test_reject_wrong_odoo(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest.update(odoo_series="20.0"))

    def test_reject_missing_manifest_entry(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest["files"].pop())

    def test_reject_size_mismatch(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest["files"][0].update(size=999))

    def test_reject_invalid_hash(self):
        self.assert_invalid(mutate=lambda manifest, payload: manifest["files"][0].update(sha256="0" * 64))

    def test_reject_file_directory_collision(self):
        self.assert_invalid_path("filestore/ab/abcdef/file")

    def test_reject_wrong_dump_header(self):
        def mutate(manifest, payload):
            payload["database.dump"] = b"not-custom-dump"
            manifest["files"][0].update(
                size=len(payload["database.dump"]),
                sha256=hashlib.sha256(payload["database.dump"]).hexdigest(),
            )

        self.assert_invalid(mutate=mutate)


if __name__ == "__main__":
    unittest.main()
