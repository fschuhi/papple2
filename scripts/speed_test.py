import struct
import time
from dataclasses import dataclass

N_EVENTS = 10_000_000

# Simulated trace record matching a memory access event:
# cycle (u32), pc (u16), address (u16), value (u8), is_write (u8) -> 10 bytes packed
RECORD_FORMAT = "<IH turn to HBB"  # '<IH turn to HBB' -> actually: '<IHHBB'
RECORD_FORMAT = "<IHHBB"
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)  # 10 bytes
CHUNK_CAPACITY = 65_536  # ~64K events per buffer (~640 KB per chunk)


@dataclass(slots=True)
class MemAccessEvent:
    cycle: int
    pc: int
    address: int
    value: int
    is_write: int


class ChunkedByteBuffer:
    """Preallocates fixed-size byte chunks to avoid dynamic reallocations."""

    def __init__(self, chunk_capacity: int = CHUNK_CAPACITY):
        self.chunk_capacity = chunk_capacity
        self.chunk_bytes = chunk_capacity * RECORD_SIZE
        self.chunks: list[bytearray] = [bytearray(self.chunk_bytes)]
        self.current_chunk_idx = 0
        self.offset = 0
        self.packer = struct.Struct(RECORD_FORMAT)

    def append(self, cycle: int, pc: int, addr: int, val: int, is_write: int) -> None:
        if self.offset >= self.chunk_bytes:
            self.chunks.append(bytearray(self.chunk_bytes))
            self.current_chunk_idx += 1
            self.offset = 0

        self.packer.pack_into(
            self.chunks[self.current_chunk_idx],
            self.offset,
            cycle,
            pc,
            addr,
            val,
            is_write,
        )
        self.offset += RECORD_SIZE

    def unpack_to_dataclasses(self) -> list[MemAccessEvent]:
        events = []
        unpack_from = self.packer.unpack_from
        for i, chunk in enumerate(self.chunks):
            # The last chunk may only be partially filled
            limit = self.offset if i == self.current_chunk_idx else self.chunk_bytes
            for off in range(0, limit, RECORD_SIZE):
                cycle, pc, addr, val, is_write = unpack_from(chunk, off)
                events.append(MemAccessEvent(cycle, pc, addr, val, is_write))
        return events


def bench_tuples() -> tuple[float, list]:
    out = []
    t0 = time.perf_counter()
    for i in range(N_EVENTS):
        out.append((i, 0x6000, 0x0300, 0x42, 1))
    t1 = time.perf_counter()
    return t1 - t0, out


def bench_dataclass() -> tuple[float, list]:
    out = []
    t0 = time.perf_counter()
    for i in range(N_EVENTS):
        out.append(MemAccessEvent(i, 0x6000, 0x0300, 0x42, 1))
    t1 = time.perf_counter()
    return t1 - t0, out


def bench_chunked_bytearray() -> tuple[float, float, list]:
    buf = ChunkedByteBuffer()
    t0 = time.perf_counter()
    for i in range(N_EVENTS):
        buf.append(i, 0x6000, 0x0300, 0x42, 1)
    t1 = time.perf_counter()

    # Deferred unpacking phase
    t2 = time.perf_counter()
    events = buf.unpack_to_dataclasses()
    t3 = time.perf_counter()

    return t1 - t0, t3 - t2, events


if __name__ == "__main__":
    print(f"Running benchmark with {N_EVENTS:,} events...\n")

    t_tuple, res_tuple = bench_tuples()
    print(f"1. Tuple + list.append:")
    print(f"   Record time:        {t_tuple*1000:.2f} ms ({t_tuple/N_EVENTS*1e9:.1f} ns/op)")

    t_dc, res_dc = bench_dataclass()
    print(f"\n2. Dataclass(slots=True) + list.append:")
    print(f"   Record time:        {t_dc*1000:.2f} ms ({t_dc/N_EVENTS*1e9:.1f} ns/op)")

    t_buf_rec, t_buf_unpack, res_buf = bench_chunked_bytearray()
    print(f"\n3. Chunked bytearray:")
    print(f"   Record time:        {t_buf_rec*1000:.2f} ms ({t_buf_rec/N_EVENTS*1e9:.1f} ns/op)")
    print(f"   Deferred unpack:    {t_buf_unpack*1000:.2f} ms ({t_buf_unpack/N_EVENTS*1e9:.1f} ns/op)")
    print(f"   Total (rec+unpack): {(t_buf_rec + t_buf_unpack)*1000:.2f} ms")

    assert len(res_tuple) == len(res_dc) == len(res_buf) == N_EVENTS
