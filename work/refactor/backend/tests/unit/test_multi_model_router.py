from src.models.task import TaskType
from src.orchestrator.multi_model_router import ModelRole, MultiModelRouter


def test_route_task_primary_roles():
    router = MultiModelRouter(show_model_names=False)

    mapping = router.task_to_role_map

    for task, roles in mapping.items():
        cfg = router.route_task(task)
        assert cfg.role == roles[0]


def test_route_task_premium_ux_for_general_and_docs():
    router = MultiModelRouter(show_model_names=False)

    cfg_general = router.route_task(TaskType.GENERAL, use_premium_ux=True)
    assert cfg_general.role in (
        ModelRole.UX_PREMIUM,
        router.task_to_role_map[TaskType.GENERAL][0],
    )

    cfg_docs = router.route_task(TaskType.DOCUMENTATION, use_premium_ux=True)
    assert cfg_docs.role in (
        ModelRole.UX_PREMIUM,
        router.task_to_role_map[TaskType.DOCUMENTATION][0],
    )


def test_fallback_chain_contains_primary_and_alternates():
    router = MultiModelRouter(show_model_names=False)

    chain = router.get_fallback_chain(ModelRole.CODE_ENGINE)
    assert len(chain) >= 2
    assert chain[0].role == ModelRole.CODE_ENGINE


def test_model_info_contains_expected_roles():
    router = MultiModelRouter(show_model_names=False)
    info = router.get_model_info()
    # Check a few known roles
    for role in ["system1_fast", "code_engine", "ux_premium", "ux_light", "safety"]:
        assert role in info
