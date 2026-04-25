import pytest
from tools.models import Span, Trace
from tools.diagnostics import analyze_trace

def test_oom_and_silent_failures_detection():
    """Ensures accurate detection of Out-of-Memory (OOM) and silent failures."""
    spans = [
        Span(span_id="1", trace_id="t1", name="job1", start_time=1.0, end_time=2.0, status="ERROR", attributes={"error.message": "killed: out of memory"}),
        Span(span_id="2", trace_id="t1", name="job2", start_time=2.0, end_time=3.0, status="UNSET", attributes={"exitCode": 137}),
        Span(span_id="3", trace_id="t1", name="job3", start_time=3.0, end_time=4.0, status="OK", attributes={"exit_code": 1})
    ]
    report = analyze_trace(Trace(trace_id="t1", spans=spans))
    
    assert len(report.oom_spans) == 2, "Should detect string match and code 137"
    assert len(report.silent_failures) == 1, "Should detect non-zero exit code"
    assert report.silent_failures[0]["name"] == "job3"

def test_finops_cache_savings():
    """Ensures that the financial savings calculation for cache usage is correct."""
    spans = [
        Span(span_id="1", trace_id="t1", name="actions/cache@v4", start_time=0.0, end_time=10.0, status="OK"), # 10s cache span
        Span(span_id="2", trace_id="t1", name="npm install", start_time=10.0, end_time=15.0, status="OK")
    ]
    report = analyze_trace(Trace(trace_id="t1", spans=spans))
    
    assert report.cache_report.total_cache_spans == 1
    assert report.cache_report.cache_duration_ms == 10000.0
    # Savings: 10s * $0.005/s = $0.05
    assert report.cache_report.estimated_savings_usd == pytest.approx(0.05)

def test_zombie_detection_and_concurrency():
    """Ensures accurate detection of zombie spans and correct concurrency calculation."""
    spans = [
        Span(span_id="1", trace_id="t1", name="Complete 1", start_time=10.0, end_time=20.0, status="OK"),
        Span(span_id="2", trace_id="t1", name="Complete 2", start_time=15.0, end_time=25.0, status="OK"),
        Span(span_id="3", trace_id="t1", name="Zombie", start_time=20.0, end_time=None, status="UNSET")
    ]
    report = analyze_trace(Trace(trace_id="t1", spans=spans))
    
    assert len(report.zombie_spans) == 1
    assert report.zombie_spans[0]["name"] == "Zombie"
    
    # Wall clock = 25 - 10 = 15s (15000ms). Compute = 10s + 10s = 20s (20000ms).
    # Concurrency = 20000 / 15000 = 1.33
    assert report.concurrency_score == pytest.approx(1.33, 0.01)

def test_flash_build_zero_division_protection():
    """Ensures protection against division by zero in extremely short traces."""
    spans = [
        Span(span_id="1", trace_id="t1", name="Fast Task", start_time=10.0, end_time=10.002, status="OK")
    ]
    report = analyze_trace(Trace(trace_id="t1", spans=spans))
    
    assert report.total_duration_ms == pytest.approx(2.0)
    assert report.concurrency_score == pytest.approx(1.0)

def test_detect_retries_and_rate_limits():
    """Verifies that CI friction (retries and rate limits) is correctly identified."""
    spans = [
        Span(span_id="1", trace_id="t1", name="npm install", start_time=1.0, end_time=2.0, status="ERROR"),
        Span(span_id="2", trace_id="t1", name="npm install", start_time=3.0, end_time=4.0, status="OK"),
        Span(span_id="3", trace_id="t1", name="github-api-call", start_time=5.0, end_time=6.0, status="ERROR", 
             attributes={"http.status_code": 429})
    ]
    
    report = analyze_trace(Trace(trace_id="t1", spans=spans))
    
    assert len(report.retries) == 1
    assert report.retries[0]["name"] == "npm install"
    assert report.retries[0]["attempts"] == 2
    
    assert len(report.rate_limits) == 1
    assert report.rate_limits[0]["name"] == "github-api-call"
