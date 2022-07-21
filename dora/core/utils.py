import logging
from typing import Tuple

import sib_api_v3_sdk
from django.conf import settings
from django.utils.text import Truncator
from sib_api_v3_sdk.rest import ApiException as SibApiException

logger = logging.getLogger(__name__)

TRUTHY_VALUES = ("1", 1, "True", "true", "t", "T", True)
FALSY_VALUES = ("0", 0, "False", "false", "f", "F", False)


def normalize_description(desc: str, limit: int) -> Tuple[str, str]:
    if len(desc) < limit:
        return desc, ""
    else:
        return Truncator(desc).chars(limit), desc


def normalize_phone_number(phone: str) -> str:
    return "".join([c for c in phone if c.isdigit()])[:10]


def code_insee_to_code_dept(code_insee):
    return code_insee[:3] if code_insee.startswith("97") else code_insee[:2]


def add_to_sib(user):
    if settings.SIB_ACTIVE:
        # Configure API key authorization: api-key
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.SIB_API_KEY

        # create an instance of the API class
        api_instance = sib_api_v3_sdk.ContactsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        create_contact = sib_api_v3_sdk.CreateContact(
            email=user.email,
            attributes={
                "PRENOM": user.first_name,
                "NOM": user.last_name,
                "OPT_IN": user.newsletter,
            },
            list_ids=[int(settings.SIB_ONBOARDING_LIST)],
            update_enabled=False,
        )

        try:
            # Create a contact
            api_response = api_instance.create_contact(create_contact)
            logger.info("User %s added to SiB: %s", user.pk, api_response)
        except SibApiException as e:
            logger.exception(e)
