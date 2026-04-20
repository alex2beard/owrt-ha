"""Async API client for OpenWrt ubus/rpcd."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import DEFAULT_REQUEST_TIMEOUT, DEFAULT_SESSION_TIMEOUT

_LOGGER = logging.getLogger(__name__)

_NULL_SESSION = "00000000000000000000000000000000"
_AUTH_RETRY_RESULT_CODES = {6}
_AUTH_RETRY_ERROR_CODES = {-32002}


class OpenWrtError(Exception):
    """Base exception for OpenWrt client errors."""


class OpenWrtAuthError(OpenWrtError):
    """Raised when authentication fails."""


class OpenWrtClient:
    """Simple ubus JSON-RPC client with session reuse."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        port: int,
        username: str,
        password: str,
        use_https: bool,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_https = use_https
        self._request_timeout = request_timeout
        self._session_id: str | None = None
        self._request_id = 0
        self._lock = asyncio.Lock()

    @property
    def endpoint(self) -> str:
        """Return the ubus endpoint URL."""
        scheme = "https" if self._use_https else "http"
        return f"{scheme}://{self._host}:{self._port}/ubus"

    async def async_test_connection(self) -> dict[str, Any]:
        """Validate credentials and fetch one status snapshot."""
        return await self.async_get_status()

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch the aggregated status payload from OpenWrt."""
        response = await self._async_rpc_call("openwrt.ha", "status")
        if not isinstance(response, dict):
            raise OpenWrtError("Unexpected status payload received from OpenWrt")
        return response

    async def async_restart_passwall2(self) -> dict[str, Any]:
        """Restart passwall2."""
        return await self._async_action("restart_passwall2")

    async def async_restart_dnsmasq(self) -> dict[str, Any]:
        """Restart dnsmasq."""
        return await self._async_action("restart_dnsmasq")

    async def async_reload_firewall(self) -> dict[str, Any]:
        """Reload the firewall service."""
        return await self._async_action("reload_firewall")

    async def async_restart_vds_openconnect(self) -> dict[str, Any]:
        """Restart the configured OpenConnect interface."""
        return await self._async_action("restart_vds_openconnect")

    async def async_reboot(self) -> dict[str, Any]:
        """Reboot the router."""
        return await self._async_action("reboot")

    async def async_reset_session(self) -> None:
        """Drop the cached ubus session."""
        self._session_id = None

    async def _async_action(self, method: str) -> dict[str, Any]:
        """Call one predefined control action."""
        response = await self._async_rpc_call("openwrt.ha", method)
        if not isinstance(response, dict):
            raise OpenWrtError(f"Unexpected response received for action {method}")
        return response

    async def _async_login(self) -> None:
        """Authenticate and cache a ubus session id."""
        response = await self._async_rpc_call_unlocked(
            "session",
            "login",
            {
                "username": self._username,
                "password": self._password,
                "timeout": DEFAULT_SESSION_TIMEOUT,
            },
            needs_auth=False,
            retry_auth=False,
        )

        session_id = response.get("ubus_rpc_session")
        if not isinstance(session_id, str) or not session_id:
            raise OpenWrtAuthError("OpenWrt did not return a ubus session id")

        self._session_id = session_id
        _LOGGER.debug("Established OpenWrt ubus session for %s", self._host)

    async def _async_rpc_call(
        self,
        object_name: str,
        method_name: str,
        params: Mapping[str, Any] | None = None,
        *,
        needs_auth: bool = True,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Execute a ubus JSON-RPC method call."""
        async with self._lock:
            return await self._async_rpc_call_unlocked(
                object_name,
                method_name,
                params,
                needs_auth=needs_auth,
                retry_auth=retry_auth,
            )

    async def _async_rpc_call_unlocked(
        self,
        object_name: str,
        method_name: str,
        params: Mapping[str, Any] | None = None,
        *,
        needs_auth: bool = True,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Execute a ubus JSON-RPC call while the caller holds the lock."""
        if needs_auth and not self._session_id:
            await self._async_login()

        session_id = self._session_id if needs_auth else _NULL_SESSION
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "call",
            "params": [
                session_id,
                object_name,
                method_name,
                dict(params or {}),
            ],
        }

        response = await self._async_post(payload)

        error = response.get("error")
        if isinstance(error, dict):
            error_code = error.get("code")
            error_message = error.get("message", "Unknown RPC error")

            if retry_auth and needs_auth and error_code in _AUTH_RETRY_ERROR_CODES:
                self._session_id = None
                await self._async_login()
                return await self._async_rpc_call_unlocked(
                    object_name,
                    method_name,
                    params,
                    needs_auth=needs_auth,
                    retry_auth=False,
                )

            if not needs_auth or method_name == "login":
                raise OpenWrtAuthError(str(error_message))

            raise OpenWrtError(str(error_message))

        result = response.get("result")
        if not isinstance(result, list) or not result:
            raise OpenWrtError("Malformed ubus response received from OpenWrt")

        status_code = result[0]
        if status_code != 0:
            if retry_auth and needs_auth and status_code in _AUTH_RETRY_RESULT_CODES:
                self._session_id = None
                await self._async_login()
                return await self._async_rpc_call_unlocked(
                    object_name,
                    method_name,
                    params,
                    needs_auth=needs_auth,
                    retry_auth=False,
                )

            if not needs_auth or method_name == "login":
                raise OpenWrtAuthError(
                    f"OpenWrt rejected authentication with code {status_code}"
                )

            raise OpenWrtError(
                f"OpenWrt RPC call {object_name}.{method_name} failed with code "
                f"{status_code}"
            )

        payload_data = result[1] if len(result) > 1 else {}
        if not isinstance(payload_data, dict):
            raise OpenWrtError("Unexpected ubus payload type received from OpenWrt")

        return payload_data

    async def _async_post(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Send the raw HTTP POST request to `/ubus`."""
        try:
            response = await self._session.post(
                self.endpoint,
                json=payload,
                timeout=self._request_timeout,
            )
            response.raise_for_status()
            data = await response.json(content_type=None)
        except ClientResponseError as err:
            raise OpenWrtError(
                f"HTTP {err.status} returned by OpenWrt endpoint {self.endpoint}"
            ) from err
        except (ClientError, TimeoutError, asyncio.TimeoutError) as err:
            raise OpenWrtError(
                f"Failed to connect to OpenWrt endpoint {self.endpoint}"
            ) from err
        except ValueError as err:
            raise OpenWrtError("OpenWrt returned invalid JSON") from err

        if not isinstance(data, dict):
            raise OpenWrtError("OpenWrt returned an unexpected HTTP payload")

        return data

    def _next_request_id(self) -> int:
        """Return the next JSON-RPC request id."""
        self._request_id += 1
        return self._request_id
