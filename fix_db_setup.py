"""
Run this script ONCE to fix the DB2 connection on your machine.

    python fix_db_setup.py

What it does:
  1. Reinstalls ibm_db, ibm_db_sa, sqlalchemy (fresh, compatible versions)
  2. Patches a bug in ibm_db_dbi.py (AttributeError on get_current_schema)
  3. Verifies the connection to ATTPLANE works end-to-end
"""

import subprocess
import sys
import site

# ── 1. Reinstall packages ──────────────────────────────────────────────────────
print("Step 1: Reinstalling packages...")
pkgs = ["ibm_db", "ibm_db_sa", "sqlalchemy"]
subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y"] + pkgs)
subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs)
print("Packages installed.\n")

# ── 2. Patch ibm_db_dbi.py ────────────────────────────────────────────────────
print("Step 2: Patching ibm_db_dbi.py...")

import importlib, pathlib

# Reload site-packages after install
importlib.invalidate_caches()
import ibm_db_dbi as _dbi_mod
dbi_path = pathlib.Path(_dbi_mod.__file__)
print(f"  File: {dbi_path}")

src = dbi_path.read_text(encoding="utf-8")

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

if OLD in src:
    patched = src.replace(OLD, NEW, 1)
    dbi_path.write_text(patched, encoding="utf-8")
    print("  Patch applied.\n")
elif NEW in src:
    print("  Already patched, skipping.\n")
else:
    print("  WARNING: Could not find the expected code block.")
    print("  The ibm_db version on your machine may differ.")
    print("  Open ibm_db_dbi.py and find get_current_schema().")
    print("  Change the two lines shown below manually:\n")
    print("    BEFORE:  LogMsg(DEBUG, f'Current schema: {self.current_schema}')")
    print("    AFTER:   LogMsg(DEBUG, f'Current schema: {conn_schema}')\n")
    print("    BEFORE:  return self.current_schema")
    print("    AFTER:   return getattr(self, 'current_schema', None)\n")

# ── 3. Verify connection ───────────────────────────────────────────────────────
print("Step 3: Testing DB connection...")

import importlib
import ibm_db        # type: ignore
importlib.reload(ibm_db_dbi := __import__("ibm_db_dbi"))  # pick up the patch

from sqlalchemy import create_engine, text  # type: ignore

def _make_conn():
    conn_str = (
        "HOSTNAME=52.211.123.34;PORT=25010;DATABASE=ATTPLANE;"
        "PROTOCOL=TCPIP;UID=attgrp8;PWD=bigdata;"
        "AUTHENTICATION=SERVER;CURRENTSCHEMA=ATTGRP8;"
    )
    import ibm_db_dbi as _dbi
    return _dbi.Connection(ibm_db.connect(conn_str, "", ""))

try:
    engine = create_engine("ibm_db_sa://", creator=_make_conn)
    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT TABNAME FROM SYSCAT.TABLES "
            "WHERE TABSCHEMA='ATTGRP8' ORDER BY TABNAME"
        )).fetchall()
    print(f"  Connected! Tables visible: {[r[0] for r in tables]}")
    print("\nAll done. Restart your Jupyter kernel and run the notebook.")
except Exception as exc:
    print(f"  Connection test failed: {type(exc).__name__}: {exc}")
    print("  Check your network / VPN and try again.")
