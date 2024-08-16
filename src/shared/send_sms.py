import httpx
import logging
from starlette.background import BackgroundTasks

from src.config import sms_config


logging.basicConfig(format="%(message)s", level=logging.INFO)
_log = logging.getLogger(__name__)


class SendSMSHandler:

    def __init__(self, url: str, username: str, token: str, sender: str):
        self._url = url
        self._token = token
        self._sender = sender
        self._username = username

    async def send_sms(self, recipient: str, message: str):

        async with httpx.AsyncClient() as client:
            payload = {
                "Username": self._username,
                "Token": self._token,
                "Dest": recipient,
                "Sms": message,
                "Sender": self._sender,
            }
            response = await client.post(self._url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                _log.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
                raise

            return response.text

    def send_sms_background(self, background_task: BackgroundTasks, recipient: str, message: str):
        background_task.add_task(self.send_sms, recipient, message)
        _log.info("Email scheduled to be sent in the background.")


def sms_sender_handler() -> SendSMSHandler:
    return SendSMSHandler(
        url=sms_config.SMS_ENDPOINT,
        username=sms_config.SMS_USERNAME,
        token=sms_config.SMS_TOKEN,
        sender=sms_config.SMS_SENDER,
    )
