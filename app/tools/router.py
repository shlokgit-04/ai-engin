from app.orchestrator.enums import IntentType
from app.orchestrator.context import ExecutionContext
from app.tools.base import BaseTool
from app.tools.project_tool import ProjectTool
from app.tools.task_tool import TaskTool
from app.tools.planner_tool import PlannerTool
from app.tools.notification_tool import NotificationTool
from app.tools.dashboard_tool import DashboardTool
from app.core.logging import logger


class ToolRouter:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for tool in [
            ProjectTool(),
            TaskTool(),
            PlannerTool(),
            NotificationTool(),
            DashboardTool(),
        ]:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        for action in tool.supported_actions():
            self._tools[action] = tool
            logger.debug("Tool registered", action=action, tool=tool.name())

    def route(self, intent: IntentType) -> BaseTool:
        tool = self._tools.get(intent.value)
        if tool is None:
            msg = f"No tool registered for intent: {intent.value}"
            logger.error(msg)
            raise ValueError(msg)
        logger.info("ToolRouter selected tool", intent=intent.value, tool=tool.name())
        return tool

    def list_actions(self) -> list[str]:
        return list(self._tools.keys())
