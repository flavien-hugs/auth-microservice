from enum import StrEnum

from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseParamsFields
from fastapi_pagination.utils import disable_installed_extensions_check

from src.config import settings

disable_installed_extensions_check()


class SortEnum(StrEnum):
    ASC = "asc"
    DESC = "desc"


def customize_page(model):
    return CustomizedPage[Page, UseParamsFields(size=settings.DEFAULT_PAGIGNIATE_PAGE_SIZE)]
