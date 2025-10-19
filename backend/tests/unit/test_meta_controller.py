"""
Unit tests for Meta-Controller
Project Creator: Herman Swanepoel
"""

from src.orchestrator.meta_controller import MetaController, AgentNode


class TestMetaController:
    """Test suite for MetaController"""

    def test_initialization(self):
        """Test meta-controller initialization"""
        controller = MetaController()
        assert controller.graph is not None
        assert len(controller.graph.nodes()) == 4  # 4 agent nodes
        assert len(controller.performance_history) == 0

    def test_simple_task_routing(self):
        """Test routing for simple tasks"""
        controller = MetaController()
        path = controller.route(task_type="refactor", complexity=0.2)

        assert len(path) == 2
        assert path == ["Reasoner", "Aggregator"]

    def test_complex_task_routing(self):
        """Test routing for complex tasks"""
        controller = MetaController()
        path = controller.route(task_type="refactor", complexity=0.8)

        assert len(path) > 2
        assert "Verifier" in path
        assert path[0] == "Planner"
        assert path[-1] == "Aggregator"

    def test_complexity_estimation(self):
        """Test complexity estimation"""
        controller = MetaController()

        # Simple code
        complexity = controller.estimate_complexity(
            code_length=50, ast_depth=5, task_type="explain"
        )
        assert 0.0 <= complexity <= 0.5

        # Complex code
        complexity = controller.estimate_complexity(
            code_length=500, ast_depth=20, task_type="refactor"
        )
        assert 0.5 <= complexity <= 1.0

    def test_performance_update(self):
        """Test performance metrics update"""
        controller = MetaController()

        metrics = {
            "agent": "Reasoner",
            "latency": 150,
            "success": True,
            "confidence": 0.9,
        }

        controller.update_graph(metrics)

        assert len(controller.performance_history) == 1
        assert controller.graph.nodes[AgentNode.REASONER]["executions"] == 1
        assert controller.graph.nodes[AgentNode.REASONER]["success_count"] == 1

    def test_graph_state(self):
        """Test graph state retrieval"""
        controller = MetaController()
        state = controller.get_graph_state()

        assert "nodes" in state
        assert "edges" in state
        assert "total_executions" in state
        assert len(state["nodes"]) == 4

    def test_graph_reset(self):
        """Test graph reset"""
        controller = MetaController()

        # Add some metrics
        controller.update_graph(
            {"agent": "Reasoner", "latency": 100, "success": True, "confidence": 0.9}
        )

        # Reset
        controller.reset_graph()

        assert len(controller.performance_history) == 0
        assert controller.graph.nodes[AgentNode.REASONER]["executions"] == 0
