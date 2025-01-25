from datetime import datetime, timezone

from fastapi import BackgroundTasks
from jinja2 import Environment, PackageLoader, select_autoescape

from src.config import sms_config
from src.models import User
from src.shared import otp_service, sms_service


async def send_otp(user: User, bg: BackgroundTasks):
    otp_secret = otp_service.generate_key()
    otp_code = otp_service.generate_otp_instance(otp_secret).now()
    # recipient = user.phonenumber.replace("+", "")

    new_attributes = user.attributes.copy() if user.attributes else {}
    new_attributes["otp_secret"] = otp_secret
    new_attributes["otp_created_at"] = datetime.now(timezone.utc).timestamp()

    template = template_env.get_template(name="sms_send_otp.txt")
    message = template.render(otp_code=otp_code, service_name=sms_config.SMS_SENDER)
    await sms_service.send_sms(bg, user.phonenumber, message)
    await user.set({"attributes": new_attributes})


template_loader = PackageLoader("src", "templates")
template_env = Environment(loader=template_loader, autoescape=select_autoescape(["html", "txt"]))
