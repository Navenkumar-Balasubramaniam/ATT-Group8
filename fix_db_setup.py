"""
Patches a bug in the ibm_db driver and verifies the DB2 connection.

Run AFTER installing packages:
    pip install .
    python fix_db_setup.py
"""

import sys
import pathlib

# ── Check ibm_db is installed ─────────────────────────────────────────────────
try:
    import ibm_db
    import ibm_db_dbi
except ImportError:
    print("ERROR: ibm_db is not installed. Run 'pip install .' first.")
    sys.exit(1)

# ── Patch ibm_db_dbi.py ───────────────────────────────────────────────────────
print("Patching ibm_db_dbi.py...")

dbi_path = pathlib.Path(ibm_db_dbi.__file__)

OLD = (
    "            LogMsg(DEBUG, f\"Current schema: {self.current_schema}\")\n"
    "        except Exception as inst:\n"
    "            LogMsg(EXCEPTION, f\"An exception occurred while getting current schema: {inst}\")\n"
    "            raise _get_exception(inst)\n"
    "        LogMsg(INFO, \"exit get_current_schema()\")\n"
    "        return self.current_schema"
)
NEW = (
    "            LogMsg(DEBUG, f\"Current schema: {conn_schema}\")\n"
    "        except Exception as inst:\n"
    "            LogMsg(EXCEPTION, f\"An exception occurred while getting current schema: {inst}\")\n"
    "            raise _get_exception(inst)\n"
    "        LogMsg(INFO, \"exit get_current_schema()\")\n"
    "        return getattr(self, 'current_schema', None)"
)

src = dbi_path.read_text(encoding="utf-8")

if NEW in src:
    print("  Already patched.\n")
elif OLD in src:
    dbi_path.write_text(src.replace(OLD, NEW, 1), encoding="utf-8")
    print("  Patch applied.\n")
else:
    print("  WARNING: Could not find expected code. ibm_db version may differ.")
    print("  See fix.md for manual patch instructions.\n")

# ── Verify connection ─────────────────────────────────────────────────────────
print("Testing DB2 connection...")

import importlib
importlib.invalidate_caches()

from sqlalchemy import create_engine, text  # type: ignore

DB_HOST     = "52.211.123.34"
DB_PORT     = 25010
DB_NAME     = "ATTPLANE"
DB_USERNAME = "attgrp8"
DB_PASSWORD = "bigdata"

def _make_conn():
    import ibm_db_dbi as _dbi
    conn_str = (
        f"HOSTNAME={DB_HOST};PORT={DB_PORT};DATABASE={DB_NAME};"
        f"PROTOCOL=TCPIP;UID={DB_USERNAME};PWD={DB_PASSWORD};"
        f"AUTHENTICATION=SERVER;CURRENTSCHEMA={DB_USERNAME.upper()};"
    )
    return _dbi.Connection(ibm_db.connect(conn_str, "", ""))

try:
    engine = create_engine("ibm_db_sa://", creator=_make_conn)
    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT TABNAME FROM SYSCAT.TABLES "
            "WHERE TABSCHEMA='ATTGRP8' ORDER BY TABNAME"
        )).fetchall()
    print(f"  Connected! Tables: {[r[0] for r in tables]}")
    print("\nAll done. Open Exploratory.ipynb, restart kernel, and run all cells.")
except Exception as exc:
    print(f"  Connection failed: {type(exc).__name__}: {exc}")
    print("  Check your network/VPN and that credentials are correct.")
