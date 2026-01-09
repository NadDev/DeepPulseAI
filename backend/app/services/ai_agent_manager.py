"""
AI Agent Manager - Per-User AI Agent Instances
Manages multiple AI Agent instances, one per user
"""
import logging
from typing import Dict, Optional
from app.services.ai_agent import AITradingAgent
from app.services.ai_bot_controller import AIBotController
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


class AIAgentManager:
    """Manages AI Agent and Bot Controller instances per user"""
    
    def __init__(self):
        self.user_agents: Dict[str, AITradingAgent] = {}
        self.user_controllers: Dict[str, AIBotController] = {}
    
    async def get_or_create_agent(
        self, 
        user_id: str, 
        api_key: str, 
        model: str = "deepseek-chat"
    ) -> AITradingAgent:
        """Get existing AI Agent for user or create new one"""
        
        if user_id in self.user_agents:
            return self.user_agents[user_id]
        
        # Create new AI Agent for this user
        agent = AITradingAgent(
            api_key=api_key,
            model=model,
            db_session_factory=SessionLocal,
            user_id=user_id
        )
        
        self.user_agents[user_id] = agent
        logger.info(f"✅ Created AI Agent for user {user_id}")
        
        return agent
    
    async def get_or_create_controller(
        self,
        user_id: str,
        bot_engine=None
    ) -> AIBotController:
        """Get existing Bot Controller for user or create new one"""
        
        if user_id in self.user_controllers:
            return self.user_controllers[user_id]
        
        # Create new Bot Controller for this user
        controller = AIBotController(
            db_session_factory=SessionLocal,
            bot_engine=bot_engine,
            user_id=user_id
        )
        
        # Link AI Agent if exists
        if user_id in self.user_agents:
            controller.set_ai_agent(self.user_agents[user_id])
        
        self.user_controllers[user_id] = controller
        logger.info(f"✅ Created Bot Controller for user {user_id}")
        
        return controller
    
    async def start_agent(self, user_id: str, mode: str = "trading") -> bool:
        """Start AI Agent for user"""
        if user_id not in self.user_agents:
            logger.error(f"❌ No AI Agent found for user {user_id}")
            return False
        
        agent = self.user_agents[user_id]
        agent.mode = mode
        await agent.start()
        logger.info(f"🚀 Started AI Agent for user {user_id} in {mode} mode")
        return True
    
    async def stop_agent(self, user_id: str) -> bool:
        """Stop AI Agent for user"""
        if user_id not in self.user_agents:
            return False
        
        agent = self.user_agents[user_id]
        await agent.stop()
        logger.info(f"🛑 Stopped AI Agent for user {user_id}")
        return True
    
    async def start_controller(self, user_id: str, mode: str = "paper") -> bool:
        """Start Bot Controller for user"""
        if user_id not in self.user_controllers:
            logger.error(f"❌ No Bot Controller found for user {user_id}")
            return False
        
        controller = self.user_controllers[user_id]
        controller.mode = mode
        await controller.start()
        logger.info(f"🚀 Started Bot Controller for user {user_id} in {mode} mode")
        return True
    
    async def stop_controller(self, user_id: str) -> bool:
        """Stop Bot Controller for user"""
        if user_id not in self.user_controllers:
            return False
        
        controller = self.user_controllers[user_id]
        await controller.stop()
        logger.info(f"🛑 Stopped Bot Controller for user {user_id}")
        return True
    
    def get_agent_status(self, user_id: str) -> dict:
        """Get AI Agent status for user"""
        if user_id not in self.user_agents:
            return {"exists": False, "running": False}
        
        agent = self.user_agents[user_id]
        return {
            "exists": True,
            "running": agent._running,
            "enabled": agent.enabled,
            "mode": agent.mode
        }
    
    def get_controller_status(self, user_id: str) -> dict:
        """Get Bot Controller status for user"""
        if user_id not in self.user_controllers:
            return {"exists": False, "running": False}
        
        controller = self.user_controllers[user_id]
        return {
            "exists": True,
            "running": controller._running,
            "enabled": controller.enabled,
            "mode": controller.mode
        }


# Global instance
ai_agent_manager = AIAgentManager()
