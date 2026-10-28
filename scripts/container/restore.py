"""Validate and restore a trusted SupplyFlow archive into the fixed local database."""

import argparse
import ast
import configparser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile


DATABASE = "supplyflow"
ODOO_SERIES = "19.0"
POSTGRES_MAJOR = 17
FORMAT = "supplyflow-office-backup"
FORMAT_VERSION = 1
DATA_DIR = Path("/var/lib/odoo")
FILESTORE_PARENT = DATA_DIR / "filestore"
FILESTORE = FILESTORE_PARENT / DATABASE
CONFIG = Path("/run/odoo/odoo.conf")
ADDON_MANIFEST = Path("/mnt/extra-addons/supplyflow_office/__manifest__.py")
CHUNK_SIZE = 1024 * 1024
MAX_MEMBERS = 100000
MAX_UNCOMPRESSED = 32 * 1024 * 1024 * 1024
MAX_MANIFEST = 16 * 1024 * 1024


def addon_version():
    manifest = ast.literal_eval(ADDON_MANIFEST.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version.startswith(ODOO_SERIES + "."):
        raise ValueError("Versi addon lokal tidak cocok dengan Odoo 19.")
    return version


def database_environment():
    parser = configparser.RawConfigParser()
    if not parser.read(CONFIG):
        raise ValueError("Konfigurasi Odoo lokal tidak ditemukan.")
    settings = parser["options"]
    expected = {"db_name": DATABASE, "db_host": "postgres", "db_user": DATABASE, "db_port": "5432"}
    if any(settings.get(key) != value for key, value in expected.items()):
        raise ValueError("Restore hanya mendukung database lokal supplyflow pada layanan postgres.")
    if Path(settings.get("data_dir", "")).resolve() != DATA_DIR or not settings.get("db_password"):
        raise ValueError("Konfigurasi data_dir atau password koneksi database tidak valid.")
    environment = os.environ.copy()
    environment.update(PGHOST="postgres", PGPORT="5432", PGUSER=DATABASE, PGDATABASE=DATABASE, PGPASSWORD=settings["db_password"], PGCONNECT_TIMEOUT="15")
    return environment


def validate_member(info):
    name = info.filename
    parts = PurePosixPath(name).parts
    if not name or len(name) > 1024 or "\\" in name or ":" in name or "\x00" in name or name.startswith("/"):
        raise ValueError("Arsip memuat path yang tidak aman.")
    if any(part in ("", ".", "..") for part in name.split("/")) or not parts:
        raise ValueError("Arsip memuat komponen path yang tidak aman.")
    if name not in ("manifest.json", "database.dump") and not (len(parts) >= 2 and parts[0] == "filestore"):
        raise ValueError("Arsip memuat berkas di luar manifest, dump, atau filestore.")
    mode = (info.external_attr >> 16) & 0xFFFF
    kind = stat.S_IFMT(mode)
    if info.is_dir() or kind not in (0, stat.S_IFREG) or info.flag_bits & 1:
        raise ValueError("Direktori eksplisit, symlink, berkas khusus, dan ZIP terenkripsi tidak didukung.")
    if info.file_size < 0 or info.file_size > MAX_UNCOMPRESSED:
        raise ValueError("Ukuran anggota arsip melampaui batas.")


def validate_archive(path, expected_addon_version):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Arsip harus berupa berkas biasa, bukan symlink.")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not members or len(members) > MAX_MEMBERS:
            raise ValueError("Jumlah berkas arsip tidak valid atau melampaui batas.")
        names = set()
        total = 0
        for info in members:
            validate_member(info)
            if info.filename.casefold() in names:
                raise ValueError("Arsip memuat nama berkas duplikat.")
            names.add(info.filename.casefold())
            total += info.file_size
        if total > MAX_UNCOMPRESSED:
            raise ValueError("Total ukuran arsip melebihi 32 GiB.")
        for name in names:
            parent = PurePosixPath(name).parent
            while str(parent) != ".":
                if str(parent) in names:
                    raise ValueError("Arsip memuat nama berkas yang juga dipakai sebagai direktori.")
                parent = parent.parent
        if "manifest.json" not in archive.namelist() or "database.dump" not in archive.namelist():
            raise ValueError("Manifest atau dump database tidak ditemukan.")
        if archive.getinfo("manifest.json").file_size > MAX_MANIFEST:
            raise ValueError("Manifest terlalu besar.")
        manifest = json.loads(archive.read("manifest.json"))
        if not isinstance(manifest, dict):
            raise ValueError("Manifest harus berupa objek JSON.")
        required = {"format": FORMAT, "format_version": FORMAT_VERSION, "database": DATABASE, "odoo_series": ODOO_SERIES, "addon_version": expected_addon_version}
        if any(manifest.get(key) != value for key, value in required.items()):
            raise ValueError("Format, database, seri Odoo, atau versi addon arsip tidak cocok.")
        if type(manifest.get("format_version")) is not int:
            raise ValueError("Versi format manifest harus berupa integer.")
        postgres = manifest.get("postgres_version_num")
        if not isinstance(postgres, int) or postgres // 10000 != POSTGRES_MAJOR:
            raise ValueError("Arsip harus berasal dari PostgreSQL 17.")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) != len(members) - 1:
            raise ValueError("Daftar berkas manifest tidak lengkap.")
        expected_names = set(archive.namelist()) - {"manifest.json"}
        manifest_names = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256"}:
                raise ValueError("Entri manifest tidak valid.")
            name, size, digest = entry["path"], entry["size"], entry["sha256"]
            if not isinstance(name, str) or name not in expected_names or name in manifest_names:
                raise ValueError("Nama berkas manifest tidak cocok dengan arsip.")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0 or archive.getinfo(name).file_size != size:
                raise ValueError("Ukuran berkas tidak cocok dengan manifest.")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("SHA-256 manifest tidak valid.")
            actual = hashlib.sha256()
            with archive.open(name) as incoming:
                while chunk := incoming.read(CHUNK_SIZE):
                    actual.update(chunk)
            if actual.hexdigest() != digest:
                raise ValueError("Hash berkas tidak cocok; arsip rusak atau berubah.")
            manifest_names.add(name)
        if manifest_names != expected_names:
            raise ValueError("Berkas arsip dan manifest berbeda.")
        with archive.open("database.dump") as dump:
            if dump.read(5) != b"PGDMP":
                raise ValueError("Dump bukan format custom PostgreSQL.")
        return manifest


def check_filestore_location():
    if DATA_DIR.resolve() != DATA_DIR or FILESTORE_PARENT.resolve() != FILESTORE_PARENT or FILESTORE.resolve() != FILESTORE:
        raise ValueError("Path filestore tidak boleh dialihkan melalui symlink.")
    if FILESTORE.exists():
        if not FILESTORE.is_dir():
            raise ValueError("Target filestore bukan direktori.")
        for item in FILESTORE.rglob("*"):
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError("Filestore lama memuat symlink atau berkas khusus.")


def remove_working_directory(path):
    path = Path(path)
    if path.parent.resolve() != FILESTORE_PARENT or path.is_symlink() or not path.name.startswith((".supplyflow-restore-", ".supplyflow-previous-")):
        raise ValueError("Menolak penghapusan path di luar direktori kerja restore.")
    if path.exists():
        shutil.rmtree(path)


def restore_archive(archive_path, manifest):
    environment = database_environment()
    version = subprocess.run(["psql", "--no-password", "--no-psqlrc", "--tuples-only", "--no-align", "--command", "SHOW server_version_num"], env=environment, text=True, check=True, stdout=subprocess.PIPE).stdout.strip()
    if not version.isdigit() or int(version) // 10000 != POSTGRES_MAJOR:
        raise ValueError("Target restore harus PostgreSQL 17.")
    query = "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = current_user AND pid <> pg_backend_pid()"
    connections = subprocess.run(["psql", "--no-password", "--no-psqlrc", "--tuples-only", "--no-align", "--command", query], env=environment, text=True, check=True, stdout=subprocess.PIPE).stdout.strip()
    if connections != "0":
        raise ValueError("Masih ada koneksi aplikasi SupplyFlow. Hentikan proses Odoo sebelum restore.")
    check_filestore_location()
    FILESTORE_PARENT.mkdir(parents=True, exist_ok=True)
    suffix = uuid.uuid4().hex
    staged = FILESTORE_PARENT / (".supplyflow-restore-" + suffix)
    previous = FILESTORE_PARENT / (".supplyflow-previous-" + suffix)
    staged.mkdir(mode=0o700)
    old_moved = False
    try:
        with tempfile.TemporaryDirectory(prefix="supplyflow-restore-") as temporary:
            dump = Path(temporary) / "database.dump"
            with zipfile.ZipFile(archive_path) as archive:
                for entry in manifest["files"]:
                    name = entry["path"]
                    destination = dump if name == "database.dump" else staged.joinpath(*PurePosixPath(name).parts[1:])
                    if name != "database.dump" and staged not in destination.resolve().parents:
                        raise ValueError("Target ekstraksi berada di luar filestore staging.")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256()
                    size = 0
                    with archive.open(name) as incoming, destination.open("xb") as outgoing:
                        while chunk := incoming.read(CHUNK_SIZE):
                            digest.update(chunk)
                            size += len(chunk)
                            outgoing.write(chunk)
                    if size != entry["size"] or digest.hexdigest() != entry["sha256"]:
                        raise ValueError("Arsip berubah setelah validasi; restore dihentikan sebelum database diubah.")
            subprocess.run(["pg_restore", "--list", str(dump)], env=environment, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["pg_restore", "--no-password", "--clean", "--if-exists", "--no-owner", "--no-privileges", "--exit-on-error", "--single-transaction", "--dbname", DATABASE, str(dump)], env=environment, check=True)
        check_filestore_location()
        if FILESTORE.exists():
            FILESTORE.rename(previous)
            old_moved = True
        staged.rename(FILESTORE)
        if old_moved:
            remove_working_directory(previous)
        print(json.dumps({"restored_database": DATABASE, "filestore_files": len(manifest["files"]) - 1, "addon_version": manifest["addon_version"]}))
    except BaseException:
        if old_moved and previous.exists() and not FILESTORE.exists():
            previous.rename(FILESTORE)
        raise
    finally:
        if staged.exists():
            remove_working_directory(staged)


def main():
    parser = argparse.ArgumentParser(description="Restore hanya arsip SupplyFlow milik sendiri yang dipercaya; SQL dump bukan input aman dari orang asing.")
    parser.add_argument("--archive", required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--validate-only", action="store_true")
    choice.add_argument("--replace-database", action="store_true")
    arguments = parser.parse_args()
    try:
        manifest = validate_archive(arguments.archive, addon_version())
        if arguments.validate_only:
            print(json.dumps({"valid": True, "database": DATABASE, "payload_files": len(manifest["files"]), "addon_version": manifest["addon_version"]}))
        else:
            restore_archive(arguments.archive, manifest)
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Restore gagal: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
