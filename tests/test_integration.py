"""Behaviour tests against the fake remote."""
from __future__ import annotations

import asyncio

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jbl_bar_91.const import DOMAIN

MP = "media_player.jbl_bar_9_1"


async def setup(hass: HomeAssistant, remote) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=remote.host, data={CONF_HOST: remote.host}, title="JBL Bar 9.1")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def until(predicate, timeout: float = 3.0) -> bool:
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while loop.time() < end:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return predicate()


async def call(hass, domain, service, entity_id, **data):
    await hass.services.async_call(domain, service, {"entity_id": entity_id, **data}, blocking=True)


async def test_config_flow(hass: HomeAssistant, remote) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: f"http://{remote.host}/"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: remote.host}


async def test_config_flow_errors(hass: HomeAssistant, remote) -> None:
    remote.forbid_ha = True
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: remote.host})
    assert result["errors"] == {"base": "forbidden"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "127.0.0.1:9"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_entities_from_state(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    mp = hass.states.get(MP)
    assert mp.state == "playing"
    assert mp.attributes["volume_level"] == pytest.approx(10 / 32)
    assert mp.attributes["source"] == "TV"
    assert mp.attributes["media_title"] == "Song" and mp.attributes["media_artist"] == "Band"
    assert hass.states.get("select.jbl_bar_9_1_bass_level").state == "1"
    assert hass.states.get("select.jbl_bar_9_1_center_level").state == "0"
    assert hass.states.get("select.jbl_bar_9_1_atmos_height").state == "mid"
    assert hass.states.get("select.jbl_bar_9_1_front_eq_preset").state == "original"
    assert hass.states.get("switch.jbl_bar_9_1_night_mode").state == "off"
    assert hass.states.get("sensor.jbl_bar_9_1_memory_used").state == "25.0"
    assert hass.states.get("sensor.jbl_bar_9_1_sound_mode").state == "standard"
    assert hass.states.get("binary_sensor.jbl_bar_9_1_bluetooth_connected").state == "on"


async def test_volume_mute_source_power(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.log.clear()
    await call(hass, "media_player", "volume_set", MP, volume_level=13 / 32)
    assert remote.s["volume"] == 13 and remote.actions() == ["volume_up"] * 3
    remote.log.clear()
    await call(hass, "media_player", "volume_mute", MP, is_volume_muted=True)
    await call(hass, "media_player", "volume_mute", MP, is_volume_muted=True)
    assert remote.actions() == ["mute"]
    await call(hass, "media_player", "select_source", MP, source="HDMI")
    assert hass.states.get(MP).attributes["source"] == "HDMI"
    await call(hass, "media_player", "turn_off", MP)
    assert hass.states.get(MP).state == "off"
    remote.log.clear()
    await call(hass, "media_player", "turn_off", MP)
    assert remote.actions() == []


async def test_levels_step_with_readback(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.log.clear()
    await call(hass, "select", "select_option", "select.jbl_bar_9_1_bass_level", option="4")
    assert remote.s["bass"] == 3 and remote.actions() == ["bass_next"] * 3
    remote.log.clear()
    await call(hass, "select", "select_option", "select.jbl_bar_9_1_center_level", option="3")
    assert remote.s["center"] == 3 and remote.actions() == ["center_next"] * 3
    assert hass.states.get("select.jbl_bar_9_1_center_level").state == "3"


async def test_front_eq(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    await call(hass, "select", "select_option", "select.jbl_bar_9_1_front_eq_preset", option="less_bass")
    assert remote.s["eq"] == [-4, -2, 0, 0, 0]
    await call(hass, "number", "set_value", "number.jbl_bar_9_1_front_eq_8_khz", value=-2.5)
    assert remote.s["eq"] == [-4, -2, 0, 0, -2.5]
    assert hass.states.get("select.jbl_bar_9_1_front_eq_preset").state == "unknown"
    remote.log.clear()
    await call(hass, "select", "select_option", "select.jbl_bar_9_1_front_eq_preset", option="original")
    assert remote.actions() == ["eq_reset"] and remote.s["eq_on"] is False


async def test_eq_entities_exist_when_added_in_standby(hass: HomeAssistant, remote) -> None:
    remote.s["power"] = "Standby"
    entry = await setup(hass, remote)
    preset, band = "select.jbl_bar_9_1_front_eq_preset", "number.jbl_bar_9_1_front_eq_125_hz"
    assert hass.states.get(preset).state == "unavailable"
    assert hass.states.get(band).state == "unavailable"
    remote.s["power"] = "On"
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(preset).state == "original"
    assert hass.states.get(band).state == "0.0"


async def test_no_eq_entities_without_helper(hass: HomeAssistant, remote) -> None:
    remote.eq_helper = False
    await setup(hass, remote)
    assert hass.states.get("select.jbl_bar_9_1_front_eq_preset") is None
    assert hass.states.get("number.jbl_bar_9_1_front_eq_125_hz") is None


async def test_night_switch_is_idempotent(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.log.clear()
    await call(hass, "switch", "turn_on", "switch.jbl_bar_9_1_night_mode")
    await call(hass, "switch", "turn_on", "switch.jbl_bar_9_1_night_mode")
    assert remote.actions() == ["night_toggle"] and remote.s["night"] is True


async def test_refused_control_is_reported_not_retried(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.s["controls"] = ["media_play", "media_pause", "media_next"]
    await remote.notify()
    assert await until(lambda: hass.states.get(MP).attributes["supported_features"] & 32)
    remote.log.clear()
    with pytest.raises(HomeAssistantError) as err:
        await call(hass, "media_player", "media_next_track", MP)
    assert "playback control" in str(err.value) or err.value.translation_key == "refused"
    assert remote.actions() == ["media_next"]


async def test_stale_token_retried_once(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.s["csrf"] = "tok2"
    remote.log.clear()
    await call(hass, "switch", "turn_on", "switch.jbl_bar_9_1_night_mode")
    assert [e[0] for e in remote.log] == ["403", "ok"]


async def test_push_updates_and_standby_closes_stream(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    assert await until(lambda: remote.streams == 1)
    remote.s["volume"] = 20
    await remote.notify()
    assert await until(lambda: hass.states.get(MP).attributes.get("volume_level") == pytest.approx(20 / 32))
    remote.s["power"] = "Standby"
    await remote.notify()
    assert await until(lambda: hass.states.get(MP).state == "off")
    assert await until(lambda: remote.streams == 0)


async def test_unload(hass: HomeAssistant, remote) -> None:
    entry = await setup(hass, remote)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
