import configparser
import pathlib
import subprocess
import sys

import psycopg2

CONFIG = "/run/odoo/odoo.conf"
BASE = ["odoo", "--config", CONFIG, "--no-http", "--max-cron-threads=0"]


def run_shell(filename):
    code = pathlib.Path("/opt/supplyflow", filename).read_text()
    subprocess.run(["odoo", "shell", "--config", CONFIG, "--no-http"], input=code, text=True, check=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "initialize"
    if mode == "initialize":
        config = configparser.RawConfigParser()
        config.read(CONFIG)
        options = config["options"]
        with psycopg2.connect(host=options["db_host"], dbname=options["db_name"], user=options["db_user"], password=options["db_password"]) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.ir_module_module')")
                exists = bool(cursor.fetchone()[0])
                installed = False
                if exists:
                    cursor.execute("SELECT state FROM ir_module_module WHERE name = 'supplyflow_office'")
                    installed = cursor.fetchone() == ("installed",)
        if not installed:
            subprocess.run(BASE + ["--stop-after-init", "--without-demo=True", "-i", "supplyflow_office"], check=True)
        run_shell("configure_instance.py")
    elif mode == "update":
        subprocess.run(BASE + ["--stop-after-init", "-u", "supplyflow_office"], check=True)
    elif mode == "seed":
        run_shell("training_data.py")
    else:
        raise SystemExit("Expected initialize, update, or seed")


if __name__ == "__main__":
    main()
