import pathlib
import re
import shutil
import sys

name = sys.argv[1] if len(sys.argv) == 2 else ""
if not re.fullmatch(r"supplyflow_test_[0-9a-f]{32}", name):
    raise SystemExit("Only a generated SupplyFlow test database filestore may be removed.")
parent = pathlib.Path("/var/lib/odoo/filestore")
target = parent / name
if parent.resolve() != parent or target.is_symlink() or target.resolve().parent != parent:
    raise SystemExit("Unsafe test filestore path.")
if target.exists():
    shutil.rmtree(target)
