"""
Test DI Container initialization
Check if all services are properly wired

Project Creator: Herman Swanepoel
"""

from backend.src.core.container import Container


def test_container():
    """Test that DI container properly initializes all services"""
    print("🔧 Testing DI Container Initialization...")
    print()

    container = Container()
    container.config.from_yaml("backend/src/config.yaml")
    container.wire(modules=["backend.src.api.router_endpoints"])

    print("1. Task Orchestrator:")
    task_orch = container.task_orchestrator()
    print(f"   - Type: {type(task_orch).__name__}")
    print(f"   - Has LLM Manager: {task_orch.llm_manager is not None}")
    print(f"   - Has Router: {task_orch.router is not None}")
    print(f"   - Has Safety Layer: {task_orch.safety_layer is not None}")
    print(f"   - Has Output Composer: {task_orch.output_composer is not None}")
    print(f"   - Has Context Engine: {task_orch.context_engine is not None}")
    print(f"   - Has Metrics Service: {task_orch.metrics_service is not None}")
    print()

    print("2. Reasoner Engine:")
    print(f"   - Has LLM Manager: {task_orch._reasoner.llm_manager is not None}")
    print(f"   - Has Router: {task_orch._reasoner.router is not None}")
    print()

    print("3. LLM Manager:")
    if task_orch.llm_manager:
        print(f"   - Provider: {task_orch.llm_manager.provider}")
        print(f"   - Model: {task_orch.llm_manager.model}")
        print(f"   - Base URL: {task_orch.llm_manager.base_url}")
        print(f"   - Allow Cloud: {task_orch.llm_manager.allow_cloud}")
    else:
        print("   ❌ LLM Manager is None!")
    print()

    print("4. Multi-Model Router:")
    if task_orch.router:
        from backend.src.models.task import TaskType

        model = task_orch.router.route_task(TaskType.CODE_GENERATION)
        print(f"   - Code Generation Model: {model.name}")
        print(f"   - Model Role: {model.role.value}")
    print()


if __name__ == "__main__":
    test_container()
