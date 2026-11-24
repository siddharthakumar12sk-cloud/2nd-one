# MiniKV

A persistent, networked key-value database built from scratch in Python (standard library only). It implements the same core design as LevelDB, RocksDB and Cassandra: a **Log-Structured Merge tree**.

## Architecture

```
            ┌──────────────┐   TCP line protocol   ┌───────────────┐
 client ───►│ asyncio server├──────────────────────►│    MiniKV     │
            └──────────────┘                        │    engine     │
                                                    └───────┬───────┘
        write: 1) append to WAL  2) update memtable         │
        read : memtable → SSTables (newest → oldest)        │
                                                            ▼
   ┌─────────┐  full   ┌────────────────────────────────────────────┐
   │memtable │────────►│ sst-000001  sst-000002  sst-000003  ...    │
   │ (RAM)   │ flush   │ sorted, immutable, Bloom filter + index    │
   └────┬────┘         └──────────────────┬─────────────────────────┘
        │ durability                      │ compaction merges all, drops
        ▼                                 ▼ stale values + tombstones
   ┌─────────┐                        ┌──────────┐
   │ WAL     │                        │ MANIFEST │ atomic list of live tables
   └─────────┘                        └──────────┘
```

| Component | What it does |
|-----------|--------------|
| **WAL** (`wal.py`) | Every write is logged with a CRC32 checksum before it is applied, so crashes lose nothing. Torn/corrupt tail records are detected and ignored on recovery. |
| **Memtable** | In-memory write buffer, flushed to disk as a sorted SSTable when it reaches a size limit. |
| **SSTable** (`sstable.py`) | Immutable sorted files with a sparse index (binary search + short scan) for fast point lookups. |
| **Bloom filter** (`bloom.py`) | Lets reads skip SSTables that definitely don't contain a key. |
| **Tombstones** | Deletes are writes of a marker, so they correctly shadow older tables until compaction. |
| **Compaction** | Merges all SSTables into one and reclaims space. |
| **MANIFEST** | Atomically swapped file listing live tables, so a crash mid-compaction can never resurrect deleted data. Orphan files are garbage-collected on startup. |
| **Server** (`server.py`) | asyncio TCP server; engine calls run in a thread pool and are guarded by a lock. |

## Quick start

```bash
git clone https://github.com/<your-username>/minikv.git
cd minikv
pip install -e .
minikv-server --data-dir ./data          # terminal 1
minikv-cli                                # terminal 2
```

```
minikv> SET user:1 Sid
OK
minikv> GET user:1
VALUE Sid
minikv> SCAN user:
JSON [["user:1", "Sid"]]
```

Use it as a library:

```python
from minikv import MiniKV
db = MiniKV("./data")
db.put("language", "python")
print(db.get("language"))
```

Or over the network:

```python
from minikv import Client
c = Client(port=7379)
c.set("k", "v"); print(c.get("k"))
```

## Protocol
`PING`, `SET key value`, `GET key`, `DEL key`, `SCAN [prefix]`, `STATS`, `FLUSH`, `COMPACT`, `QUIT`. Values may contain spaces but not newlines.

## Tests and benchmark
```bash
pip install -r requirements.txt
pytest -v
python benchmark.py
```
The suite covers crash recovery, torn WAL writes, tombstones, compaction, orphan cleanup, Bloom filter accuracy, and concurrent clients.

## Design trade-offs and limitations
- SSTables are JSON lines for readability; a binary format with block compression would be faster.
- Compaction is a simple full merge. Leveled or size-tiered compaction would scale better.
- Compaction holds the global lock; a production system would compact in the background.
- `fsync` per write is optional (`MiniKV(..., fsync=True)`) because it trades speed for durability.

## Ideas to extend
TTL support, background compaction thread, range deletes, replication, a binary protocol.

## License
MIT
