#   Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License").
#   You may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""LISA SDK."""
import json
import logging
import sys
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Union

import requests
from aiohttp import ClientSession, ClientTimeout
from pydantic import BaseModel, ConfigDict, Field, field_validator
from requests import Session

from .errors import parse_error
from .types import FoundationModel, Response, StreamingResponse

logging.basicConfig(level=logging.INFO)

API_VERSION = "v1"


def on_llm_new_token(token: str) -> None:
    """Handle new tokens during streaming."""
    sys.stdout.write(token)
    sys.stdout.flush()


class Lisa(BaseModel):
    """A wrapper around the LISA REST API."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(..., description="REST API url.")
    headers: Optional[Dict[str, str]] = Field(None, description="Headers for request.")
    cookies: Optional[Dict[str, str]] = Field(None, description="Cookies for request.")
    timeout: int = Field(10, description="Timeout in minutes request.")
    verify: Optional[Union[str, bool]] = Field(None, description="Whether to verify SSL certificates.")
    async_timeout: Optional[ClientTimeout] = None  # Do not provide a default value here

    _session: Session

    @field_validator("url")
    def validate_url(cls: "Lisa", v: str) -> str:
        """Validate URL is properly formatted."""
        url = v.rstrip("/")
        if not url.endswith(API_VERSION):
            url = f"{url}/{API_VERSION}"
        return url

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._session = requests.Session()
        if self.headers:
            self._session.headers = self.headers  # type: ignore
        if self.verify is not None:
            self._session.verify = self.verify
        if self.cookies:
            self._session.cookies = self.cookies  # type: ignore

        self.async_timeout = ClientTimeout(self.timeout * 60)

    def describe_model(self, provider: str, model_name: str) -> FoundationModel:
        """Get model metadata.

        Parameters
        ----------
        provider : str
            Name of provider.

        model_name : str
            Name of model.

        Returns
        -------
        Dict[str, str]
            Model metadata.
        """
        response = self._session.get(f"{self.url}/describeModel?provider={provider}&modelName={model_name}")
        if response.status_code == 200:
            return FoundationModel.from_dict(response.json())
        else:
            raise parse_error(response.status_code, response)

    def list_models(self) -> List[FoundationModel]:
        """List all foundation models.

        Returns
        -------
        List[FoundationModel]
            List of available text generation and embedding foundation models.
        """
        response = self._session.get(f"{self.url}/listModels")
        if response.status_code == 200:
            json_models = response.json()
            models = [
                self.describe_model(provider=provider, model_name=model_name)
                for model_type, providers in json_models.items()
                for provider, model_names in providers.items()
                for model_name in model_names
            ]
        else:
            raise parse_error(response.status_code, response)
        return models

    def list_textgen_models(self) -> List[FoundationModel]:
        """List all text generation foundation models.

        Returns
        -------
        List[FoundationModel]
            List of available text generation foundation models.
        """
        response = self._session.get(f"{self.url}/listModels?modelTypes=textgen")
        if response.status_code == 200:
            json_models = response.json()
            models = [
                self.describe_model(provider=provider, model_name=model_name)
                for model_type, providers in json_models.items()
                for provider, model_names in providers.items()
                for model_name in model_names
            ]
            return models
        else:
            raise parse_error(response.status_code, response)

    def list_embedding_models(self) -> List[FoundationModel]:
        """List all embedding foundation models.

        Returns
        -------
        List[FoundationModel]
            List of available text generation foundation models.
        """
        response = self._session.get(f"{self.url}/listModels?modelTypes=embedding")
        if response.status_code == 200:
            json_models = response.json()
            models = [
                self.describe_model(provider=provider, model_name=model_name)
                for model_type, providers in json_models.items()
                for provider, model_names in providers.items()
                for model_name in model_names
            ]
            return models
        else:
            raise parse_error(response.status_code, response)

    def generate(self, prompt: str, model: FoundationModel) -> Response:
        """Generate text based on the provided prompt using a specific model.

        Parameters
        ----------
        prompt : str
            Input prompt.

        model : FoundationModel
            Foundation model for text generation.

        Returns
        -------
        Response
            Text generation response.
        """
        payload = {
            "provider": model.provider,
            "modelName": model.model_name,
            "text": prompt,
            "modelKwargs": model.model_kwargs.model_dump() if model.model_kwargs else {},
        }
        response = self._session.post(f"{self.url}/generate", json=payload)
        if response.status_code == 200:
            output = response.json()
            return Response(
                generated_text=output["generatedText"],
                generated_tokens=output["generatedTokens"],
                finish_reason=output["finishReason"],
            )
        else:
            print(response)
            raise parse_error(response.status_code, response)

    async def agenerate(
        self,
        prompt: str,
        model: FoundationModel,
    ) -> Response:
        """Generate text based on the provided prompt using a specific model.

        Parameters
        ----------
        prompt : str
            Input prompt.

        model : FoundationModel
            Foundation model for text generation.

        Returns
        -------
        Response
            Text generation response.
        """
        payload = {
            "provider": model.provider,
            "modelName": model.model_name,
            "text": prompt,
            "modelKwargs": model.model_kwargs.model_dump() if model.model_kwargs else {},
        }
        async with ClientSession(
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.async_timeout,
        ) as session:
            async with session.post(f"{self.url}/generate", json=payload, ssl=self.verify) as response:
                output = await response.json()
                if response.status == 200:
                    return Response(
                        generated_text=output["generatedText"],
                        generated_tokens=output["generatedTokens"],
                        finish_reason=output["finishReason"],
                    )
                else:
                    raise parse_error(response.status_code, response)

    def generate_stream(self, prompt: str, model: FoundationModel) -> Generator[StreamingResponse, None, None]:
        """Generate text with streaming based on the provided prompt using a specific model.

        Parameters
        ----------
        prompt : str
            Input prompt.

        model : FoundationModel
            Foundation model for text generation.

        Returns
        -------
        Generator[StreamingResponse, None, None]
            Text generation streaming response.
        """
        request = {
            "provider": model.provider,
            "modelName": model.model_name,
            "text": prompt,
            "modelKwargs": model.model_kwargs.model_dump() if model.model_kwargs else {},
        }
        response = self._session.post(f"{self.url}/generateStream", json=request)
        if response.status_code == 200:
            for resp_line in response.iter_lines():
                if resp_line == "b\n":
                    continue
                payload = resp_line.decode("utf-8")
                if payload.startswith("data:"):
                    json_payload = json.loads(payload.removeprefix("data:").rstrip("/n"))
                    if "finishReason" in json_payload:
                        yield StreamingResponse(  # nosec [B106]
                            token="",
                            finish_reason=json_payload["finishReason"],
                            generated_tokens=json_payload["generatedTokens"],
                        )
                    else:
                        yield StreamingResponse(
                            token=json_payload["token"]["text"],
                        )
        else:
            raise parse_error(response.status_code, response)

    async def agenerate_stream(
        self,
        prompt: str,
        model: FoundationModel,
    ) -> AsyncGenerator[StreamingResponse, None]:
        """Generate text with streaming based on the provided prompt using a specific model.

        Parameters
        ----------
        prompt : str
            Input prompt.

        model : FoundationModel
            Foundation model for text generation.

        Returns
        -------
        AsyncGenerator[StreamingResponse, None]
            Text generation streaming response.
        """
        request = {
            "provider": model.provider,
            "modelName": model.model_name,
            "text": prompt,
            "modelKwargs": model.model_kwargs.model_dump() if model.model_kwargs else {},
        }
        async with ClientSession(
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.async_timeout,
        ) as session:
            async with session.post(f"{self.url}/generateStream", json=request, ssl=self.verify) as response:
                if response.status != 200:
                    payload = await response.json()
                    # TODO this probably won't work
                    raise parse_error(response.status_code, response)
                async for resp_line in response.content:
                    if resp_line == "b\n":
                        continue
                    payload = resp_line.decode("utf-8")
                    if payload.startswith("data:"):
                        json_payload = json.loads(payload.removeprefix("data:").rstrip("/n"))
                        if "finishReason" in json_payload:
                            yield StreamingResponse(  # nosec [B106]
                                token="",
                                finish_reason=json_payload["finishReason"],
                                generated_tokens=json_payload["generatedTokens"],
                            )
                        else:
                            yield StreamingResponse(
                                token=json_payload["token"]["text"],
                            )

    def embed(self, texts: Union[str, List[str]], model: FoundationModel) -> List[List[float]]:
        """Generate text embeddings based on the provided prompt using a specific model.

        Parameters
        ----------
        texts : Union[str, List[str]]
            Input texts.

        model : FoundationModel
            Foundation model for text embeddings.

        Returns
        -------
        List[List[float]]
            Text embeddings as a batched response.
        """
        payload = {
            "provider": model.provider,
            "modelName": model.model_name,
            "text": texts,
            "modelKwargs": model.model_kwargs.model_dump() if model.model_kwargs else {},
        }
        response = self._session.post(f"{self.url}/embeddings", json=payload)
        if response.status_code == 200:
            output = response.json()
            return output["embeddings"]  # type: ignore
        else:
            raise parse_error(response.status_code, response)

    async def aembed(self, texts: Union[str, List[str]], model: FoundationModel) -> List[List[float]]:
        """Generate text embeddings based on the provided prompt using a specific model.

        Parameters
        ----------
        texts : Union[str, List[str]]
            Input texts.

        model : FoundationModel
            Foundation model for text embeddings.

        Returns
        -------
        List[List[float]]
            Text embeddings as a batched response.
        """
        payload = {
            "provider": model.provider,
            "modelName": model.model_name,
            "text": texts,
            "modelKwargs": model.model_kwargs.model_dump() if model.model_kwargs else {},
        }
        async with ClientSession(
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.async_timeout,
        ) as session:
            async with session.post(f"{self.url}/embeddings", json=payload, ssl=False) as response:
                if response.status != 200:
                    output = await response.json()
                    raise parse_error(response.status_code, response)

                output = await response.json()
                return output["embeddings"]  # type: ignore

    def __del__(self) -> None:
        """Close session."""
        try:
            self._session.close()
        except Exception:
            pass
