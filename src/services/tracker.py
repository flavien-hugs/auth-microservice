from datetime import datetime, timedelta, UTC

from beanie import PydanticObjectId
from fastapi import BackgroundTasks, Request
from user_agents import parse

from src.models import LoginLog
from src.shared.scripts.utils import make_request


class TrackingUser:

    def __init__(self):
        self.ip_base_url = "https://api64.ipify.org?format=json"

    async def __call__(self, request: Request, user_id: PydanticObjectId):

        response = make_request(method="get", url=self.ip_base_url)
        data = response.json() if response.is_success else {}
        ip_address = data.get("ip", "Unknown") if data else "Unknown"

        user_agent_str = request.headers.get("User-Agent", "")
        user_agent = parse(user_agent_str)
        if not user_agent:
            return

        last_24_hours = datetime.now(tz=UTC) - timedelta(hours=24)
        if await LoginLog.find_one(
            {
                "user_id": user_id,
                "ip_address": ip_address,
                "device": user_agent.get_device(),
                "os": user_agent.get_os(),
                "browser": user_agent.get_browser(),
                "created_at": {"$gte": last_24_hours},
            }
        ).exists():
            return

        login_log = LoginLog(
            user_id=user_id,
            ip_address=ip_address,
            device=user_agent.get_device(),
            os=user_agent.get_os(),
            browser=user_agent.get_browser(),
            is_tablet=user_agent.is_tablet,
            is_mobile=user_agent.is_mobile,
            is_pc=user_agent.is_pc,
            is_bot=user_agent.is_bot,
            is_touch_capable=user_agent.is_touch_capable,
            is_email_client=user_agent.is_email_client,
        )
        await login_log.create()

    async def insert_log(self, task: BackgroundTasks, request: Request, user_id: PydanticObjectId):
        """
        Insère un log d'utilisateur en arrière-plan en utilisant les tâches de fond.
        """
        task.add_task(self.__call__, request=request, user_id=user_id)


tracking = TrackingUser()
