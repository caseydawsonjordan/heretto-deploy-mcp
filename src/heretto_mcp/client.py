import os
from typing import Any, Dict, Optional

import requests


class HerettoDeployAPI:
    """Simple client for the Heretto Deploy API."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        # Allow base URL to be set via env var
        self.base_url = (
            base_url or 
            os.getenv("HERETTO_API_BASE_URL") or 
            "https://deploy.heretto.com/v3"
        ).rstrip("/")
        self.token = token or os.getenv("HERETTO_DEPLOY_TOKEN")

    def _headers(self) -> Dict[str, str]:
        headers = {}
        if self.token:
            headers["X-Deploy-API-Auth"] = self.token
        return headers

    def search(self, organization_id: str, deployment_id: str, query: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/org/{organization_id}/deployments/{deployment_id}/search"
        payload = {"queryString": query}
        payload.update(kwargs)
        response = requests.post(url, json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_deployment(self, organization_id: str, deployment_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/org/{organization_id}/deployments/{deployment_id}"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_structure(self, organization_id: str, deployment_id: str, **params: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/org/{organization_id}/deployments/{deployment_id}/structure"
        response = requests.get(url, params=params, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_html_strings(self, organization_id: str, deployment_id: str, locale: str = "en") -> Dict[str, Any]:
        url = f"{self.base_url}/org/{organization_id}/deployments/{deployment_id}/html-strings"
        params = {"locale": locale}
        response = requests.get(url, params=params, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_content(self, organization_id: str, deployment_id: str, **params: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/org/{organization_id}/deployments/{deployment_id}/content"
        response = requests.get(url, params=params, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get_open_api_specification(
        self, organization_id: str, deployment_id: str, specification_id: str
    ) -> str:
        url = (
            f"{self.base_url}/org/{organization_id}/deployments/{deployment_id}/api-specification/{specification_id}"
        )
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.text