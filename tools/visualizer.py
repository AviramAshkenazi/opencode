import logging
import re
from typing import Union, Dict, Any, List

from .models import Trace, Span, ErrorPayload

logger = logging.getLogger(__name__)

def sanitize_string(text: str, is_id: bool = False) -> str:
    """Removes or replaces characters that could break Mermaid syntax."""
    if not text:
        return "unnamed"
    if is_id:
        # Keep only alphanumeric and underscores
        return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
    # Remove colons, commas, quotes, brackets, and parentheses
    return re.sub(r'[:,"\'\(\)\[\]{}]', ' ', str(text)).strip() or "unnamed_task"

def apply_semantic_zooming(spans: List[Span], max_spans: int = 50) -> List[Span]:
    if len(spans) <= max_spans:
        return sorted(spans, key=lambda x: x.start_time or 0.0)
        
    errors = [s for s in spans if s.status == "ERROR"]
    others = [s for s in spans if s.status != "ERROR"]
    
    needed_others = max(0, max_spans - len(errors))
    critical_others = sorted(others, key=lambda x: x.duration_ms or 0.0, reverse=True)[:needed_others]
    
    combined = errors + critical_others
    return sorted(combined, key=lambda x: x.start_time or 0.0)

def format_mermaid_line(span: Span, index: int, min_start_sec: float) -> str:
    """Formats a single span into a Mermaid Gantt line."""
    safe_name = sanitize_string(span.name, is_id=False)
    safe_id = f"task_{index}_{sanitize_string(span.span_id, is_id=True)}"
    
    start_ms = int(((span.start_time or 0.0) - min_start_sec) * 1000)
    end_ms = int(((span.end_time or 0.0) - min_start_sec) * 1000)
    
    # Ensure duration is at least 1ms to render properly in Mermaid
    if end_ms <= start_ms:
        end_ms = start_ms + 1
        
    # Mermaid syntax: Task Name : [status,] id, start, end
    status_tag = "crit, " if span.status == "ERROR" else ""
    return f"    {safe_name} :{status_tag}{safe_id}, {start_ms}, {end_ms}"

def generate_mermaid_gantt(trace: Trace) -> Union[Dict[str, Any], ErrorPayload]:
    """Transforms a Trace object into a Mermaid.js Gantt chart string."""
    if not trace.spans:
        return ErrorPayload(
            status="error",
            error_type="EmptyTrace",
            message="Cannot visualize an empty trace.",
            suggestion="Provide a valid parsed trace with populated spans."
        )

    valid_spans = [s for s in trace.spans if s.end_time is not None and s.start_time is not None]
    if not valid_spans:
        return ErrorPayload(
            status="error",
            error_type="NoValidSpans",
            message="No spans with valid start and end times found.",
            suggestion="Check if the pipeline crashed before completing any steps."
        )

    rendered_spans = apply_semantic_zooming(valid_spans)
    min_start_sec = rendered_spans[0].start_time

    mermaid_lines = [
        "```mermaid",
        "gantt",
        "    title FastCI Pipeline Execution Trace",
        "    dateFormat x",
        "    axisFormat %M:%S",
        "    section Execution Steps"
    ]
    
    for idx, span in enumerate(rendered_spans):
        mermaid_lines.append(format_mermaid_line(span, idx, min_start_sec))

    mermaid_lines.append("```")

    return {
        "status": "ok",
        "mermaid_syntax": "\n".join(mermaid_lines),
        "span_count": len(rendered_spans),
        "original_span_count": len(valid_spans)
    }

def format_pr_report(diff, trace_after) -> str:
    """Generates a rich Markdown report for GitHub PRs based on optimization results."""
    gantt_result = generate_mermaid_gantt(trace_after)
    mermaid_chart = gantt_result.get("mermaid_syntax", "") if isinstance(gantt_result, dict) else ""
    
    resolved_list = "\n".join([f"* ✅ `{b}`" for b in diff.bottlenecks_resolved])
    if not resolved_list:
        resolved_list = "* No specific bottlenecks fully eliminated, but overall time improved."

    return f"""### 🚀 FastCI: Pipeline Optimization Report

**TL;DR:** FastCI Agent successfully optimized the pipeline, reducing CI friction and resolving critical bottlenecks.

#### 📊 Impact Analysis
* ⏱️ **Time Saved:** `{diff.time_saved_ms / 1000}s` per run (**{diff.improvement_percent}% improvement**)
* 💰 **FinOps Delta:** `${diff.savings_delta_usd}/run`
* 🚦 **New Errors Introduced:** `{diff.new_errors_count}`

#### 🔍 Bottlenecks Resolved
{resolved_list}

#### 📈 Optimized Visual Trace
<details>
<summary>Click to view Mermaid Gantt</summary>

{mermaid_chart}

</details>

*Generated autonomously by FastCI Agent. See `decision_log.md` for my complete chain-of-thought.*"""
