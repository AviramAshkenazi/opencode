import json
import subprocess
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture
def dummy_trace(tmp_path):
    """Generates a basic trace file for CLI tests."""
    file_path = tmp_path / "dummy_trace.jsonl"
    data = {
        "context": {"trace_id": "1", "span_id": "1"},
        "name": "CLI Test",
        "start_time": "2026-04-23T10:00:00Z",
        "end_time": "2026-04-23T10:00:01Z",
        "status": {"code": 1}
    }
    with open(file_path, "w") as f:
        f.write(json.dumps(data) + "\n")
    return file_path

def run_cli_command(args: list) -> subprocess.CompletedProcess:
    """Function to run CLI commands and capture output."""
    cmd = ["python3", "-m", "tools.fastci_cli"] + args
    return subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

def test_cli_diagnose_success(dummy_trace):
    """Ensures the diagnose command returns valid JSON and exit code 0."""
    result = run_cli_command(["diagnose", str(dummy_trace)])
    
    assert result.returncode == 0
    output_data = json.loads(result.stdout)
    assert "concurrency_score" in output_data
    assert "total_duration_ms" in output_data

def test_cli_missing_file():
    """Ensures the CLI handles missing files gracefully."""
    result = run_cli_command(["diagnose", "some/fake/path.jsonl"])
    
    assert result.returncode == 2
    output_data = json.loads(result.stdout)
    assert output_data["status"] == "error"
    assert output_data["error_type"] == "FileNotFound"

def test_cli_schema_command():
    """Ensures the schema command (which generates the data contract for the AI) works correctly."""
    result = run_cli_command(["schema"])
    
    assert result.returncode == 0
    output_data = json.loads(result.stdout)
    assert output_data["status"] == "ok"
    
    schema = output_data["schema"]
    assert "DiagnosticReport" in schema
    assert "Span" in schema

def test_cli_visualize_raw_output(dummy_trace):
    """Checks that --raw flag outputs plain text instead of a JSON wrapper."""
    cmd = ["python3", "-m", "tools.fastci_cli", "visualize", str(dummy_trace), "--raw"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    # Output should start with the mermaid block, not with '{'
    assert result.stdout.strip().startswith("```mermaid")
    # Verify it's not a JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)

def test_cli_diff_impact(dummy_trace, tmp_path):
    """Verifies that the diff command correctly identifies improvements."""
    # Create an 'optimized' trace that is 500ms faster than dummy_trace (which was 1000ms)
    opt_path = tmp_path / "opt.jsonl"
    data = {
        "context": {"trace_id": "1", "span_id": "1"},
        "name": "CLI Test",
        "start_time": "2026-04-23T10:00:00Z",
        "end_time": "2026-04-23T10:00:00.500000Z", # 500ms duration
        "status": {"code": 1}
    }
    with open(opt_path, "w") as f:
        f.write(json.dumps(data) + "\n")
        
    result = run_cli_command(["diff", str(dummy_trace), str(opt_path)])
    assert result.returncode == 0
    
    diff_data = json.loads(result.stdout)
    assert diff_data["time_saved_ms"] == 500.0
    assert diff_data["improvement_percent"] == 50.0
