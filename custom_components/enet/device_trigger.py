"""Provides device triggers for enet."""
from __future__ import annotations

from typing import Any
import logging
import voluptuous as vol

from homeassistant.components.automation import (
    AutomationActionType,
    AutomationTriggerInfo,
)
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE


from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, ATTR_ENET_EVENT, CONF_UNIQUE_ID, CONF_SUBTYPE
from .aioenet import SensorChannel

_LOGGER = logging.getLogger(__name__)

BUTTON_EVENT_TYPES = (
    "initial_press",  # ButtonEvent.INITIAL_PRESS,
    "short_release",  # ButtonEvent.SHORT_RELEASE,
)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(BUTTON_EVENT_TYPES),
        vol.Required(CONF_SUBTYPE): vol.Union(int, str),
        vol.Required(CONF_UNIQUE_ID): vol.Union(int, str),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for enet devices."""
    device_registry = await hass.helpers.device_registry.async_get_registry()
    device_entry = device_registry.async_get(device_id)
    entry_id = [i for i in device_entry.config_entries][0]
    hub = hass.data[DOMAIN][entry_id]
    triggers = []

    enet_device_id = get_enet_device_id(device_entry)
    enet_device = next((d for d in hub.devices if d.uid == enet_device_id), None)
    _LOGGER.debug("Enet device: %s", enet_device)

    # if not isinstance(enet_device, Sensor):
    if not any([isinstance(c, SensorChannel) for c in enet_device.channels]):
        return

    for channel in enet_device.channels:
        for event_type in BUTTON_EVENT_TYPES:
            triggers.append(
                {
                    CONF_DEVICE_ID: device_entry.id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_PLATFORM: "device",
                    CONF_TYPE: event_type,
                    CONF_SUBTYPE: channel.channel["no"],
                    CONF_UNIQUE_ID: enet_device.uid,
                }
            )
    _LOGGER.debug("Triggers: %s", triggers)
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: AutomationTriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: ATTR_ENET_EVENT,
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_TYPE: config[CONF_TYPE],
                CONF_SUBTYPE: config[CONF_SUBTYPE],
            },
        }
    )
    _LOGGER.debug("Attaching trigger: %s", event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, automation_info, platform_type="device"
    )


def get_enet_device_id(device_entry):
    """Get Hue device id from device entry."""
    return next(
        (
            identifier[1]
            for identifier in device_entry.identifiers
            if identifier[0] == DOMAIN
            and ":" not in identifier[1]  # filter out v1 mac id
        ),
        None,
    )
