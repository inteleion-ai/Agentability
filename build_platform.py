"""Build script to generate all Agentability platform files.

This script creates the complete file structure for the Agentability platform
following Google standards and best practices.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

def create_directory(path: str) -> None:
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {path}")

def write_file(path: str, content: str) -> None:
    """Write content to file."""
    Path(path).write_text(content, encoding='utf-8')
    print(f"Created file: {path}")

# SDK Files
SDK_BASE = BASE_DIR / "sdk" / "python" / "agentability"

# Drift Detector
DRIFT_DETECTOR = '''"""Quality drift detection for agent performance.

Detects degradation in decision quality, accuracy, and other metrics over time.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import statistics


@dataclass
class DriftReport:
    """Report on detected drift."""
    metric_name: str
    baseline_value: float
    current_value: float
    change: float
    drift_detected: bool
    severity: float
    timestamp: datetime


class DriftDetector:
    """Detects quality drift in agent metrics."""
    
    def __init__(self, baseline_window_hours: int = 24):
        self.baseline_window_hours = baseline_window_hours
        self.metrics_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a metric value."""
        if name not in self.metrics_history:
            self.metrics_history[name] = []
        self.metrics_history[name].append((datetime.now(), value))
    
    def detect_drift(
        self,
        metric_name: str,
        current_window_hours: int = 1,
        threshold: float = 0.1
    ) -> Optional[DriftReport]:
        """Detect drift in a metric."""
        if metric_name not in self.metrics_history:
            return None
        
        history = self.metrics_history[metric_name]
        now = datetime.now()
        
        # Calculate baseline
        baseline_cutoff = now - timedelta(hours=self.baseline_window_hours)
        baseline_values = [v for t, v in history if baseline_cutoff <= t < now - timedelta(hours=current_window_hours)]
        
        # Calculate current
        current_cutoff = now - timedelta(hours=current_window_hours)
        current_values = [v for t, v in history if t >= current_cutoff]
        
        if not baseline_values or not current_values:
            return None
        
        baseline_avg = statistics.mean(baseline_values)
        current_avg = statistics.mean(current_values)
        change = current_avg - baseline_avg
        
        drift_detected = abs(change / baseline_avg) > threshold if baseline_avg != 0 else False
        
        return DriftReport(
            metric_name=metric_name,
            baseline_value=baseline_avg,
            current_value=current_avg,
            change=change,
            drift_detected=drift_detected,
            severity=abs(change / baseline_avg) if baseline_avg != 0 else 0,
            timestamp=now
        )
'''

# Write drift detector
write_file(SDK_BASE / "analyzers" / "drift_detector.py", DRIFT_DETECTOR)

# Lineage Tracer
LINEAGE_TRACER = '''"""Information lineage tracking.

Tracks how information flows from sources through agents to decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


@dataclass
class InformationLineage:
    """Tracks lineage of information."""
    lineage_id: str
    source: str
    destination: str
    path: List[str]
    transformations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class LineageTracer:
    """Traces information lineage through agent system."""
    
    def __init__(self):
        self.lineages: List[InformationLineage] = []
        self.graph: Dict[str, Set[str]] = {}
    
    def record_lineage(
        self,
        source: str,
        destination: str,
        path: List[str],
        transformations: Optional[List[str]] = None
    ) -> InformationLineage:
        """Record information lineage."""
        lineage = InformationLineage(
            lineage_id=f"lineage_{len(self.lineages)}",
            source=source,
            destination=destination,
            path=path,
            transformations=transformations or []
        )
        
        self.lineages.append(lineage)
        
        # Update graph
        for i in range(len(path) - 1):
            if path[i] not in self.graph:
                self.graph[path[i]] = set()
            self.graph[path[i]].add(path[i + 1])
        
        return lineage
    
    def trace_back(self, destination: str) -> List[InformationLineage]:
        """Trace back to find all sources for a destination."""
        return [l for l in self.lineages if l.destination == destination]
'''

write_file(SDK_BASE / "analyzers" / "lineage_tracer.py", LINEAGE_TRACER)

# Cost Analyzer
COST_ANALYZER = '''"""LLM cost analysis and optimization.

Analyzes LLM usage costs and provides optimization recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import statistics


@dataclass
class CostOptimization:
    """Cost optimization recommendation."""
    optimization_type: str
    description: str
    estimated_savings_usd: float
    confidence: float


class CostAnalyzer:
    """Analyzes and optimizes LLM costs."""
    
    # Pricing per 1M tokens (approximate)
    MODEL_PRICING = {
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    }
    
    def __init__(self):
        self.costs: List[Dict[str, Any]] = []
    
    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        timestamp: Optional[datetime] = None
    ) -> float:
        """Record an LLM call and return its cost."""
        pricing = self.MODEL_PRICING.get(model, {"input": 10.0, "output": 30.0})
        
        cost = (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )
        
        self.costs.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "timestamp": timestamp or datetime.now()
        })
        
        return cost
    
    def get_total_cost(self, time_window_hours: Optional[int] = None) -> float:
        """Calculate total cost."""
        costs = self._filter_costs(time_window_hours)
        return sum(c["cost_usd"] for c in costs)
    
    def get_cost_by_model(self, time_window_hours: Optional[int] = None) -> Dict[str, float]:
        """Get costs broken down by model."""
        costs = self._filter_costs(time_window_hours)
        by_model: Dict[str, float] = {}
        
        for cost in costs:
            model = cost["model"]
            if model not in by_model:
                by_model[model] = 0.0
            by_model[model] += cost["cost_usd"]
        
        return by_model
    
    def suggest_optimizations(self) -> List[CostOptimization]:
        """Suggest cost optimizations."""
        optimizations = []
        by_model = self.get_cost_by_model(time_window_hours=24)
        
        # Check if using expensive models unnecessarily
        if "gpt-4" in by_model and by_model["gpt-4"] > 10.0:
            savings = by_model["gpt-4"] * 0.8  # 80% savings with cheaper model
            optimizations.append(CostOptimization(
                optimization_type="model_downgrade",
                description="Consider using GPT-3.5-turbo for simple tasks instead of GPT-4",
                estimated_savings_usd=savings,
                confidence=0.7
            ))
        
        return optimizations
    
    def _filter_costs(self, time_window_hours: Optional[int]) -> List[Dict[str, Any]]:
        if not time_window_hours:
            return self.costs
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        return [c for c in self.costs if c["timestamp"] >= cutoff]
'''

write_file(SDK_BASE / "analyzers" / "cost_analyzer.py", COST_ANALYZER)

# Conflict Analyzer
CONFLICT_ANALYZER = '''"""Multi-agent conflict analysis.

Analyzes conflicts between agents and recommends resolutions.
"""

from typing import Any, Dict, List, Optional
from ..metrics.conflict_metrics import ConflictMetricsCollector, ConflictMetric


class ConflictAnalyzer:
    """Analyzes multi-agent conflicts."""
    
    def __init__(self, collector: ConflictMetricsCollector):
        self.collector = collector
    
    def analyze_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """Perform deep analysis of a conflict."""
        return self.collector.get_game_theoretic_analysis(conflict_id)
    
    def get_conflict_hotspots(self) -> List[Tuple[str, str]]:
        """Identify agent pairs that conflict most."""
        return self.collector.get_most_conflicting_pairs(top_n=5)
'''

write_file(SDK_BASE / "analyzers" / "conflict_analyzer.py", CONFLICT_ANALYZER)

print("\\nCore analyzer files created successfully!")

# Integrations
INTEGRATIONS_BASE = SDK_BASE / "integrations"
create_directory(INTEGRATIONS_BASE)

# LangChain Integration
LANGCHAIN_INTEGRATION = '''"""LangChain auto-instrumentation.

Automatically instruments LangChain chains and agents with Agentability tracking.
"""

from typing import Any, Optional
from ..tracer import Tracer


class LangChainInstrumentation:
    """Auto-instruments LangChain components."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
    
    def instrument_chain(self, chain: Any) -> Any:
        """Instrument a LangChain chain."""
        # Wrap chain's __call__ method
        original_call = chain.__call__
        
        def instrumented_call(*args, **kwargs):
            with self.tracer.trace_decision(
                agent_id=f"langchain_{chain.__class__.__name__}",
                decision_type="generation"
            ) as ctx:
                result = original_call(*args, **kwargs)
                ctx.set_confidence(0.8)  # Default confidence
                return result
        
        chain.__call__ = instrumented_call
        return chain
'''

write_file(INTEGRATIONS_BASE / "__init__.py", "# Integrations module")
write_file(INTEGRATIONS_BASE / "langchain.py", LANGCHAIN_INTEGRATION)

print("Integration files created!")

# Create README
README = '''# 🚀 Agentability

**The Observability Standard for Production AI Agents**

<a href="https://github.com/agentdyne9/agentability"><img alt="GitHub stars" src="https://img.shields.io/github/stars/agentdyne9/agentability?style=social"></a>
<a href="https://pypi.org/project/agentability/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agentability"></a>
<a href="https://github.com/agentdyne9/agentability/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>

## What is Agentability?

While competitors show **WHAT** agents did, Agentability shows **WHY** they did it, **HOW** they thought about it, and **WHAT capabilities** they have.

## 🎯 Key Features

- **Memory Intelligence** - Track vector, episodic, semantic, and working memory
- **Decision Provenance** - Complete "why" chain for every decision
- **Conflict Analytics** - Game-theoretic multi-agent disagreement analysis
- **Causal Graphs** - Temporal causality mapping (not just traces)
- **Zerodha-Class UX** - Best-in-class charting and real-time updates
- **Offline + Online** - Works without infrastructure (SQLite) or scales (TimescaleDB)

## 🚀 Quick Start

### Installation

```bash
pip install agentability
```

### Basic Usage

```python
from agentability import Tracer

tracer = Tracer(offline_mode=True)

# Track a decision
with tracer.trace_decision(
    agent_id="risk_agent",
    decision_type="classification"
) as ctx:
    result = agent.decide(input_data)
    ctx.set_confidence(0.85)
    ctx.set_success(True)

# Track vector memory
from agentability.memory import VectorMemoryTracker

tracker = VectorMemoryTracker(agent_id="rag_agent")
with tracker.track_retrieval(top_k=10) as ctx:
    results = vector_db.similarity_search(query, k=10)
    ctx.record_results(results)
```

## 📊 Dashboard

Run the dashboard locally:

```bash
cd dashboard
npm install
npm run dev
```

## 📚 Documentation

Visit our [documentation](https://agentability.dev/docs) for:
- Getting Started Guide
- API Reference
- Best Practices
- Production Deployment

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🌟 Star Us!

If you find Agentability useful, please star the repo!
'''

write_file(BASE_DIR / "README.md", README)

print("\\n✅ All core SDK files created successfully!")
print("\\nNext steps:")
print("1. Review generated files")
print("2. Run tests")
print("3. Build dashboard")
print("4. Deploy platform")
