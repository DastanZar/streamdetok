"""Strict UTF-8 scanner with explicit invalid-byte recovery.

scan returns (valid complete byte COUNT, viable tail length, dead offsets).
The count is not an offset into the original buffer if dead bytes exist.
Recovery consumes the valid part of an invalid sequence and resumes at the
first offending byte, matching Python's UTF-8 ignore decoder.
"""

from __future__ import annotations


def lead_len(byte: int) -> int:
    if 0 <= byte <= 0x7F:
        return 1
    if 0xC2 <= byte <= 0xDF:
        return 2
    if 0xE0 <= byte <= 0xEF:
        return 3
    if 0xF0 <= byte <= 0xF4:
        return 4
    return -1


def is_cont(byte: int) -> bool:
    return 0x80 <= byte <= 0xBF


def scan(buf: bytes) -> tuple[int, int, list[int]]:
    index = complete = 0
    dead: list[int] = []
    while index < len(buf):
        lead = buf[index]
        need = lead_len(lead)
        if need == -1:
            dead.append(index)
            index += 1
            continue
        consumed = 1
        while consumed < need and index + consumed < len(buf):
            byte = buf[index + consumed]
            low, high = 0x80, 0xBF
            if consumed == 1:
                if lead == 0xE0:
                    low = 0xA0
                elif lead == 0xED:
                    high = 0x9F
                elif lead == 0xF0:
                    low = 0x90
                elif lead == 0xF4:
                    high = 0x8F
            if not low <= byte <= high:
                break
            consumed += 1
        if consumed == need:
            complete += need
            index += need
        elif index + consumed == len(buf):
            return complete, consumed, dead
        else:
            dead.extend(range(index, index + consumed))
            index += consumed
    return complete, 0, dead


class UTF8:
    @staticmethod
    def pending(buf: bytes) -> tuple[bytes, bytes]:
        """Return complete valid bytes (invalid spans dropped) and a viable tail."""
        _, tail_len, dead = scan(buf)
        end = len(buf) - tail_len
        deadset = set(dead)
        return bytes(byte for i, byte in enumerate(buf[:end]) if i not in deadset), buf[end:]

    @staticmethod
    def complete(buf: bytes) -> bool:
        _, tail, dead = scan(buf)
        return tail == 0 and not dead

    @staticmethod
    def dead_positions(buf: bytes) -> list[int]:
        return scan(buf)[2]

    @staticmethod
    def dead(buf: bytes) -> bool:
        return bool(scan(buf)[2])
