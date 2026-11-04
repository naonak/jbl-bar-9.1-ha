"""Behaviour tests against the fake remote."""
from __future__ import annotations

import asyncio

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
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


async def test_smart_mode_switch(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    sw = "switch.jbl_bar_9_1_smart_mode"
    assert hass.states.get(sw).state == "off"
    remote.log.clear()
    await call(hass, "switch", "turn_on", sw)
    await call(hass, "switch", "turn_on", sw)
    assert remote.actions() == ["smart"] and hass.states.get(sw).state == "on"
    await call(hass, "switch", "turn_off", sw)
    assert remote.actions() == ["smart", "standard"] and remote.mode == "Standard"


async def test_audio_sync_in_chunks(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    num = "number.jbl_bar_9_1_audio_sync"
    assert hass.states.get(num).state == "0"
    remote.log.clear()
    await call(hass, "number", "set_value", num, value=120)
    assert remote.av_sync == 120 and hass.states.get(num).state == "120"
    assert [(e[1], e[3]) for e in remote.log if e[0] == "ok"] == [("av_sync_set", 120)]
    await call(hass, "number", "set_value", num, value=100)
    assert remote.av_sync == 100


async def test_audio_sync_split_for_older_remotes(hass: HomeAssistant, remote) -> None:
    remote.av_sync_limit = 80
    await setup(hass, remote)
    remote.log.clear()
    await call(hass, "number", "set_value", "number.jbl_bar_9_1_audio_sync", value=120)
    assert remote.av_sync == 120
    assert [e[3] for e in remote.log if e[0] == "ok"] == [120, 50, 100, 120]


async def test_audio_sync_unavailable_on_bluetooth(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    await call(hass, "media_player", "select_source", MP, source="Bluetooth")
    assert hass.states.get("number.jbl_bar_9_1_audio_sync").state == "unavailable"


async def test_no_advanced_entities_on_older_remote(hass: HomeAssistant, remote) -> None:
    remote.advanced = False
    await setup(hass, remote)
    assert hass.states.get("switch.jbl_bar_9_1_smart_mode") is None
    assert hass.states.get("number.jbl_bar_9_1_audio_sync") is None
    assert hass.states.get("button.jbl_bar_9_1_standard_mode") is not None


async def test_standard_button_replaced_by_smart_switch(hass: HomeAssistant, remote) -> None:
    remote.advanced = False
    entry = await setup(hass, remote)
    assert hass.states.get("button.jbl_bar_9_1_standard_mode") is not None
    # The bar gets the advanced remote: after a reload the old button is gone.
    remote.advanced = True
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("button.jbl_bar_9_1_standard_mode") is None
    assert er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{remote.host}_standard_mode") is None
    assert hass.states.get("switch.jbl_bar_9_1_smart_mode") is not None


async def test_setup_controls(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    calibrate, sub = "button.jbl_bar_9_1_calibrate_surround", "button.jbl_bar_9_1_pair_subwoofer"
    assert hass.states.get("sensor.jbl_bar_9_1_audio_format").state == "DOLBY SURROUND DD+"
    assert hass.states.get("sensor.jbl_bar_9_1_calibration").state == "Idle"
    assert hass.states.get(calibrate).state != "unavailable"
    remote.log.clear()
    await call(hass, "button", "press", calibrate)
    assert await until(lambda: hass.states.get("sensor.jbl_bar_9_1_calibration").state == "Step 1 starting")
    assert remote.actions() == ["calibrate"]
    # The bar is measuring: both setup buttons wait.
    assert hass.states.get(calibrate).state == "unavailable" and hass.states.get(sub).state == "unavailable"
    remote.setup = {"sub_pairing": False, "calibration": "Step 1 done"}
    await remote.notify()
    assert await until(lambda: hass.states.get(calibrate).state != "unavailable")
    await call(hass, "button", "press", sub)
    assert await until(lambda: hass.states.get("sensor.jbl_bar_9_1_subwoofer").state == "Pairing")
    assert remote.actions() == ["calibrate", "sub_pair"] and hass.states.get(sub).state == "unavailable"


async def test_calibrate_needs_undocked_rears(hass: HomeAssistant, remote) -> None:
    remote.rear_docked = True
    await setup(hass, remote)
    assert hass.states.get("button.jbl_bar_9_1_calibrate_surround").state == "unavailable"
    assert hass.states.get("button.jbl_bar_9_1_pair_subwoofer").state != "unavailable"


async def test_no_setup_entities_on_older_remote(hass: HomeAssistant, remote) -> None:
    remote.setup = None
    await setup(hass, remote)
    for entity_id in ("button.jbl_bar_9_1_calibrate_surround", "button.jbl_bar_9_1_pair_subwoofer",
                      "sensor.jbl_bar_9_1_audio_format", "sensor.jbl_bar_9_1_calibration"):
        assert hass.states.get(entity_id) is None


async def test_waits_for_a_control_running_elsewhere(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.busy_other = "av_sync_set"
    await remote.notify()
    assert await until(lambda: hass.states.get("binary_sensor.jbl_bar_9_1_command_running").state == "on")
    assert hass.states.get("binary_sensor.jbl_bar_9_1_command_running").attributes["source"] == "remote"
    remote.log.clear()

    async def finish() -> None:
        await asyncio.sleep(0.6)
        remote.busy_other = None
        await remote.notify()

    task = hass.async_create_task(finish())
    await call(hass, "media_player", "volume_up", MP)
    await task
    assert remote.s["volume"] == 11 and remote.actions() == ["volume_up"]
    assert await until(lambda: hass.states.get("binary_sensor.jbl_bar_9_1_command_running").state == "off")


async def test_resends_after_another_control_is_running(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    remote.log.clear()
    # The remote refuses before acting; the state does not report busy (older remote).
    real_state = remote.state

    def refuse_once() -> dict:
        return real_state()

    remote.busy_other = "smart"
    remote.state = lambda: {**refuse_once(), "control": {"busy": False}}

    async def finish() -> None:
        await asyncio.sleep(0.3)
        remote.busy_other = None

    task = hass.async_create_task(finish())
    await call(hass, "media_player", "volume_up", MP)
    await task
    remote.state = real_state
    assert [e[0] for e in remote.log][-1] == "ok" and ("busy", "volume_up") in remote.log and remote.actions() == ["volume_up"]


async def test_command_running_while_home_assistant_waits(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    sensor = "binary_sensor.jbl_bar_9_1_command_running"
    assert hass.states.get(sensor).state == "off"
    remote.action_delay = 0.5
    task = hass.async_create_task(call(hass, "switch", "turn_on", "switch.jbl_bar_9_1_night_mode"))
    assert await until(lambda: hass.states.get(sensor).state == "on")
    attrs = hass.states.get(sensor).attributes
    assert attrs["source"] == "home_assistant" and attrs["action"] == "night_toggle"
    await task
    assert await until(lambda: hass.states.get(sensor).state == "off")


async def test_unload(hass: HomeAssistant, remote) -> None:
    entry = await setup(hass, remote)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_bass_offset(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    num = "number.jbl_bar_9_1_bass_offset"
    assert hass.states.get(num).state == "0.0"
    assert hass.states.get(num).attributes["status"] == "off"
    remote.log.clear()
    await call(hass, "number", "set_value", num, value=-1.5)
    assert remote.bass_offset == -1.5 and hass.states.get(num).state == "-1.5"
    assert [(e[1], e[4]) for e in remote.log if e[0] == "ok"] == [("bar91.bass-offset.set", {"offset_db": -1.5})]
    assert hass.states.get(num).attributes["status"] == "active"


async def test_bass_offset_needs_the_extension(hass: HomeAssistant, remote) -> None:
    remote.bass_offset = None
    await setup(hass, remote)
    assert hass.states.get("number.jbl_bar_9_1_bass_offset") is None


async def test_mode_after_standby(hass: HomeAssistant, remote) -> None:
    remote.remembered_mode = "Smart"
    await setup(hass, remote)
    assert hass.states.get("sensor.jbl_bar_9_1_mode_after_standby").state == "smart"


async def test_no_mode_after_standby_without_memory(hass: HomeAssistant, remote) -> None:
    await setup(hass, remote)
    assert hass.states.get("sensor.jbl_bar_9_1_mode_after_standby") is None


async def test_center_options_unchanged(hass: HomeAssistant, remote) -> None:
    """Center is shown 1-6 through translations; option values stay 0-5 for automations."""
    await setup(hass, remote)
    assert hass.states.get("select.jbl_bar_9_1_center_level").attributes["options"] == ["0", "1", "2", "3", "4", "5"]
