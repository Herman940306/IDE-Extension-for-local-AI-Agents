"""
Meta-Controller for dynamic agent orchestration
Project Creator: Herman Swanepoel
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

import networkx as nx

logger = logging.getLogger(__name__)


class AgentNode(str, Enum):
    """Agent nodes in the reasoning graph"""

    PLANNER = "Planner"
    REASONER = "Reasoner"
    VERIFIER = "Verifier"
    AGGREGATOR = "Aggregator"


class MetaController:
    """
    Meta-controller for dynamic agent orchestration using graph-based routing.

    Supervises inter-agent coordination through a reasoning graph that adapts
    based on task complexity and performance metrics.
    """

    def __init__(self) -> None:
        """Initialize meta-controller with default graph topology"""
        self.graph = nx.DiGraph()
        self.performance_history: List[Dict[str, Any]] = []
        self._build_default_graph()
        logger.info("MetaController initialized with default graph")

    def _build_default_graph(self) -> None:
        """Build default reasoning graph topology"""
        # Default edges with initial weights
        edges = [
            (AgentNode.PLANNER, AgentNode.REASONER, {"weight": 1.0}),
            (AgentNode.REASONER, AgentNode.VERIFIER, {"weight": 1.0}),
            (AgentNode.VERIFIER, AgentNode.AGGREGATOR, {"weight": 1.0}),
            # Shortcut for simple tasks
            (AgentNode.REASONER, AgentNode.AGGREGATOR, {"weight": 1.5}),
        ]

        self.graph.add_edges_from(edges)

        # Add node attributes
        for node in AgentNode:
            self.graph.nodes[node]["executions"] = 0
            self.graph.nodes[node]["total_latency"] = 0.0
            self.graph.nodes[node]["success_count"] = 0

    def route(
        self,
        task_type: str,
        complexity: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Determine execution path based on task characteristics.

        Args:
            task_type: Type of task (refactor, explain, generate, etc.)
            complexity: Complexity score (0.0 to 1.0)
            context: Additional context for routing decision

        Returns:
            List of agent names in execution order
        """
        logger.info(f"Routing task: type={task_type}, complexity={complexity:.2f}")

        # Simple tasks: skip verifier
        if complexity < 0.3:
            path = [AgentNode.REASONER.value, AgentNode.AGGREGATOR.value]
            logger.info(f"Simple task route: {' -> '.join(path)}")
            return path

        # Complex tasks: full pipeline
        try:
            # For complex tasks, ensure Verifier is included in the path
            if complexity >= 0.5:
                # Force full path with verification
                path = [
                    AgentNode.PLANNER.value,
                    AgentNode.REASONER.value,
                    AgentNode.VERIFIER.value,
                    AgentNode.AGGREGATOR.value,
                ]
                logger.info(f"Complex task route (with verification): {' -> '.join(path)}")
                return path

            # Medium complexity: use graph-based routing
            path = nx.shortest_path(
                self.graph, AgentNode.PLANNER, AgentNode.AGGREGATOR, weight="weight"
            )
            path_str = [node.value if isinstance(node, AgentNode) else node for node in path]
            logger.info(f"Complex task route: {' -> '.join(path_str)}")
            return path_str
        except nx.NetworkXNoPath:
            # Fallback to default path
            logger.warning("No path found, using default route")
            return [
                AgentNode.PLANNER.value,
                AgentNode.REASONER.value,
                AgentNode.VERIFIER.value,
                AgentNode.AGGREGATOR.value,
            ]

    def estimate_complexity(self, code_length: int, ast_depth: int, task_type: str) -> float:
        """
        Estimate task complexity based on code characteristics.

        Args:
            code_length: Number of lines of code
            ast_depth: Depth of abstract syntax tree
            task_type: Type of task

        Returns:
            Complexity score (0.0 to 1.0)
        """
        # Base complexity from code metrics
        length_score = min(code_length / 500, 1.0)  # Normalize to 500 lines
        depth_score = min(ast_depth / 20, 1.0)  # Normalize to depth 20

        # Task type multipliers
        task_multipliers = {
            "refactor": 0.8,
            "explain": 0.5,
            "generate": 0.7,
            "debug": 0.9,
            "optimize": 0.85,
            "test": 0.6,
        }

        multiplier = task_multipliers.get(task_type.lower(), 0.7)

        # Weighted average
        complexity = (length_score * 0.4 + depth_score * 0.6) * multiplier

        logger.debug(
            f"Complexity estimation: {complexity:.2f} "
            f"(length={code_length}, depth={ast_depth}, type={task_type})"
        )

        return min(complexity, 1.0)

    def update_graph(self, performance_metrics: Dict[str, Any]) -> None:
        """
        Update graph weights based on performance metrics.

        Args:
            performance_metrics: Dict containing agent performance data
                - agent: Agent name
                - latency: Execution time in ms
                - success: Whether execution succeeded
                - confidence: Confidence score
        """
        agent = performance_metrics.get("agent")
        latency = performance_metrics.get("latency", 0)
        success = performance_metrics.get("success", False)

        if agent not in [node.value for node in AgentNode]:
            logger.warning(f"Unknown agent in metrics: {agent}")
            return

        # Update node statistics
        node = AgentNode(agent)
        self.graph.nodes[node]["executions"] += 1
        self.graph.nodes[node]["total_latency"] += latency
        if success:
            self.graph.nodes[node]["success_count"] += 1

        # Store in history
        self.performance_history.append(performance_metrics)

        # Adapt graph weights based on performance
        self._adapt_weights()

        logger.info(f"Updated graph with metrics for {agent}")

    def _adapt_weights(self) -> None:
        """Adapt edge weights based on accumulated performance data"""
        if len(self.performance_history) < 10:
            return  # Need sufficient data

        # Calculate average latency and success rate per agent
        agent_stats = {}
        for node in AgentNode:
            executions = self.graph.nodes[node]["executions"]
            if executions > 0:
                avg_latency = self.graph.nodes[node]["total_latency"] / executions
                success_rate = self.graph.nodes[node]["success_count"] / executions
                agent_stats[node] = {
                    "avg_latency": avg_latency,
                    "success_rate": success_rate,
                }

        # Adjust edge weights
        # Lower weight = preferred path
        for u, v in self.graph.edges():
            if v in agent_stats:
                stats = agent_stats[v]
                # Penalize high latency and low success rate
                latency_penalty = stats["avg_latency"] / 1000  # Normalize to seconds
                success_bonus = 2.0 - stats["success_rate"]  # Lower is better
                new_weight = latency_penalty * success_bonus
                self.graph[u][v]["weight"] = max(new_weight, 0.1)  # Minimum weight

        logger.debug("Adapted graph weights based on performance")

    def get_graph_state(self) -> Dict[str, Any]:
        """
        Get current graph state for visualization/debugging.

        Returns:
            Dict containing nodes, edges, and statistics
        """
        return {
            "nodes": [
                {
                    "name": node.value,
                    "executions": self.graph.nodes[node]["executions"],
                    "avg_latency": (
                        self.graph.nodes[node]["total_latency"]
                        / self.graph.nodes[node]["executions"]
                        if self.graph.nodes[node]["executions"] > 0
                        else 0
                    ),
                    "success_rate": (
                        self.graph.nodes[node]["success_count"]
                        / self.graph.nodes[node]["executions"]
                        if self.graph.nodes[node]["executions"] > 0
                        else 0
                    ),
                }
                for node in AgentNode
            ],
            "edges": [
                {
                    "from": u.value if isinstance(u, AgentNode) else u,
                    "to": v.value if isinstance(v, AgentNode) else v,
                    "weight": data["weight"],
                }
                for u, v, data in self.graph.edges(data=True)
            ],
            "total_executions": len(self.performance_history),
        }

    def reset_graph(self) -> None:
        """Reset graph to default state"""
        self.graph.clear()
        self.performance_history.clear()
        self._build_default_graph()
        logger.info("Graph reset to default state")
