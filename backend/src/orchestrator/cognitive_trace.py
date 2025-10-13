"""
Cognitive Trace Store for explainability and transparency
Project Creator: Herman Swanepoel
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CognitiveTrace:
    """Single cognitive trace entry"""
    trace_id: str
    timestamp: str
    agent: str
    action: str
    confidence: float
    input_hash: str
    output_hash: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class CognitiveTraceStore:
    """
    Store and manage cognitive traces for explainability.
    
    Captures reasoning metadata from each agent to ensure full
    transparency and enable debugging of AI decisions.
    """
    
    def __init__(self, path: str = "./data/trace_logs.jsonl"):
        """
        Initialize cognitive trace store.
        
        Args:
            path: Path to JSONL log file
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache: List[CognitiveTrace] = []
        self.cache_size = 100
        logger.info(f"CognitiveTraceStore initialized at {self.path}")
    
    def record(
        self,
        trace_id: str,
        agent: str,
        action: str,
        confidence: float,
        input_hash: str,
        output_hash: str,
        notes: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a cognitive trace entry.
        
        Args:
            trace_id: Unique trace identifier
            agent: Agent name
            action: Action performed
            confidence: Confidence score (0.0 to 1.0)
            input_hash: Hash of input data
            output_hash: Hash of output data
            notes: Optional notes
            metadata: Additional metadata
        """
        trace = CognitiveTrace(
            trace_id=trace_id,
            timestamp=datetime.utcnow().isoformat(),
            agent=agent,
            action=action,
            confidence=confidence,
            input_hash=input_hash,
            output_hash=output_hash,
            metadata={
                "notes": notes,
                **(metadata or {})
            }
        )
        
        # Add to cache
        self.cache.append(trace)
        if len(self.cache) >= self.cache_size:
            self._flush_cache()
        
        logger.debug(f"Recorded trace: {trace_id} from {agent}")
    
    def _flush_cache(self) -> None:
        """Flush cache to disk"""
        if not self.cache:
            return
        
        try:
            with open(self.path, "a") as f:
                for trace in self.cache:
                    f.write(json.dumps(trace.to_dict()) + "\n")
            
            logger.debug(f"Flushed {len(self.cache)} traces to disk")
            self.cache.clear()
        except Exception as e:
            logger.error(f"Failed to flush traces: {e}")
    
    def get_traces(
        self,
        agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve traces with optional filtering.
        
        Args:
            agent: Filter by agent name
            trace_id: Filter by trace ID
            limit: Maximum number of traces to return
            
        Returns:
            List of trace dictionaries
        """
        traces = []
        
        # Check cache first
        for trace in reversed(self.cache):
            if agent and trace.agent != agent:
                continue
            if trace_id and trace.trace_id != trace_id:
                continue
            traces.append(trace.to_dict())
            if len(traces) >= limit:
                return traces
        
        # Read from file if needed
        if not self.path.exists():
            return traces
        
        try:
            with open(self.path, "r") as f:
                for line in reversed(list(f)):
                    if len(traces) >= limit:
                        break
                    
                    trace_dict = json.loads(line)
                    if agent and trace_dict["agent"] != agent:
                        continue
                    if trace_id and trace_dict["trace_id"] != trace_id:
                        continue
                    traces.append(trace_dict)
        except Exception as e:
            logger.error(f"Failed to read traces: {e}")
        
        return traces[:limit]
    
    def get_trace_chain(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all traces for a specific trace ID (full reasoning chain).
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            List of traces in chronological order
        """
        traces = self.get_traces(trace_id=trace_id, limit=1000)
        # Sort by timestamp
        traces.sort(key=lambda t: t["timestamp"])
        return traces
    
    def summarize(
        self,
        traces: List[Dict[str, Any]],
        max_length: int = 500
    ) -> str:
        """
        Summarize traces into human-readable text.
        
        Args:
            traces: List of trace entries
            max_length: Maximum summary length
            
        Returns:
            Human-readable summary
        """
        if not traces:
            return "No traces to summarize"
        
        summary = f"Reasoning Chain ({len(traces)} steps):\n\n"
        
        for i, trace in enumerate(traces, 1):
            agent = trace["agent"]
            action = trace["action"]
            confidence = trace["confidence"]
            
            summary += f"{i}. {agent}: {action}\n"
            summary += f"   Confidence: {confidence:.2f}\n"
            
            # Add notes if present
            notes = trace.get("metadata", {}).get("notes", "")
            if notes:
                summary += f"   Notes: {notes}\n"
            
            summary += "\n"
            
            # Check length
            if len(summary) > max_length:
                summary = summary[:max_length] + "...\n(truncated)"
                break
        
        return summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored traces.
        
        Returns:
            Dict containing trace statistics
        """
        all_traces = self.get_traces(limit=10000)
        
        if not all_traces:
            return {
                "total_traces": 0,
                "agents": {},
                "avg_confidence": 0.0
            }
        
        # Calculate statistics
        agent_counts = {}
        total_confidence = 0.0
        
        for trace in all_traces:
            agent = trace["agent"]
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
            total_confidence += trace["confidence"]
        
        return {
            "total_traces": len(all_traces),
            "agents": agent_counts,
            "avg_confidence": total_confidence / len(all_traces),
            "cache_size": len(self.cache)
        }
    
    def clear(self, keep_file: bool = False) -> None:
        """
        Clear all traces.
        
        Args:
            keep_file: If True, keep the file but truncate it
        """
        self.cache.clear()
        
        if not keep_file and self.path.exists():
            self.path.unlink()
            logger.info("Cleared all traces and deleted file")
        elif keep_file and self.path.exists():
            self.path.write_text("")
            logger.info("Cleared all traces, file kept")
    
    def __del__(self):
        """Flush cache on deletion"""
        self._flush_cache()
