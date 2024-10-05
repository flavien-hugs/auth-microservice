import logging
from typing import Any, Dict
from urllib.parse import urlencode

import httpx
from starlette.background import BackgroundTasks

from src.config import sms_config

logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)


class SMSException(Exception):
    pass


class SendSMSHandler:

    def __init__(self):
        self._base_url = sms_config.SMS_URL
        self._sender = sms_config.SMS_SENDER
        self._sms_type = sms_config.SMS_TYPE
        self._dlr = 1

        self._headers = {"APIKEY": sms_config.SMS_API_KEY, "CLIENTID": sms_config.SMS_CLIENT_ID}

    async def __call__(self, recipient: str, message: str, *args, **kwargs) -> Dict[str, Any]:
        params = {"from": self._sender, "to": recipient, "type": self._sms_type, "message": message, "dlr": self._dlr}

        async with httpx.AsyncClient(follow_redirects=True) as client:
            url = f"{self._base_url}?{urlencode(params)}"
            response = await client.post(url, headers=self._headers, timeout=30)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SMSException(f"HTTP error '{exc}' while sending SMS") from exc
        except Exception as err:
            raise SMSException(f"Unexpected error while sending SMS to {recipient}: {str(err)}") from err

        response_data = response.json()
        if response_data.get("status") != "ACT":
            raise SMSException(f"SMS sending failed: {response_data.get('message', 'Unknown error')}")
        return response_data

    async def _send_sms_task(self, recipient: str, message: str):
        try:
            await self.__call__(recipient, message)
        except SMSException as exc:
            _log.error(f"Failed to send SMS to {recipient}: {str(exc)}")
            raise exc from exc
        except Exception as err:
            _log.error(f"Unexpected error while sending SMS to {recipient}: {str(err)}")
            raise err from err

    async def send_sms(self, background_task: BackgroundTasks, recipient: str, message: str):
        background_task.add_task(self._send_sms_task, recipient, message)
        _log.info(f"SMS scheduled to be sent to {recipient} in the background.")


def sms_sender_handler() -> SendSMSHandler:
    return SendSMSHandler()
