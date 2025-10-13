"""
Base adapter interface for agent frameworks
Project Creator: Herman Swanepoel
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from src.models import Task, AgentResponse, CodeContext


class Capability(str, Enum):
    """Agent capabilities"""
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    BUG_DETECTION = "bug_detection"
    SECURITY_ANALYSIS = "security_analysis"
    CODE_GENERATION = "code_generation"
    RESEARCH = "research"
    ORCHESTRATION = "orchestration"


class AgentConfig(BaseModel):
    """Configuration for an agent"""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    capabilities: List[Capability] = Field(default_factory=list, description="Agent capabilities")
    enabled: bool = Field(default=True, description="Whether agent is enabled")
    max_concurrent: int = Field(default=1, description="Maximum concurrent executions")
    timeout: int = Field(default=30, description="Execution timeout in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AgentAdapter(ABC):
    """
    Base adapter interface for agent frameworks
    
    All agent framework adapters must implement this interface to ensure
    consistent behavior across different agent systems (CrewAI, SuperAGI, AutoGPT, etc.)
    """

    # Class-level response cache shared across all adapters
    _response_cache: Optional['ResponseCache'] = None

    def __init__(self, config: AgentConfig):
        """
        Initialize the adapter with configuration
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.is_initialized = False
        
        # Initialize shared cache if not exists
        if AgentAdapter._response_cache is None:
            from src.adapters.adapter_utils import ResponseCache
            AgentAdapter._response_cache = ResponseCache(max_size=100, ttl_seconds=3600)
    
    @property
    def response_cache(self) -> 'ResponseCache':
        """Get shared response cache"""
        return AgentAdapter._response_cache

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the agent adapter
        
        This method should set up any necessary resources, connections,
        or configurations required by the agent framework.
        
        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Execute a task using the agent
        
        Args:
            task: Task to execute
            context: Code context for the task
            
        Returns:
            AgentResponse with suggestions and reasoning
            
        Raises:
            Exception: If task execution fails
        """
        pass

    @abstractmethod
    async def get_capabilities(self) -> List[Capability]:
        """
        Get the capabilities of this agent
        
        Returns:
            List of capabilities this agent supports
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the agent is healthy and ready to execute tasks
        
        Returns:
            True if agent is healthy, False otherwise
        """
        pass

    async def shutdown(self) -> None:
        """
        Shutdown the agent adapter and clean up resources
        
        Override this method if your adapter needs custom cleanup logic.
        """
        self.is_initialized = False

    def can_handle_task(self, task: Task) -> bool:
        """
        Check if this agent can handle the given task type
        
        Args:
            task: Task to check
            
        Returns:
            True if agent can handle this task type
        """
        # Map task types to capabilities
        task_capability_map = {
            "refactor": Capability.REFACTORING,
            "documentation": Capability.DOCUMENTATION,
            "test_generation": Capability.TESTING,
            "bug_detection": Capability.BUG_DETECTION,
            "security_analysis": Capability.SECURITY_ANALYSIS,
            "inline_suggestion": Capability.CODE_GENERATION,
        }
        
        required_capability = task_capability_map.get(task.type.value)
        if not required_capability:
            return False
            
        return required_capability in self.config.capabilities

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get adapter metadata
        
        Returns:
            Dictionary containing adapter metadata
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "capabilities": [cap.value for cap in self.config.capabilities],
            "enabled": self.config.enabled,
            "initialized": self.is_initialized,
            "max_concurrent": self.config.max_concurrent,
            "timeout": self.config.timeout,
        }


class AdapterRegistry:
    """Registry for managing agent adapters"""

    def __init__(self):
        self._adapters: Dict[str, AgentAdapter] = {}

    def register(self, name: str, adapter: AgentAdapter) -> None:
        """
        Register an adapter
        
        Args:
            name: Unique name for the adapter
            adapter: Adapter instance
        """
        self._adapters[name] = adapter

    def unregister(self, name: str) -> None:
        """
        Unregister an adapter
        
        Args:
            name: Name of adapter to unregister
        """
        if name in self._adapters:
            del self._adapters[name]

    def get(self, name: str) -> Optional[AgentAdapter]:
        """
        Get an adapter by name
        
        Args:
            name: Adapter name
            
        Returns:
            Adapter instance or None if not found
        """
        return self._adapters.get(name)

    def get_all(self) -> Dict[str, AgentAdapter]:
        """
        Get all registered adapters
        
        Returns:
            Dictionary of all adapters
        """
        return self._adapters.copy()

    def get_by_capability(self, capability: Capability) -> List[AgentAdapter]:
        """
        Get all adapters that support a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of adapters supporting the capability
        """
        return [
            adapter for adapter in self._adapters.values()
            if capability in adapter.config.capabilities and adapter.config.enabled
        ]

    async def initialize_all(self) -> None:
        """Initialize all registered adapters"""
        for adapter in self._adapters.values():
            if not adapter.is_initialized:
                await adapter.initialize()

    async def shutdown_all(self) -> None:
        """Shutdown all registered adapters"""
        for adapter in self._adapters.values():
            await adapter.shutdown()
