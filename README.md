# TryFi for Home Assistant
![beta_badge](https://img.shields.io/badge/maturity-Beta-yellow.png?style=for-the-badge)
[![](https://img.shields.io/github/release/tryfi/hass-tryfi/all.svg?style=for-the-badge)](https://github.com/tryfi/hass-tryfi/releases)
![release_date](https://img.shields.io/github/release-date/tryfi/hass-tryfi.svg?style=for-the-badge)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/tryfi/hass-tryfi)
[![](https://img.shields.io/github/license/tryfi/hass-tryfi?style=for-the-badge)](LICENSE)
[![](https://img.shields.io/github/actions/workflow/status/tryfi/hass-tryfi/combined.yaml?style=for-the-badge)](https://github.com/tryfi/hass-tryfi/actions)

This allows you to integrate [TryFi](https://tryfi.com) Smart GPS Collars with Home Assistant.

**Note:** This integration includes an embedded version of the pytryfi library, so no separate installation is required.

## Features
Current functionality includes:
* Device Tracker - your pet will show up in HA using the GPS coordinates from the collar
* Step Counter - it will report your pets daily, weekly, and monthly steps
* Distance Counter - it will report your pets daily, weekly and monthly distance
* Battery Level - it will report your Pet's collar battery level
* Battery Charging - it will report if your Pet's collar is charging
* Collar Light - you can control the light on the collar by turning it on and off and setting the color
* Lost Dog Mode - allows you to select Lost mode if your dog if it is lost and select Safe if it is found
* Bases - reports the status of the base (online/offline)

# Installation
## Pre-Requisities
* Home Assistant >= 2024.10.0
* TryFi dog collar with active cellular subscription
* [HACS](https://github.com/custom-components/hacs) is already installed

## Installation Methods

### HACS Install

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tryfi&repository=hass-tryfi&category=integration)

1. Click the button above to add this repository to HACS, or manually search for `TryFi` under `Integrations` in the HACS Store tab.
2. Add the [Integration](#configuration) to your HA and configure.

### Manual Install
1. In your `/config` directory, create a `custom_components` folder if one does not exist.
2. Copy the [tryfi](https://github.com/tryfi/hass-tryfi/tree/master/custom_components) folder and all of it's contents to your `custom_components` directory.
3. Restart Home Assistant.
4. Add the [Integration](#configuration) to your HA and configure.

## Configuration
1. After installing TryFi go to Configuration --> Integrations and add a new Integration
2. Search for TryFi
3. Enter in your TryFi username and password. Optionally you can select a polling frequency option (in seconds). Suggestion is nothing less then 5.
4. Click Submit

![Setup](https://github.com/tryfi/hass-tryfi/blob/master/docs/setup.jpg?raw=true)

## Diagnostics

On the TryFi integration page, open the menu for the config entry and select **Download diagnostics**. The TryFi section contains polling settings, the last ten coordinator refresh outcomes, and basic collar battery, charging and base connectivity status. Pets, bases, Wi-Fi and behavior stats each report their latest status, last attempt and success timestamps, and the exception type on failure. Behavior stats are marked skipped when no request was attempted. It omits account details, device identifiers, location data and raw API messages.

## Validation
Once you have added the integration, you will see 1 or more devices and entities associated with this integration. To validate its accuracy, you can review the steps and distance counters for your pet or its current whereabouts.

![Integration](https://github.com/tryfi/hass-tryfi/blob/master/docs/tryfiaftersetup.jpg?raw=true)

### Dog Device and Entities
#### Device

![Dog Device](https://github.com/tryfi/hass-tryfi/blob/master/docs/dogdevice.jpg?raw=true)

#### Entities

![Dog Entities](https://github.com/tryfi/hass-tryfi/blob/master/docs/dogentities.jpg?raw=true)

### Base Device and Entities

![Base Device and Entities](https://github.com/tryfi/hass-tryfi/blob/master/docs/dogbase.jpg?raw=true)

# How to Use
## Light Collar
The light on your Pet's collar is represented as a light switch in HA. It can either be turned on or off.
The color can be set. The collar only supports Red, Green, Blue, LightBlue, Purple, Yellow, and White. The closest color to your selection will be used.

![Lovelace](https://github.com/tryfi/hass-tryfi/blob/master/docs/doglight.jpg?raw=true)

## Lost Dog Mode
TryFi is equiped with a "Lost Dog Mode" functionality. In HA this is represented by a select entity.
Select Lost if your pet is lost or Safe if your pet is OK.

![Lovelace](https://github.com/tryfi/hass-tryfi/blob/master/docs/doglostmode.png?raw=true)

# Lovelace

## Entities
```
type: entities
entities:
  - entity: select.harley_lost_state
  - entity: sensor.harley_collar_battery_level
  - entity: binary_sensor.harley_collar_battery_charging
  - entity: sensor.home_base
  - entity: sensor.harley_daily_steps
  - entity: sensor.harley_weekly_steps
  - entity: sensor.harley_monthly_steps
  - entity: sensor.harley_daily_distance
  - entity: sensor.harley_weekly_distance
  - entity: sensor.harley_monthly_distance
  - entity: sensor.harley_daily_sleep
  - entity: sensor.harley_weekly_sleep
  - entity: sensor.harley_monthly_sleep
  - entity: sensor.harley_daily_nap
  - entity: sensor.harley_weekly_nap
  - entity: sensor.harley_monthly_nap
```
## Light
```
type: light
entity: light.harley_collar_light
```

# Automation Examples
## Turn on the Collar Light After Dark
Turns on the collar light after dark if the pet is not home.
```
- id: '1604060166498'
  alias: Turn on Light After Dark If Not Home
  description: ''
  trigger:
  - platform: sun
    event: sunset
  condition:
  - condition: and
    conditions:
    - condition: device
      device_id: a7237a6c1144fcd90828b21de2572603
      domain: device_tracker
      entity_id: device_tracker.pet_tracker
      type: is_not_home
  action:
  - type: turn_on
    device_id: a7237a6c1144fcd90828b21de2572603
    entity_id: light.pet_collar_light
    domain: light
  mode: single
```
## Fully Charged Notification
Sends notification when battery has charged to 100%.
```
- id: '1661129896868'
  alias: Pet's Collar - Fully Charged
  description: ''
  trigger:
  - platform: state
    entity_id:
    - sensor.pet_collar_battery_level
    to: '100'
    for:
      hours: 0
      minutes: 0
      seconds: 0
  condition:
  - condition: state
    entity_id: binary_sensor.pet_collar_battery_charging
    state: 'on'
  action:
  - service: notify.everyone_phone
    data:
      message: Pet's collar is fully charged!
  mode: single
```
# Known Issues
* It sometimes takes time for the status to accurately refresh in HA. For example the light on/off status and the Lost Mode select status.

# Contributor Policy
The AI Policy for this integration is: No matter if you write code by hand or using AI, you should understand what it's doing and how. Please do a once-over read of your own code before sending a Pull request to make our jobs easier.

# Links
* [Python TryFi Interface](https://github.com/tryfi/pytryfi)
* [TryFi]((https://tryfi.com/))
