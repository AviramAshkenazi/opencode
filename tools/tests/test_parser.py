import json
import pytest
from tools.parser import parse_trace_file
from tools.models import Trace, ErrorPayload

@pytest.fixture
def temp_trace_file(tmp_path):
    def _create_file(data_lines):
        file_path = tmp_path / "test_trace.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            for line in data_lines:
                if isinstance(line, str):
                    f.write(line + "\n")
                else:
                    f.write(json.dumps(line) + "\n")
        return file_path
    return _create_file

def test_parse_valid_trace_with_iso_times(temp_trace_file):
    """Tests correct parsing of ISO 8601 timestamps and trace_id inheritance."""
    data = [
        {
            "context": {"trace_id": "trace-123", "span_id": "span-1"},
            "name": "Install Dependencies",
            "start_time": "2026-04-23T10:00:00.000000Z",
            "end_time": "2026-04-23T10:00:05.000000Z",
            "status": {"code": 1}
        },
        {
            "context": {"span_id": "span-2"}, 
            "name": "Run Unit Tests",
            "start_time": "2026-04-23T10:00:05.000000Z",
            "end_time": "2026-04-23T10:00:10.000000Z",
            "status": {"code": 2}
        }
    ]
    file_path = temp_trace_file(data)
    result = parse_trace_file(file_path)
    
    assert isinstance(result, Trace)
    assert len(result.spans) == 2
    
    span1 = result.spans[0]
    assert span1.status == "OK"
    assert span1.duration_ms == pytest.approx(5000.0)
    
    span2 = result.spans[1]
    assert span2.trace_id == "trace-123"
    assert span2.status == "ERROR"

def test_malformed_json_resilience(temp_trace_file):
    """Tests that the parser skips malformed JSON lines without crashing."""
    data = [
        "{ broken json }",
        {"context": {"trace_id": "t1", "span_id": "s1"}, "name": "Valid", "start_time": "2026-04-23T10:00:00Z"}
    ]
    result = parse_trace_file(temp_trace_file(data))
    assert len(result.spans) == 1

def test_missing_file_handling():
    """Tests graceful error handling for missing files."""
    result = parse_trace_file("non_existent.jsonl")
    assert isinstance(result, ErrorPayload)
    assert result.error_type == "FileNotFound"

def test_clock_skew_time_traveler(temp_trace_file):
    """Ensures handling of clock skew where end time is before start time."""
    data = [
        {
            "context": {"trace_id": "t1", "span_id": "s1"},
            "name": "Time Traveler",
            "start_time": "2026-04-23T10:00:10.000000Z",
            "end_time": "2026-04-23T10:00:00.000000Z",
            "status": {"code": 1}
        }
    ]
    result = parse_trace_file(temp_trace_file(data))
    span = result.spans[0]
    
    assert span.end_time == span.start_time
    assert span.duration_ms == 0.0