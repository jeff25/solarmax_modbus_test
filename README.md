[![hacs_badge](https://img.shields.io/badge/HACS-default-orange.svg)](https://github.com/hacs/default)[![GitHub release](https://img.shields.io/github/v/release/Chris42/homeassistant-solarmax-modbus)](https://github.com/Chris42/homeassistant-solarmax-modbus/releases)[![GitHub All Releases](https://img.shields.io/github/downloads/Chris42/homeassistant-solarmax-modbus/total)](https://github.com/Chris42/homeassistant-solarmax-modbus/releases)  


# Solarmax Inverter Modbus - A Home Assistant integration for Solarmax SP/SMT Inverters

Integration for reading data from Solarmax Inverters through Modbus TCP.

It should work for Ampere Inverter sold by EKD-Solar if it is labled 4600SP on the small sticker. Also reported to work on Solarmax 6SMT

## Features

- Installation through Config Flow UI
- Configurable polling interval - changeable at any time

## Installation

Add this repositiry to HACS and install. 

1. Open HACS
2. Click on the three dots -> add userdefined repository -> paste git link
3. Find "homeassistant-solarmax-modbus" and click "Download."
4. Restart Home Assistant.
5. After reboot of Home-Assistant, this integration can be configured through the integration setup UI


## Configuration

1. Navigate to the "Integrations" page in your configuration, then click "Add Integration" and 
select "Solarmax Modbus."
2. Enter the IP Address and Interval 

## Features

Because the Inverter is powered off if there is no power from the solar panels there is an optional ping_host which can be used to prevent the modbus connect failure logs at night. If you use a modbus proxy you may enter the real address of the inverter. If you set this option tcp query is only tried if the ping was successful. 


