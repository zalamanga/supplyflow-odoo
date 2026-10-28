"""Create one private SupplyFlow database/filestore archive while Odoo is stopped."""

import argparse
import ast
import configparser
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import zipfile


DATABASE = "supplyflow"
ODOO_SERIES = "19.0"
POSTGRES_MAJOR = 17
FORMAT = "supplyflow-office-backup"
FORMAT_VERSION = 1
DATA_DIR = Path("/var/lib/odoo")
FILESTORE = DATA_DIR / "filestore" / DATABASE
CONFIG = Path("/run/odoo/odoo.conf")
ADDON_MANIFEST = Path("/mnt/extra-addons/supplyflow_office/__manifest__.py")
CHUNK_SIZE = 1024 * 1024


def addon_version():
    manifest = ast.literal_eval(ADDON_MANIFEST.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version.startswith(ODOO_SERIES + "."):
        raise ValueError("Versi addon tidak cocok dengan seri Odoo yang didukung.")
    return version


def database_environment():
    parser = configparser.RawConfigParser()
    if not parser.read(CONFIG):
        raise ValueError("Konfigurasi Odoo lokal tidak ditemukan.")
    settings = parser["options"]
    expected = {"db_name": DATABASE, "db_host": "postgres", "db_user": DATABASE, "db_port": "5432"}
    if any(settings.get(key) != value for key, value in expected.items()):
        raise ValueError("Backup hanya mendukung database lokal supplyflow pada layanan postgres.")
    if Path(settings.get("data_dir", "")).resolve() != DATA_DIR:
        raise ValueError("data_dir harus /var/lib/odoo.")
    password = settings.get("db_password", "")
    if not password:
        raise ValueError("Password koneksi database belum dikonfigurasi.")
    environment = os.environ.copy()
    environment.update(PGHOST="postgres", PGPORT="5432", PGUSER=DATABASE, PGDATABASE=DATABASE, PGPASSWORD=password, PGCONNECT_TIMEOUT="15")
    return environment


def checked_run(arguments, environment, capture=False):
    return subprocess.run(arguments, env=environment, check=True, text=True, stdout=subprocess.PIPE if capture else None)


def postgres_version(environment):
    value = checked_run(["psql", "--no-password", "--no-psqlrc", "--tuples-only", "--no-align", "--command", "SHOW server_version_num"], environment, capture=True).stdout.strip()
    if not value.isdigit() or int(value) // 10000 != POSTGRES_MAJOR:
        raise ValueError("Backup ini hanya mendukung PostgreSQL 17.")
    return int(value)


def check_quiet_database(environment):
    query = "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND usename = current_user AND pid <> pg_backend_pid()"
    count = checked_run(["psql", "--no-password", "--no-psqlrc", "--tuples-only", "--no-align", "--command", query], environment, capture=True).stdout.strip()
    if count != "0":
        raise ValueError("Masih ada koneksi aplikasi SupplyFlow. Hentikan proses Odoo sebelum backup.")


def filestore_files():
    if DATA_DIR.resolve() != DATA_DIR or FILESTORE.resolve() != FILESTORE:
        raise ValueError("Path filestore tidak boleh dialihkan melalui symlink.")
    if not FILESTORE.exists():
        return []
    result = []
    for path in sorted(FILESTORE.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise ValueError("Filestore memuat symlink atau berkas khusus yang tidak didukung.")
        if stat.S_ISREG(mode):
            if FILESTORE not in path.resolve().parents:
                raise ValueError("Berkas filestore berada di luar lokasi yang diizinkan.")
            result.append(path)
    return result


def add_file(archive, source, member, compression):
    digest = hashlib.sha256()
    size = 0
    info = zipfile.ZipInfo.from_file(source, arcname=member, strict_timestamps=False)
    info.compress_type = compression
    with source.open("rb") as incoming, archive.open(info, "w", force_zip64=True) as outgoing:
        while chunk := incoming.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
            outgoing.write(chunk)
    return {"path": member, "size": size, "sha256": digest.hexdigest()}


def create_backup(output):
    output = Path(output)
    if not output.is_absolute() or output.parent.resolve() != Path("/tmp").resolve() or output.suffix.lower() != ".zip":
        raise ValueError("Output harus berupa berkas .zip langsung di /tmp container backup.")
    environment = database_environment()
    version = postgres_version(environment)
    check_quiet_database(environment)
    current_addon_version = addon_version()
    files = filestore_files()
    created_output = False
    try:
        with tempfile.TemporaryDirectory(prefix="supplyflow-backup-") as temporary:
            dump = Path(temporary) / "database.dump"
            checked_run(["pg_dump", "--no-password", "--format=custom", "--no-owner", "--no-privileges", "--dbname", DATABASE, "--file", str(dump)], environment)
            with output.open("xb") as output_file:
                created_output = True
                with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
                    entries = [add_file(archive, dump, "database.dump", zipfile.ZIP_STORED)]
                    for file in files:
                        member = "filestore/" + file.relative_to(FILESTORE).as_posix()
                        entries.append(add_file(archive, file, member, zipfile.ZIP_DEFLATED))
                    manifest = {
                        "format": FORMAT,
                        "format_version": FORMAT_VERSION,
                        "database": DATABASE,
                        "odoo_series": ODOO_SERIES,
                        "addon_version": current_addon_version,
                        "postgres_version_num": version,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "files": entries,
                    }
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"archive": output.name, "bytes": output.stat().st_size, "filestore_files": len(files), "format_version": FORMAT_VERSION}))
    except BaseException:
        if created_output and output.exists() and output.parent.resolve() == Path("/tmp").resolve() and not output.is_symlink():
            output.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description="Backup lokal SupplyFlow; hentikan proses Odoo terlebih dahulu.")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    try:
        create_backup(arguments.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Backup gagal: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
