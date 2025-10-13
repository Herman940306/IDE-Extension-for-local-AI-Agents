"""
Mode manager for offline/online mode control
Project Creator: Herman Swanepoel
"""

import logging
from typing import Dict, Any, List, Callable, Optional
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Operation mode enumeration"""
    OFFLINE = "offline"  # Local-only, maximum privacy
    ONLINE = "online"    # Cloud LLM fallback enabled


class ModeManager:
    """
    Manages offline/online mode state and enforces privacy controls
    """
    
    def __init__(self, default_mode: OperationMode = OperationMode.OFFLINE):
        """
        Initialize mode manager
        
        Args:
            default_mode: Default operation mode (offline by default)
        """
        self.current_mode = default_mode
        self.mode_change_callbacks: List[Callable[[OperationMode], None]] = []
        self.cloud_api_blocked = True if default_mode == OperationMode.OFFLINE else False
        
        # Statistics
        self.mode_changes = 0
        self.cloud_api_calls_blocked = 0
        self.cloud_api_calls_allowed = 0
        
        logger.info(f"✓ ModeManager initialized in {default_mode.value} mode")
    
    def get_current_mode(self) -> OperationMode:
        """
        Get current operation mode
        
        Returns:
            Current OperationMode
        """
        return self.current_mode
    
    def is_offline(self) -> bool:
        """Check if in offline mode"""
        return self.current_mode == OperationMode.OFFLINE
    
    def is_online(self) -> bool:
        """Check if in online mode"""
        return self.current_mode == OperationMode.ONLINE
    
    async def set_mode(self, mode: OperationMode) -> Dict[str, Any]:
        """
        Set operation mode and notify callbacks
        
        Args:
            mode: New operation mode
            
        Returns:
            Dictionary with mode change result
        """
        if mode == self.current_mode:
            logger.debug(f"Already in {mode.value} mode")
            return {
                "success": True,
                "mode": mode.value,
                "changed": False,
                "message": f"Already in {mode.value} mode"
            }
        
        old_mode = self.current_mode
        self.current_mode = mode
        self.cloud_api_blocked = (mode == OperationMode.OFFLINE)
        self.mode_changes += 1
        
        logger.info(f"Mode changed: {old_mode.value} → {mode.value}")
        
        # Notify all callbacks
        await self._notify_callbacks(mode)
        
        return {
            "success": True,
            "mode": mode.value,
            "changed": True,
            "previous_mode": old_mode.value,
            "message": f"Switched to {mode.value} mode"
        }
    
    async def switch_to_offline(self) -> Dict[str, Any]:
        """
        Switch to offline mode (local-only)
        
        Returns:
            Mode change result
        """
        return await self.set_mode(OperationMode.OFFLINE)
    
    async def switch_to_online(self) -> Dict[str, Any]:
        """
        Switch to online mode (cloud fallback enabled)
        
        Returns:
            Mode change result
        """
        return await self.set_mode(OperationMode.ONLINE)
    
    async def toggle_mode(self) -> Dict[str, Any]:
        """
        Toggle between offline and online modes
        
        Returns:
            Mode change result
        """
        new_mode = OperationMode.ONLINE if self.is_offline() else OperationMode.OFFLINE
        return await self.set_mode(new_mode)
    
    def can_use_cloud_api(self) -> bool:
        """
        Check if cloud API calls are allowed in current mode
        
        Returns:
            True if cloud API calls are allowed
        """
        return not self.cloud_api_blocked
    
    def validate_cloud_operation(self, operation_name: str) -> bool:
        """
        Validate if a cloud operation is allowed
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            True if allowed, False if blocked
        """
        if self.cloud_api_blocked:
            self.cloud_api_calls_blocked += 1
            logger.warning(f"Cloud operation blocked in offline mode: {operation_name}")
            return False
        
        self.cloud_api_calls_allowed += 1
        logger.debug(f"Cloud operation allowed: {operation_name}")
        return True
    
    def register_mode_change_callback(
        self,
        callback: Callable[[OperationMode], None]
    ) -> None:
        """
        Register callback to be notified on mode changes
        
        Args:
            callback: Function to call on mode change (receives new mode)
        """
        self.mode_change_callbacks.append(callback)
        logger.debug(f"Registered mode change callback: {callback.__name__}")
    
    def unregister_mode_change_callback(
        self,
        callback: Callable[[OperationMode], None]
    ) -> None:
        """
        Unregister mode change callback
        
        Args:
            callback: Callback to remove
        """
        if callback in self.mode_change_callbacks:
            self.mode_change_callbacks.remove(callback)
            logger.debug(f"Unregistered mode change callback: {callback.__name__}")
    
    async def _notify_callbacks(self, new_mode: OperationMode) -> None:
        """
        Notify all registered callbacks of mode change
        
        Args:
            new_mode: New operation mode
        """
        for callback in self.mode_change_callbacks:
            try:
                # Support both sync and async callbacks
                result = callback(new_mode)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Mode change callback error ({callback.__name__}): {e}")
    
    def get_mode_info(self) -> Dict[str, Any]:
        """
        Get detailed mode information
        
        Returns:
            Dictionary with mode information
        """
        return {
            "current_mode": self.current_mode.value,
            "is_offline": self.is_offline(),
            "is_online": self.is_online(),
            "cloud_api_blocked": self.cloud_api_blocked,
            "mode_changes": self.mode_changes,
            "cloud_calls_blocked": self.cloud_api_calls_blocked,
            "cloud_calls_allowed": self.cloud_api_calls_allowed,
            "registered_callbacks": len(self.mode_change_callbacks)
        }
    
    def get_privacy_status(self) -> Dict[str, Any]:
        """
        Get privacy status information
        
        Returns:
            Dictionary with privacy information
        """
        return {
            "mode": self.current_mode.value,
            "local_only": self.is_offline(),
            "cloud_enabled": self.is_online(),
            "data_leaves_device": self.is_online(),
            "privacy_level": "maximum" if self.is_offline() else "standard",
            "description": self._get_mode_description()
        }
    
    def _get_mode_description(self) -> str:
        """Get human-readable mode description"""
        if self.is_offline():
            return "All operations run locally. Maximum privacy. No data sent to cloud."
        else:
            return "Cloud LLM fallback enabled. Data may be sent to cloud providers."
    
    def reset_statistics(self) -> None:
        """Reset mode statistics"""
        self.mode_changes = 0
        self.cloud_api_calls_blocked = 0
        self.cloud_api_calls_allowed = 0
        logger.info("Mode statistics reset")
