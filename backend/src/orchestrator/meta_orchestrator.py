"""
Meta-orchestrator for intelligent task routing and agent coordination
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import time

from models import Task, TaskType, AgentResponse, Suggestion
from adapters.base_adapter import AgentAdapter
from services.llm_manager import LLMManager
from services.context_manager import ContextManager
from services.semantic_search import SemanticSearchService

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class AgentHealth:
    """Track agent health and performance"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.status = AgentStatus.IDLE
        self.success_count = 0
        self.failure_count = 0
        self.total_latency = 0.0
        self.request_count = 0
        self.last_used = 0.0
        self.consecutive_failures = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0
    
    @property
    def average_latency(self) -> float:
        """Calculate average latency"""
        return self.total_latency / self.request_count if self.request_count > 0 else 0.0
    
    @property
    def is_healthy(self) -> bool:
        """Check if agent is healthy"""
        return (
            self.status != AgentStatus.UNAVAILABLE and
            self.consecutive_failures < 3 and
            self.success_rate > 0.5
        )
    
    def record_success(self, latency: float):
        """Record successful execution"""
        self.success_count += 1
        self.request_count += 1
        self.total_latency += latency
        self.consecutive_failures = 0
        self.last_used = time.time()
        self.status = AgentStatus.IDLE
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.request_count += 1
        self.consecutive_failures += 1
        self.last_used = time.time()
        
        if self.consecutive_failures >= 3:
            self.status = AgentStatus.UNAVAILABLE
        else:
            self.status = AgentStatus.IDLE


class MetaOrchestrator:
    """
    Meta-orchestrator for intelligent task routing and multi-agent coordination
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        context_manager: ContextManager,
        semantic_search: SemanticSearchService
    ):
        """
        Initialize meta-orchestrator
        
        Args:
            llm_manager: LLM manager instance
            context_manager: Context manager instance
            semantic_search: Semantic search service
        """
        self.llm_manager = llm_manager
        self.context_manager = context_manager
        self.semantic_search = semantic_search
        
        # Agent registry
        self.agents: Dict[str, AgentAdapter] = {}
        self.agent_health: Dict[str, AgentHealth] = {}
        
        # Task routing rules
        self.routing_rules = self._initialize_routing_rules()
        
        # Execution tracking
        self.active_tasks: Set[str] = set()
        
        logger.info("✓ MetaOrchestrator initialized")
    
    def _initialize_routing_rules(self) -> Dict[TaskType, List[str]]:
        """Initialize task type to agent mapping"""
        return {
            TaskType.REFACTOR: ["refactor_agent"],
            TaskType.DOCUMENTATION: ["doc_agent"],
            TaskType.BUG_FIX: ["bug_agent"],
            TaskType.TEST_GENERATION: ["test_agent"],
            TaskType.CODE_REVIEW: ["bug_agent", "refactor_agent"],
            TaskType.RESEARCH: ["research_agent"],
            TaskType.GENERAL: ["refactor_agent"]  # Fallback
        }
    
    def register_agent(self, agent_name: str, agent: AgentAdapter):
        """
        Register an agent with the orchestrator
        
        Args:
            agent_name: Unique agent name
            agent: Agent adapter instance
        """
        self.agents[agent_name] = agent
        self.agent_health[agent_name] = AgentHealth(agent_name)
        logger.info(f"✓ Registered agent: {agent_name}")
    
    def unregister_agent(self, agent_name: str):
        """
        Unregister an agent
        
        Args:
            agent_name: Agent name to unregister
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            del self.agent_health[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")
    
    async def route_task(self, task: Task) -> AgentResponse:
        """
        Route task to appropriate agent(s) and return response
        
        Args:
            task: Task to route
            
        Returns:
            AgentResponse with suggestions
        """
        task_id = task.id or f"task_{int(time.time() * 1000)}"
        self.active_tasks.add(task_id)
        
        try:
            # 1. Determine which agents should handle this task
            selected_agents = await self._select_agents(task)
            
            if not selected_agents:
                logger.warning(f"No agents available for task type: {task.type}")
                return self._create_fallback_response(task)
            
            # 2. Execute task with selected agents
            if len(selected_agents) == 1:
                # Single agent execution
                response = await self._execute_single_agent(task, selected_agents[0])
            else:
                # Multi-agent execution with aggregation
                response = await self._execute_multi_agent(task, selected_agents)
            
            return response
            
        except Exception as e:
            logger.error(f"Task routing failed: {e}")
            return self._create_error_response(task, str(e))
        
        finally:
            self.active_tasks.discard(task_id)
    
    async def _select_agents(self, task: Task) -> List[str]:
        """
        Select appropriate agents for task using intent classification
        
        Args:
            task: Task to analyze
            
        Returns:
            List of agent names
        """
        # Get candidate agents based on task type
        candidates = self.routing_rules.get(task.type, [])
        
        # Filter by health status
        healthy_agents = [
            agent for agent in candidates
            if agent in self.agents and self.agent_health[agent].is_healthy
        ]
        
        if not healthy_agents:
            # Try fallback agents
            healthy_agents = [
                agent for agent in self.agents.keys()
                if self.agent_health[agent].is_healthy
            ]
        
        # Rank by performance
        healthy_agents.sort(
            key=lambda a: (
                self.agent_health[a].success_rate,
                -self.agent_health[a].average_latency
            ),
            reverse=True
        )
        
        return healthy_agents[:2]  # Max 2 agents for multi-agent tasks
    
    async def _execute_single_agent(
        self,
        task: Task,
        agent_name: str
    ) -> AgentResponse:
        """
        Execute task with single agent
        
        Args:
            task: Task to execute
            agent_name: Agent to use
            
        Returns:
            AgentResponse
        """
        agent = self.agents[agent_name]
        health = self.agent_health[agent_name]
        
        health.status = AgentStatus.BUSY
        start_time = time.time()
        
        try:
            # Execute task
            response = await agent.execute_task(task)
            
            # Record success
            latency = time.time() - start_time
            health.record_success(latency)
            
            logger.info(f"✓ Task completed by {agent_name} in {latency:.2f}s")
            return response
            
        except Exception as e:
            # Record failure
            health.record_failure()
            logger.error(f"Agent {agent_name} failed: {e}")
            
            # Try fallback
            return await self._try_fallback(task, agent_name)
    
    async def _execute_multi_agent(
        self,
        task: Task,
        agent_names: List[str]
    ) -> AgentResponse:
        """
        Execute task with multiple agents and aggregate responses
        
        Args:
            task: Task to execute
            agent_names: List of agents to use
            
        Returns:
            Aggregated AgentResponse
        """
        # Execute agents in parallel
        tasks_list = [
            self._execute_single_agent(task, agent_name)
            for agent_name in agent_names
        ]
        
        responses = await asyncio.gather(*tasks_list, return_exceptions=True)
        
        # Filter out exceptions
        valid_responses = [
            r for r in responses
            if isinstance(r, AgentResponse) and not isinstance(r, Exception)
        ]
        
        if not valid_responses:
            return self._create_fallback_response(task)
        
        # Aggregate responses
        return await self._aggregate_responses(valid_responses, task)
    
    async def _aggregate_responses(
        self,
        responses: List[AgentResponse],
        task: Task
    ) -> AgentResponse:
        """
        Aggregate multiple agent responses using consensus
        
        Args:
            responses: List of agent responses
            task: Original task
            
        Returns:
            Aggregated response
        """
        # Collect all suggestions
        all_suggestions = []
        for response in responses:
            all_suggestions.extend(response.suggestions)
        
        # Remove duplicates based on code similarity
        unique_suggestions = self._deduplicate_suggestions(all_suggestions)
        
        # Rank by confidence
        unique_suggestions.sort(key=lambda s: s.confidence, reverse=True)
        
        # Take top suggestions
        top_suggestions = unique_suggestions[:5]
        
        # Create aggregated response
        return AgentResponse(
            task_id=task.id,
            agent_name="meta_orchestrator",
            suggestions=top_suggestions,
            metadata={
                "agent_count": len(responses),
                "total_suggestions": len(all_suggestions),
                "aggregation_method": "consensus"
            }
        )
    
    def _deduplicate_suggestions(
        self,
        suggestions: List[Suggestion]
    ) -> List[Suggestion]:
        """
        Remove duplicate suggestions based on code similarity
        
        Args:
            suggestions: List of suggestions
            
        Returns:
            Deduplicated list
        """
        unique = []
        seen_codes = set()
        
        for suggestion in suggestions:
            # Use code hash for deduplication
            code_hash = hash(suggestion.code.strip())
            
            if code_hash not in seen_codes:
                seen_codes.add(code_hash)
                unique.append(suggestion)
        
        return unique
    
    async def _try_fallback(
        self,
        task: Task,
        failed_agent: str
    ) -> AgentResponse:
        """
        Try fallback agent when primary fails
        
        Args:
            task: Task to execute
            failed_agent: Agent that failed
            
        Returns:
            AgentResponse from fallback or error response
        """
        # Find alternative agents
        candidates = await self._select_agents(task)
        fallback_agents = [a for a in candidates if a != failed_agent]
        
        if fallback_agents:
            logger.info(f"Trying fallback agent: {fallback_agents[0]}")
            return await self._execute_single_agent(task, fallback_agents[0])
        
        # No fallback available
        return self._create_fallback_response(task)
    
    def _create_fallback_response(self, task: Task) -> AgentResponse:
        """
        Create basic fallback response when agents unavailable
        
        Args:
            task: Original task
            
        Returns:
            Basic AgentResponse
        """
        return AgentResponse(
            task_id=task.id,
            agent_name="fallback",
            suggestions=[
                Suggestion(
                    code="# Agent temporarily unavailable\n# Please try again",
                    description="Service temporarily unavailable",
                    confidence=0.1,
                    reasoning="No agents available to handle this request"
                )
            ],
            metadata={"fallback": True}
        )
    
    def _create_error_response(self, task: Task, error: str) -> AgentResponse:
        """
        Create error response
        
        Args:
            task: Original task
            error: Error message
            
        Returns:
            Error AgentResponse
        """
        return AgentResponse(
            task_id=task.id,
            agent_name="error",
            suggestions=[],
            metadata={"error": error}
        )
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get status of all registered agents
        
        Returns:
            Dictionary with agent status information
        """
        status = {}
        
        for agent_name, health in self.agent_health.items():
            status[agent_name] = {
                "status": health.status.value,
                "success_rate": round(health.success_rate, 3),
                "average_latency": round(health.average_latency, 3),
                "request_count": health.request_count,
                "is_healthy": health.is_healthy,
                "consecutive_failures": health.consecutive_failures
            }
        
        return status
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics
        
        Returns:
            Dictionary with orchestrator stats
        """
        return {
            "registered_agents": len(self.agents),
            "healthy_agents": sum(1 for h in self.agent_health.values() if h.is_healthy),
            "active_tasks": len(self.active_tasks),
            "total_requests": sum(h.request_count for h in self.agent_health.values()),
            "overall_success_rate": self._calculate_overall_success_rate()
        }
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all agents"""
        total_success = sum(h.success_count for h in self.agent_health.values())
        total_requests = sum(h.request_count for h in self.agent_health.values())
        
        return round(total_success / total_requests, 3) if total_requests > 0 else 1.0
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all agents
        
        Returns:
            Health check results
        """
        results = {}
        
        for agent_name, agent in self.agents.items():
            try:
                # Simple ping test
                start = time.time()
                # Could implement agent.ping() method
                latency = time.time() - start
                
                results[agent_name] = {
                    "healthy": True,
                    "latency": round(latency * 1000, 2)  # ms
                }
            except Exception as e:
                results[agent_name] = {
                    "healthy": False,
                    "error": str(e)
                }
                self.agent_health[agent_name].status = AgentStatus.UNAVAILABLE
        
        return results
