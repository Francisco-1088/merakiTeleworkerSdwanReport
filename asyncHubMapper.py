import meraki.aio
import asyncio
import config
import pandas as pd
from tabulate import tabulate

aiomeraki = meraki.aio.AsyncDashboardAPI(config.API_KEY,
            base_url="https://api.meraki.com/api/v1",
            log_file_prefix=__file__[:-3],
            print_console=True,
            maximum_retries=config.max_retries,
            maximum_concurrent_requests=config.max_requests,
)

async def get_vpn_statuses(aiomeraki, org_id, net_ids):
    try:
        vpn_in_net_list = await aiomeraki.appliance.getOrganizationApplianceVpnStatuses(organizationId=org_id, networkIds=net_ids, total_pages=-1)
    except meraki.aio.AsyncAPIError as e:
        parsed = e.message['errors'][0].split(" ")
        remove_net_ids_list = [net.strip(",") for net in parsed[9:]]
        new_net_ids = [i for i in net_ids if i not in remove_net_ids_list]
        vpn_in_net_list = await aiomeraki.appliance.getOrganizationApplianceVpnStatuses(organizationId=org_id, networkIds=new_net_ids, total_pages=-1)
    return vpn_in_net_list

async def gather_net_vpn_statuses(net_ids):
    net_vpns = []
    get_tasks = []
    for i in range(0, len(net_ids), 100):
        sub_net_ids = net_ids[i:i+100]
        get_tasks.append(get_vpn_statuses(aiomeraki, config.ORG_ID, sub_net_ids))

    for task in asyncio.as_completed(get_tasks):
        net_vpn_statuses_in_net_list = await task
        for net in net_vpn_statuses_in_net_list:
            net_vpns.append(net)
    return net_vpns

async def main(aiomeraki):
    async with aiomeraki:
        nets = await aiomeraki.organizations.getOrganizationNetworks(config.ORG_ID, total_pages=-1)
        net_ids = []
        print(len(nets))
        for net in nets:
            if 'L' not in net['id'] and net['isBoundToConfigTemplate']==True and net['id']:
                net_ids.append(net['id'])
        print(len(net_ids))
        main_vpn_statuses = await gather_net_vpn_statuses(net_ids)
    return main_vpn_statuses

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    vpn_statuses = loop.run_until_complete(main(aiomeraki))
    vpn_statuses_df = pd.DataFrame(vpn_statuses)
    vpn_statuses_df.to_csv("vpn_statuses.csv")
    vpn_status_spokes_list = []
    vpn_hubs_list = []
    vpn_status_list = vpn_statuses_df.to_dict("records")
    for row in vpn_status_list:
        if row['vpnMode'] == "spoke":
            res = row['merakiVpnPeers']
            new_row = {k: row[k] for k in row.keys() - {
                'merakiVpnPeers',
            }}
            for i in range(len(res)):
                new_res = res[i]
                new_row[f'hub_{i}_net_id'] = new_res['networkId']
                new_row[f'hub_{i}_net_name'] = new_res['networkName']
                new_row[f'hub_{i}_reachability'] = new_res['reachability']
            vpn_status_spokes_list.append(new_row)

    vpn_status_spokes_df = pd.DataFrame(vpn_status_spokes_list)

    vpn_status_spokes_df_primary_hub_group = vpn_status_spokes_df.groupby("hub_0_net_name")
    vpn_status_spokes_df_secondary_hub_group = vpn_status_spokes_df.groupby("hub_1_net_name")

    print("Primary Hubs: ")
    primary_hub_stats = []
    for key in vpn_status_spokes_df_primary_hub_group.groups:
        print(key)
        group_df = vpn_status_spokes_df_primary_hub_group.get_group(key)
        online_spokes = len(group_df[group_df['deviceStatus'] == "online"])
        offline_spokes = len(group_df[group_df['deviceStatus'] == "offline"])
        dormant_spokes = len(group_df[group_df['deviceStatus'] == "dormant"])
        reachable_spokes = len(group_df[group_df['hub_0_reachability'] == "reachable"])
        unreachable_spokes = len(group_df[group_df['hub_0_reachability'] == "unreachable"])
        hub_stats = {
            "hub_name": key,
            "online_spokes": online_spokes,
            "offline_spokes": offline_spokes,
            "dormant_spokes": dormant_spokes,
            "reachable_spokes": reachable_spokes,
            "unreachable_spokes": unreachable_spokes
        }
        primary_hub_stats.append(hub_stats)
        # print(tabulate(vpn_status_spokes_df_primary_hub_group.get_group(key), headers='keys', tablefmt='fancy_grid'))

    print("Secondary Hubs: ")
    secondary_hub_stats = []
    for key in vpn_status_spokes_df_secondary_hub_group.groups:
        print(key)
        group_df = vpn_status_spokes_df_secondary_hub_group.get_group(key)
        online_spokes = len(group_df[group_df['deviceStatus'] == "online"])
        offline_spokes = len(group_df[group_df['deviceStatus'] == "offline"])
        dormant_spokes = len(group_df[group_df['deviceStatus'] == "dormant"])
        reachable_spokes = len(group_df[group_df['hub_1_reachability'] == "reachable"])
        unreachable_spokes = len(group_df[group_df['hub_1_reachability'] == "unreachable"])
        hub_stats = {
            "hub_name": key,
            "online_spokes": online_spokes,
            "offline_spokes": offline_spokes,
            "dormant_spokes": dormant_spokes,
            "reachable_spokes": reachable_spokes,
            "unreachable_spokes": unreachable_spokes
        }
        secondary_hub_stats.append(hub_stats)

    global_hub_stats = []
    for hub_0 in primary_hub_stats:
        for hub_1 in secondary_hub_stats:
            if hub_0['hub_name'] == hub_1['hub_name']:
                total_online_spokes = hub_0['online_spokes'] + hub_1['online_spokes']
                total_offline_spokes = hub_0['offline_spokes'] + hub_1['offline_spokes']
                total_dormant_spokes = hub_0['dormant_spokes'] + hub_1['dormant_spokes']
                total_spokes = total_online_spokes + total_offline_spokes + total_dormant_spokes
                total_reachable_spokes = hub_0['reachable_spokes'] + hub_1['reachable_spokes']
                total_unreachable_spokes = hub_0['unreachable_spokes'] + hub_1['unreachable_spokes']
                primary_online_spokes = hub_0['online_spokes']
                primary_offline_spokes = hub_0['offline_spokes']
                primary_dormant_spokes = hub_0['dormant_spokes']
                primary_spokes = primary_online_spokes + primary_offline_spokes + primary_dormant_spokes
                primary_reachable_spokes = hub_0['reachable_spokes']
                primary_unreachable_spokes = hub_0['reachable_spokes']
                secondary_online_spokes = hub_1['online_spokes']
                secondary_offline_spokes = hub_1['offline_spokes']
                secondary_dormant_spokes = hub_1['dormant_spokes']
                secondary_spokes = secondary_online_spokes + secondary_offline_spokes + secondary_dormant_spokes
                secondary_reachable_spokes = hub_1['reachable_spokes']
                secondary_unreachable_spokes = hub_1['reachable_spokes']
                global_stats = {
                    "hub_name": hub_0['hub_name'],
                    "total_spokes": total_spokes,
                    "total_online_spokes": total_online_spokes,
                    "total_offline_spokes": total_offline_spokes,
                    "total_dormant_spokes": total_dormant_spokes,
                    "total_reachable_spokes": total_reachable_spokes,
                    "total_unreachable_spokes": total_unreachable_spokes,
                    "primary_spokes": primary_spokes,
                    "primary_online_spokes": primary_online_spokes,
                    "primary_offline_spokes": primary_offline_spokes,
                    "primary_dormant_spokes": primary_dormant_spokes,
                    "primary_reachable_spokes": primary_reachable_spokes,
                    "primary_unreachable_spokes": primary_unreachable_spokes,
                    "secondary_spokes": secondary_spokes,
                    "secondary_online_spokes": secondary_online_spokes,
                    "secondary_offline_spokes": secondary_offline_spokes,
                    "secondary_dormant_spokes": secondary_dormant_spokes,
                    "secondary_reachable_spokes": secondary_reachable_spokes,
                    "secondary_unreachable_spokes": secondary_unreachable_spokes,
                }
                global_hub_stats.append(global_stats)

    global_hubs = [hub['hub_name'] for hub in global_hub_stats]
    for hub in primary_hub_stats:
        if hub['hub_name'] not in global_hubs:
            global_stats = {
                "hub_name": hub['hub_name'],
                "total_spokes": hub['online_spokes'] + hub['offline_spokes'] + hub['dormant_spokes'],
                "total_online_spokes": hub['online_spokes'],
                "total_offline_spokes": hub['offline_spokes'],
                "total_dormant_spokes": hub['dormant_spokes'],
                "total_reachable_spokes": hub['reachable_spokes'],
                "total_unreachable_spokes": hub['unreachable_spokes'],
                "primary_spokes": hub['online_spokes'] + hub['offline_spokes'] + hub['dormant_spokes'],
                "primary_online_spokes": hub['online_spokes'],
                "primary_offline_spokes": hub['offline_spokes'],
                "primary_dormant_spokes": hub['dormant_spokes'],
                "primary_reachable_spokes": hub['reachable_spokes'],
                "primary_unreachable_spokes": hub['unreachable_spokes'],
                "secondary_spokes": 0,
                "secondary_online_spokes": 0,
                "secondary_offline_spokes": 0,
                "secondary_dormant_spokes": 0,
                "secondary_reachable_spokes": 0,
                "secondary_unreachable_spokes": 0,
            }
            global_hub_stats.append(global_stats)

    for hub in secondary_hub_stats:
        if hub['hub_name'] not in global_hubs:
            global_stats = {
                "hub_name": hub['hub_name'],
                "total_spokes": hub['online_spokes'] + hub['offline_spokes'] + hub['dormant_spokes'],
                "total_online_spokes": hub['online_spokes'],
                "total_offline_spokes": hub['offline_spokes'],
                "total_dormant_spokes": hub['dormant_spokes'],
                "total_reachable_spokes": hub['reachable_spokes'],
                "total_unreachable_spokes": hub['unreachable_spokes'],
                "primary_spokes": 0,
                "primary_online_spokes": 0,
                "primary_offline_spokes": 0,
                "primary_dormant_spokes": 0,
                "primary_reachable_spokes": 0,
                "primary_unreachable_spokes": 0,
                "secondary_spokes": hub['online_spokes'] + hub['offline_spokes'] + hub['dormant_spokes'],
                "secondary_online_spokes": hub['online_spokes'],
                "secondary_offline_spokes": hub['offline_spokes'],
                "secondary_dormant_spokes": hub['dormant_spokes'],
                "secondary_reachable_spokes": hub['reachable_spokes'],
                "secondary_unreachable_spokes": hub['unreachable_spokes'],
            }
            global_hub_stats.append(global_stats)

    primary_hub_stats_df = pd.DataFrame(primary_hub_stats)
    secondary_hub_stats_df = pd.DataFrame(secondary_hub_stats)
    global_hub_stats_df = pd.DataFrame(global_hub_stats)
    primary_hub_stats_df.to_csv("./primary_hub_stats.csv")
    secondary_hub_stats_df.to_csv("./secondary_hub_stats.csv")
    global_hub_stats_df.to_csv("./global_hub_stats.csv")

    print("Primary Hubs:")
    print(tabulate(primary_hub_stats_df, headers="keys", tablefmt="fancy_grid"))
    print("\n")
    print("Secondary Hubs:")
    print(tabulate(secondary_hub_stats_df, headers="keys", tablefmt="fancy_grid"))
    print("\n")
    print("Global:")
    print(tabulate(global_hub_stats_df, headers="keys", tablefmt="fancy_grid"))

