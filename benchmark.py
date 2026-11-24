"""Quick throughput benchmark: python benchmark.py"""
import random
import shutil
import tempfile
import time

from minikv import MiniKV

N = 20_000
d = tempfile.mkdtemp()
db = MiniKV(d, memtable_limit=2000)

t = time.perf_counter()
for i in range(N):
    db.put(f"user:{i}", f"value-{i}")
w = time.perf_counter() - t

keys = [f"user:{random.randrange(N)}" for _ in range(N)]
t = time.perf_counter()
for k in keys:
    db.get(k)
r = time.perf_counter() - t

print(f"writes: {N / w:,.0f} ops/s   reads: {N / r:,.0f} ops/s   {db.stats()}")
db.close()
shutil.rmtree(d)
