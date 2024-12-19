from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class FilterParams(BaseModel):
    type: Optional[str] = Field(None, description="Type of the parameter")
    name: Optional[str] = Field(None, description="Name of the parameter")


class SendSmsMessage(BaseModel):
    message: str = Field(..., description="Message to send")
    phone_number: str = Field(..., description="Phone number to send message")


class SendEmailMessage(BaseModel):
    subject: Optional[str] = Field(None, description="Subject of the email")
    message: str = Field(..., description="Message to send")
    recipients: EmailStr = Field(..., description="Email recipients")
