"""
Unit tests for the pure functions in src/processing/chunker.py.
No database or GPU required.
"""

from src.processing.chunker import (
    count_tokens,
    build_text_with_offsets,
    find_timestamps_by_position,
)


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == 0


def test_count_tokens_increases_with_text_length():
    assert count_tokens("hello") < count_tokens("hello there, this is a longer sentence")


def test_count_tokens_is_deterministic():
    text = "The quick brown fox jumps over the lazy dog."
    assert count_tokens(text) == count_tokens(text)


def test_build_text_with_offsets_joins_segments_with_space():
    segments = [
        {"text": "Hello", "start_time": 0.0, "end_time": 1.0},
        {"text": "world", "start_time": 1.0, "end_time": 2.0},
    ]
    full_text, offsets = build_text_with_offsets(segments)

    assert full_text == "Hello world"
    assert offsets[0] == {"start_char": 0, "end_char": 5, "start_time": 0.0, "end_time": 1.0}
    assert offsets[1] == {"start_char": 6, "end_char": 11, "start_time": 1.0, "end_time": 2.0}


def test_build_text_with_offsets_skips_empty_segments():
    segments = [
        {"text": "Hello", "start_time": 0.0, "end_time": 1.0},
        {"text": "   ", "start_time": 1.0, "end_time": 1.5},
        {"text": "world", "start_time": 1.5, "end_time": 2.0},
    ]
    full_text, offsets = build_text_with_offsets(segments)

    assert full_text == "Hello world"
    assert len(offsets) == 2


def test_find_timestamps_by_position_locates_chunk_at_start():
    segments = [
        {
            "text": "This is the first segment with enough length to exceed thirty characters",
            "start_time": 0.0,
            "end_time": 3.0,
        },
        {
            "text": "This is the second segment also fairly long for the test",
            "start_time": 3.0,
            "end_time": 6.0,
        },
    ]
    full_text, offsets = build_text_with_offsets(segments)
    chunk_text = full_text[:60]

    start_time, end_time, chunk_end = find_timestamps_by_position(chunk_text, full_text, offsets)

    assert start_time == 0.0
    assert chunk_end == 60


def test_find_timestamps_by_position_locates_chunk_in_second_segment():
    segments = [
        {
            "text": "This is the first segment with enough length to exceed thirty characters",
            "start_time": 0.0,
            "end_time": 3.0,
        },
        {
            "text": "This is the second segment also fairly long for the test",
            "start_time": 3.0,
            "end_time": 6.0,
        },
    ]
    full_text, offsets = build_text_with_offsets(segments)
    seg2_start = offsets[1]["start_char"]
    chunk_text = full_text[seg2_start:seg2_start + 40]

    start_time, end_time, chunk_end = find_timestamps_by_position(
        chunk_text, full_text, offsets, search_start=seg2_start
    )

    assert start_time == 3.0


def test_find_timestamps_by_position_short_chunk_falls_back_to_search_start():
    # Chunks under 30 chars can't be located via prefix search (the shortest
    # prefix length tried is 30), so the function falls back to search_start.
    segments = [{"text": "word", "start_time": 5.0, "end_time": 6.0}]
    full_text, offsets = build_text_with_offsets(segments)

    _, _, chunk_end = find_timestamps_by_position("word", full_text, offsets, search_start=0)

    assert chunk_end == len("word")