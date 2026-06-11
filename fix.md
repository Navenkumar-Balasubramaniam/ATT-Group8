# DB2 Connection Fix

Connecting to the ATTPLANE database from Python requires three fixes that are not obvious. Follow the steps below in order.

---

## Step 1 — Reinstall the DB packages

Open a terminal (Anaconda Prompt or VS Code terminal) and run:

```bash
pip uninstall -y ibm_db ibm_db_sa sqlalchemy
pip install ibm_db==3.2.9 ibm_db_sa==0.4.4 sqlalchemy==2.0.50
```

Or run the helper script included in this repo (does all three steps automatically):

```bash
python fix_db_setup.py
```

---

## Step 2 — Patch ibm_db_dbi.py

`ibm_db 3.2.9` has a bug: `get_current_schema()` tries to read `self.current_schema` before it is ever set, which raises `AttributeError` and surfaces as a confusing `SQL1042C` error.

Find the file:

```
<your-python>\Lib\site-packages\ibm_db_dbi.py
```

Locate the `get_current_schema` method (around line 1069) and make two changes:

**Before:**
```python
            LogMsg(DEBUG, f"Current schema: {self.current_schema}")
        except Exception as inst:
            LogMsg(EXCEPTION, f"An exception occurred while getting current schema: {inst}")
            raise _get_exception(inst)
        LogMsg(INFO, "exit get_current_schema()")
        return self.current_schema
```

**After:**
```python
            LogMsg(DEBUG, f"Current schema: {conn_schema}")
        except Exception as inst:
            LogMsg(EXCEPTION, f"An exception occurred while getting current schema: {inst}")
            raise _get_exception(inst)
        LogMsg(INFO, "exit get_current_schema()")
        return getattr(self, 'current_schema', None)
```

> The `fix_db_setup.py` script applies this patch automatically.

---

## Step 3 — Use AUTHENTICATION=SERVER in the connection

The DB2 CLI driver (used by Python) does not send `AUTHENTICATION=SERVER` by default, but the server requires it. The JDBC driver that tools like DBeaver use sends it automatically, which is why those tools connect fine while Python does not.

Replace the standard `make_db2_engine()` function in your notebook with the following:

```python
import ibm_db
import ibm_db_dbi
import ibm_db_sa
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import registry as _sa_registry
_sa_registry.register("db2", "ibm_db_sa.ibm_db", "DB2Dialect_ibm_db")
_sa_registry.register("db2.ibm_db", "ibm_db_sa.ibm_db", "DB2Dialect_ibm_db")
```

```python
def _make_raw_connection():
    conn_str = (
        f"HOSTNAME={DB_HOST};PORT={DB_PORT};DATABASE={DB_NAME};"
        f"PROTOCOL=TCPIP;UID={DB_USERNAME};PWD={DB_PASSWORD};"
        f"AUTHENTICATION=SERVER;CURRENTSCHEMA={DB_USERNAME.upper()};"
    )
    return ibm_db_dbi.Connection(ibm_db.connect(conn_str, "", ""))

def make_db2_engine():
    return create_engine("ibm_db_sa://", creator=_make_raw_connection)

engine = make_db2_engine()
```

> When the engine is created correctly it will show `Engine(ibm_db_sa://)`.
> The old broken approach shows `Engine(db2+ibm_db://attgrp8:***@...)`.

---

## Quick checklist

| Check | Expected result |
|---|---|
| `python fix_db_setup.py` completes without error | "DB2 connection successful" printed |
| Cell 3 output | `Engine(ibm_db_sa://)` |
| Cell 4 output | `DB2 connection successful` |
| TCP check (cell 2) | `TCP connection succeeded: 52.211.123.34:25010 is reachable` |

---

## Credentials

| Setting | Value |
|---|---|
| Host | `52.211.123.34` |
| Port | `25010` |
| Database | `ATTPLANE` |
| Username | `attgrp1` … `attgrp8` (use your group number) |
| Password | `bigdata` |
| Schema | Same as username in uppercase, e.g. `ATTGRP8` |
