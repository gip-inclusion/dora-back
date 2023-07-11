import logging
from typing import Optional

import furl
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def log_and_raise(resp: requests.Response, *args, **kwargs):
    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        logger.error(resp.json())
        raise err


def di_client_factory():
    return DataInclusionClient(
        base_url=settings.DATA_INCLUSION_URL,
        token=settings.DATA_INCLUSION_STREAM_API_KEY,
    )


class DataInclusionClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = furl.furl(base_url)
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.session.hooks["response"] = [log_and_raise]

    def _get_pages(self, url: furl.furl):
        page = 1
        data = []

        while True:
            next_url = url.copy().add({"page": page})
            response = self.session.get(next_url)
            response_data = response.json()
            data += response_data["items"]

            if len(response_data["items"]) > 0:
                page += 1
            else:
                return data

    def list_services(self, source: Optional[str] = None) -> Optional[list[dict]]:
        url = self.base_url.copy()
        url = url / "services"

        if source is not None:
            url.args["source"] = source

        try:
            return self._get_pages(url)
        except requests.HTTPError:
            return None

    def retrieve_service(self, source: str, id: str) -> Optional[dict]:
        url = self.base_url.copy()
        url = url / "services" / source / id
        response = self.session.get(url)

        try:
            return response.json()
        except requests.HTTPError:
            return None

    def search_services(
        self,
        sources: Optional[list[str]] = None,
        code_insee: Optional[str] = None,
        thematiques: Optional[list[str]] = None,
        types: Optional[list[str]] = None,
        frais: Optional[list[str]] = None,
    ) -> Optional[list[dict]]:
        url = self.base_url.copy()
        url = url / "search/services"

        if sources is not None:
            url.args["sources"] = sources

        if code_insee is not None:
            url.args["code_insee"] = code_insee

        if thematiques is not None:
            url.args["thematiques"] = thematiques

        if types is not None:
            url.args["types"] = types

        if frais is not None:
            url.args["frais"] = frais

        try:
            return self._get_pages(url)
        except requests.HTTPError:
            return None
