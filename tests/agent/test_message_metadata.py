from agent.message_metadata import (
    INFLIGHT_TASK_RESTATEMENT, TYPED_ASK, append_message, is_compaction_scaffolding, record_absorbed_message,
    replay_metadata_fields, stamp_message_timestamp,
)


def test_stamp_preserves_source_timestamp(monkeypatch):
    monkeypatch.setattr("agent.message_metadata.wall_time", lambda: 999.0)
    message = {"role": "user", "content": "hello", "timestamp": 123.0}

    result = stamp_message_timestamp(message)

    assert result is message
    assert message["timestamp"] == 123.0


def test_append_stamps_same_mapping_at_append_time(monkeypatch):
    monkeypatch.setattr("agent.message_metadata.wall_time", lambda: 456.0)
    messages = []
    message = {"role": "tool", "content": "ok"}

    result = append_message(messages, message)

    assert result is message
    assert messages == [message]
    assert message["timestamp"] == 456.0


def test_replay_keeps_a_user_rows_typed_ask_beside_the_scaffolding_flag():
    """Gateway replay carries the stamp (previous_message reads it after a restart) without
    turning the row into compaction scaffolding, which would skip its timestamp."""
    stamped = {"role": "user", "content": "x", "display_metadata": {TYPED_ASK: "ask", "other": 1}}
    both = {"role": "user", "content": "x", "display_metadata": {TYPED_ASK: "ask", INFLIGHT_TASK_RESTATEMENT: True}}

    assert replay_metadata_fields(stamped) == {"display_metadata": {TYPED_ASK: "ask"}}
    assert not is_compaction_scaffolding(stamped)
    assert replay_metadata_fields(both) == {"display_metadata": {INFLIGHT_TASK_RESTATEMENT: True, TYPED_ASK: "ask"}}
    assert replay_metadata_fields({**stamped, "role": "assistant"}) == {}


def test_a_fold_onto_scaffolding_forgets_the_typed_ask():
    """A summary carrier absorbing the in-flight task, or an anchor leading a scaffolding turn, leaves
    no single ask the stamp could name, so ``previous_message`` falls back to the row."""
    carrier = {"role": "user", "content": "summary", "_compressed_summary": True, "display_metadata": {TYPED_ASK: "a"}}
    record_absorbed_message(carrier, {"role": "user", "content": "task"})
    target = {"role": "user", "content": "ask\n\nnudge", "display_metadata": {TYPED_ASK: "ask"}}
    record_absorbed_message(target, {"role": "user", "content": "ask"}, dropped_leads=True)

    assert TYPED_ASK not in carrier["display_metadata"] and TYPED_ASK not in target["display_metadata"]
