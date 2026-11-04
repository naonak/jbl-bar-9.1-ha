"""Config flow: the bar's IP address (and remote port)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JblBarClient, JblBarError, JblBarForbidden, normalize_host
from .const import DOMAIN, SUPPORTED_MODEL


class JblBarConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            host = normalize_host(user_input[CONF_HOST])
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            client = JblBarClient(async_get_clientsession(self.hass), host)
            try:
                state = await client.get_state()
                model = await client.get_model()
            except JblBarForbidden:
                errors["base"] = "forbidden"
            except JblBarError:
                errors["base"] = "cannot_connect"
            else:
                if "power" not in state or "csrf" not in state:
                    errors["base"] = "not_remote"
                elif model not in (None, SUPPORTED_MODEL):
                    # Same toolkit server, another bar: its state and actions differ.
                    errors["base"] = "unsupported_model"
                    placeholders["model"] = model
                else:
                    return self.async_create_entry(title="JBL Bar 9.1", data={CONF_HOST: host})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str}),
            errors=errors,
            description_placeholders=placeholders,
        )
