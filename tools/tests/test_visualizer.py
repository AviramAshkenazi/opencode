import pytest
from tools.models import Span, Trace, ErrorPayload
from tools.visualizer import sanitize_string, apply_semantic_zooming, generate_mermaid_gantt

def test_mermaid_string_sanitation():
    """Ensures that characters that break Mermaid syntax are properly sanitized."""
    dangerous_name = 'npm run "build:prod" (test) [x]'
    safe_name = sanitize_string(dangerous_name)
    assert safe_name == "npm run  build prod   test   x"
    
    dangerous_id = "span-id-123!@#"
    safe_id = sanitize_string(dangerous_id, is_id=True)
    assert safe_id == "span_id_123___"

def test_semantic_zooming_protection():
    """Ensures protection against rendering crashes by truncating excessively long traces."""
    # Creating 60 spans with different durations
    spans = [
        Span(span_id=str(i), trace_id="t1", name=f"Task {i}", start_time=float(i), end_time=float(i*2), status="OK")
        for i in range(1, 61)
    ]
    
    zoomed_spans = apply_semantic_zooming(spans, max_spans=50)
    assert len(zoomed_spans) == 50
    # Ensure the longest span (task 60 which took 60 seconds) survived the filtering
    assert any(s.span_id == "60" for s in zoomed_spans)

def test_mermaid_gantt_generation():
    """Ensures the generated visual format is valid and contains the required information."""
    spans = [
        Span(span_id="1", trace_id="t1", name="Task 1", start_time=100.0, end_time=110.0, status="OK"),
        Span(span_id="2", trace_id="t1", name="Task 2 Error", start_time=105.0, end_time=115.0, status="ERROR")
    ]
    trace = Trace(trace_id="t1", spans=spans)
    
    result = generate_mermaid_gantt(trace)
    assert result["status"] == "ok"
    
    mermaid = result["mermaid_syntax"]
    assert "```mermaid" in mermaid
    assert "gantt" in mermaid
    assert "Task 1 :" in mermaid
    assert "Task 2 Error :crit," in mermaid

def test_visualizer_empty_trace():
    """Ensures the visualizer handles empty traces gracefully."""
    result = generate_mermaid_gantt(Trace(trace_id="t1", spans=[]))
    assert isinstance(result, ErrorPayload)
    assert result.error_type == "EmptyTrace"