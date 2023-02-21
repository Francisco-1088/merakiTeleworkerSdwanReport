# merakiTeleworkerSdwanReport

This repository contains a number of tools for gathering information about large AutoVPN deployments, especially teleworker use cases, but also applicable to SD-WAN use cases.

* **deviceClientReport:** Returns information about all clients attached to teleworker and SD-WAN devices across an entire organization, including the teleworker device or SD-WAN device they connect to, and the template their teleworker/SD-WAN device is attached to. Also returns information about individual teleworker/SD-WAN gateways, their reachability and active uplinks.
* **spokeTemplateConfigs:** Returns existing configurations (l3/l7 firewalls, traffic shaping, shaping rules and hub priorities) for all teleworker and SD-WAN templates in the organization as well as the number of spokes attached to each one.
* **asyncHubMapper:** Query VPN statuses across the entire organization, and determine the number of spokes attached to each hub by priority, their online/offline/dormant statuses, as well as their reachability/unreachability to each hub.

# Table of Contents

[Introduction](#intro)

[Prerequisites](#prereq)

[How to use](#howtouse)

[Caveats](#caveats)

<a id="intro"></a>

# Introduction

In Progress...

<a id="prereq"></a>

## Prerequisites

1. Active Cisco Meraki subscriptions in the orgs where the script will be run
2. API access enabled for these organizations, as well as an API Key with access to them. See how to enable [here](https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API)
3. A working Python 3.0 environment
4. Install libraries in `requirements.txt`
5. A working organization with Hub and Spoke teleworker/SD-WAN configs.

<a id="howtouse"></a>

## How to Use

1. Clone repo to your working directory with `git clone https://github.com/Francisco-1088/merakiSwitchProfiler.git`
2. Edit `config.py`
* Add your API Key under `api_key` in line 2
* Add the Organization ID of the organization where the source configuration template exists. You can find your Org ID easily by right clicking anywhere in the screen while logged in to your organization, and clicking "View Page Source". In the resulting page use "Find" to look for the keyword `Mkiconf.org_id`
3. Run `pip install -r requirements.txt` from your terminal
4. `deviceClientReport.py`:
* Run with `python deviceClientReport.py`
* Output files:
* `org_devices.csv`: Lists all MX/Z devices in the organization.
* `org_networks.csv`: Lists all MX/Z networks in the organization, along with their associated templates.
* `device_network.csv`: Joined table of the previous two reports.
* `teleworker_sdwan_device_report.csv`: Details of all teleworker/SD-WAN devices in the organization, including their WAN IPs, network names, associated templates, public IPs and firmware versions.
* `client_report.csv`: Lists all clients attached to teleworker/SD-WAN devices, their network usage, IP addressing as well as the details of their attached teleworker/SD-WAN device.
5. `spokeTemplateConfigs.py`:
* Run with `python spokeTemplateConfigs.py`
* Will output a single file named `template_spoke_configs.csv` which contains each teleworker/SD-WAN template in the organization, its Hub priorities, the number of hubs associated to it, and the L3 firewall, L7 firewall, traffic shaping settings and their associated traffic shaping rules.
6. `asyncHubMapper.py`:
* Run with `python asyncHubMapper.py`
* This script is optimized with the async Library, but in very large orgs can take a while to finish. For a 7000 spoke organization, it can take 3-4 minutes to complete.
* Output files:
* `primary_hub_stats.csv`: Contains the online, offline, dormant, reachable and unreachable spokes totals per Hub, for all spokes using that Hub as primary.
* `secondary_hub_stats.csv`: Contains the online, offline, dormant, reachable and unreachable spokes totals per Hub, for all spokes using that Hub as secondary.
* `global_hub_stats.csv`: Contains the online, offline, dormant, reachable and unreachable spokes totals per Hub, detailing the number of spokes using it as primary and secondary for each stat.
* Note that this script assumes that no spokes exist in the organization with more than 2 associated hubs.

<a id="caveats"></a>

## Caveats

In Progress...
