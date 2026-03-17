"""
Explainability export system - enterprise feature.

Export decision explanations in multiple formats.

Copyright (c) 2026 Agentability
Licensed under MIT License
"""

from typing import Dict, Optional
import json
from pathlib import Path
from datetime import datetime


class ExplanationExporter:
    """
    Export decision explanations in multiple formats.
    
    Formats:
    - JSON (machine-readable)
    - Markdown (human-readable)
    - HTML (web-ready)
    - PDF (reports)
    
    This is what enterprises want for audit trails!
    """
    
    def export_decision(
        self,
        decision_dict: Dict,
        format: str = "json",
        output_path: Optional[str] = None
    ) -> str:
        """
        Export decision explanation.
        
        Args:
            decision_dict: Decision data as dict
            format: Export format (json, markdown, html, pdf)
            output_path: Optional path to save file
        
        Returns:
            Exported content as string (or path if saved)
        """
        if format == "json":
            return self._export_json(decision_dict, output_path)
        elif format == "markdown":
            return self._export_markdown(decision_dict, output_path)
        elif format == "html":
            return self._export_html(decision_dict, output_path)
        elif format == "pdf":
            return self._export_pdf(decision_dict, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, decision: Dict, output_path: Optional[str]) -> str:
        """Export as JSON."""
        content = json.dumps(decision, indent=2, default=str)
        
        if output_path:
            Path(output_path).write_text(content)
            return output_path
        
        return content
    
    def _export_markdown(self, decision: Dict, output_path: Optional[str]) -> str:
        """Export as Markdown."""
        lines = []
        lines.append("# Decision Explanation")
        lines.append(f"**Decision ID:** `{decision.get('decision_id', 'N/A')}`")
        lines.append(f"**Agent:** `{decision.get('agent_id', 'N/A')}`")
        lines.append(f"**Timestamp:** {decision.get('timestamp', 'N/A')}")
        lines.append(f"**Confidence:** {decision.get('confidence', 0.0):.2%}")
        lines.append("")
        
        lines.append("## Decision Output")
        lines.append("```")
        lines.append(str(decision.get('output', 'N/A')))
        lines.append("```")
        lines.append("")
        
        lines.append("## Reasoning Chain")
        for i, step in enumerate(decision.get('reasoning_steps', []), 1):
            step_type = step.get('reasoning_type', 'step')
            thought = step.get('thought', '')
            lines.append(f"{i}. **{step_type}**: {thought}")
        lines.append("")
        
        if decision.get('uncertainties'):
            lines.append("## Uncertainties")
            for u in decision['uncertainties']:
                lines.append(f"- {u}")
            lines.append("")
        
        if decision.get('tool_calls'):
            lines.append("## Tool Calls")
            for tool in decision['tool_calls']:
                tool_name = tool.get('tool_name')
                exec_time = tool.get('execution_time_ms', 0)
                lines.append(f"- **{tool_name}** ({exec_time}ms)")
            lines.append("")
        
        if decision.get('policy_violations'):
            lines.append("## ⚠️ Policy Violations")
            for v in decision['policy_violations']:
                severity = v.get('severity', 'unknown')
                desc = v.get('rule_description', '')
                lines.append(f"- **{severity.upper()}**: {desc}")
            lines.append("")
        
        lines.append("## Performance")
        lines.append(f"- **Latency:** {decision.get('latency_ms', 0):.1f}ms")
        
        if decision.get('llm_metrics'):
            llm = decision['llm_metrics']
            lines.append(f"- **Tokens:** {llm.get('total_tokens', 0)} ({llm.get('input_tokens', 0)} in, {llm.get('output_tokens', 0)} out)")
            lines.append(f"- **Cost:** ${llm.get('cost', 0):.4f}")
        
        md = "\n".join(lines)
        
        if output_path:
            Path(output_path).write_text(md)
            return output_path
        
        return md
    
    def _export_html(self, decision: Dict, output_path: Optional[str]) -> str:
        """Export as HTML."""
        decision_id = decision.get('decision_id', 'N/A')
        agent_id = decision.get('agent_id', 'N/A')
        timestamp = decision.get('timestamp', 'N/A')
        confidence = decision.get('confidence', 0.0)
        output = decision.get('output', 'N/A')
        
        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html>')
        html_parts.append('<head>')
        html_parts.append(f'<title>Decision Explanation - {decision_id}</title>')
        html_parts.append('<style>')
        html_parts.append('body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }')
        html_parts.append('.header { border-bottom: 2px solid #333; padding-bottom: 20px; }')
        html_parts.append('.section { margin: 30px 0; }')
        html_parts.append('.section h2 { color: #333; }')
        html_parts.append('</style>')
        html_parts.append('</head>')
        html_parts.append('<body>')
        
        html_parts.append('<div class="header">')
        html_parts.append('<h1>Decision Explanation</h1>')
        html_parts.append(f'<p><strong>ID:</strong> <code>{decision_id}</code></p>')
        html_parts.append(f'<p><strong>Agent:</strong> {agent_id}</p>')
        html_parts.append(f'<p><strong>Timestamp:</strong> {timestamp}</p>')
        html_parts.append(f'<p><strong>Confidence:</strong> {confidence:.1%}</p>')
        html_parts.append('</div>')
        
        html_parts.append('<div class="section">')
        html_parts.append('<h2>Decision Output</h2>')
        html_parts.append(f'<pre>{output}</pre>')
        html_parts.append('</div>')
        
        html_parts.append('<div class="section">')
        html_parts.append('<h2>Reasoning Chain</h2>')
        for i, step in enumerate(decision.get('reasoning_steps', []), 1):
            step_type = step.get('reasoning_type', 'step')
            thought = step.get('thought', '')
            html_parts.append(f'<p><strong>{i}. {step_type}:</strong> {thought}</p>')
        html_parts.append('</div>')
        
        html_parts.append('</body>')
        html_parts.append('</html>')
        
        html = '\n'.join(html_parts)
        
        if output_path:
            Path(output_path).write_text(html)
            return output_path
        
        return html
    
    def _export_pdf(self, decision: Dict, output_path: Optional[str]) -> str:
        """Export as PDF (requires weasyprint or similar)."""
        html_content = self._export_html(decision, None)
        
        try:
            from weasyprint import HTML
            pdf_content = HTML(string=html_content).write_pdf()
            
            if output_path:
                Path(output_path).write_bytes(pdf_content)
                return output_path
            
            return pdf_content
            
        except ImportError:
            raise ImportError(
                "PDF export requires weasyprint. "
                "Install with: pip install weasyprint"
            )
