import meraki
import asyncio
import meraki.aio
import pandas as pd
import config
from tabulate import tabulate

# Instantiate async Meraki API client
aiomeraki = meraki.aio.AsyncDashboardAPI(
            config.API_KEY,
            base_url="https://api.meraki.com/api/v1",
            log_file_prefix=__file__[:-3],
            print_console=False,
            maximum_retries=config.max_retries,
            maximum_concurrent_requests=config.max_requests,
)

# Instantiate synchronous Meraki API client
dashboard = meraki.DashboardAPI(
    config.API_KEY,
    base_url="https://api.meraki.com/api/v1",
    log_file_prefix=__file__[:-3],
    print_console=config.console_logging,
    )

async def gather_clients(aiomeraki, dev_serial, net_name, net_id, temp_name, temp_id):
    clients = await aiomeraki.devices.getDeviceClients(dev_serial)
    if clients != []:
        for client in clients:
            client['serial']=dev_serial
            client['net_name']=net_name
            client['networkId']=net_id
            client['configTemplateName']=temp_name
            client['configTemplateId']=temp_id
    return clients

def print_tabulate(df):
    print(tabulate(df, headers='keys', tablefmt='fancy_grid'))

async def gather_teleworker_devices(aiomeraki):
    org_devices = await aiomeraki.organizations.getOrganizationDevices(
        organizationId=config.ORG_ID,
        total_pages=-1
    )
    org_devices_pd = pd.DataFrame(org_devices)
    org_devices_pd = org_devices_pd[org_devices_pd['networkId'].notna()]
    org_devices_pd.to_csv('./org_devices.csv')

    org_templates = await aiomeraki.organizations.getOrganizationConfigTemplates(
        organizationId=config.ORG_ID
    )

    org_templates_pd = pd.DataFrame(org_templates).rename(columns={'id':'configTemplateId', 'name': 'configTemplateName', 'productTypes': 'configTemplateProductTypes', 'timeZone': 'configTemplateTimeZone'})

    org_networks = await aiomeraki.organizations.getOrganizationNetworks(
        organizationId=config.ORG_ID,
        total_pages=-1
    )

    org_networks_pd = pd.DataFrame(org_networks)
    org_networks_pd = org_networks_pd[org_networks_pd['configTemplateId'].notna()].rename(columns={'id':'networkId', 'name': 'net_name', 'url': 'net_url', 'tags': 'net_tags', 'notes': 'net_notes'})

    device_uplinks = dashboard.organizations.getOrganizationDevicesUplinksAddressesByDevice(organizationId=config.ORG_ID)
    device_uplinks_df = pd.DataFrame(device_uplinks)

    serials_df = pd.DataFrame(device_uplinks_df['serial'].dropna().to_list(), columns=['serial'])

    uplinks_df = pd.DataFrame(device_uplinks_df['uplinks'].dropna().to_list(), columns=['cellular', 'wan1', 'wan2'])
    wan1_df = pd.DataFrame(uplinks_df['wan1'].dropna().to_list(), columns=['interface', 'addresses'])
    wan1_addresses_df = pd.concat([wan1_df.explode('addresses').drop(['addresses'], axis=1),
                                   wan1_df.explode('addresses')['addresses'].apply(pd.Series)], axis=1)

    device_uplinks_addresses = serials_df.join(wan1_addresses_df)
    public_ips = pd.DataFrame(device_uplinks_addresses['public'].dropna().to_list(), columns=['address']).rename(columns={'address': 'public_ip'})

    device_uplinks_addresses = device_uplinks_addresses.join(public_ips)
    device_uplinks_addresses = device_uplinks_addresses.drop(columns=["public", "interface", "protocol", "address"])

    org_devices_pd = org_devices_pd.merge(device_uplinks_addresses, on='serial', how='left')

    org_networks_pd.to_csv('./org_networks.csv')
    #print(tabulate(org_devices_pd.head(), headers='keys', tablefmt='fancy_grid'))
    #print(tabulate(org_templates_pd.head(), headers='keys', tablefmt='fancy_grid'))
    #print(tabulate(org_networks_pd.head(), headers='keys', tablefmt='fancy_grid'))

    org_devices_pd['networkId'] = org_devices_pd['networkId'].astype(str)
    org_networks_pd['networkId'] = org_networks_pd['networkId'].astype(str)

    device_network_pd = org_devices_pd.merge(org_networks_pd, on='networkId', how='left')
    device_network_pd = device_network_pd[device_network_pd['configTemplateId'].notna()]
    device_network_pd.to_csv('./device_network.csv')
    device_network_pd['configTemplateId'] = device_network_pd['configTemplateId'].astype(str)
    #print(device_network_pd)
    #print(tabulate(device_network_pd.head(), headers='keys', tablefmt='fancy_grid'))

    device_network_template_pd = device_network_pd.merge(org_templates_pd, on='configTemplateId', how='left')
    #print(tabulate(device_network_template_pd, headers='keys', tablefmt='fancy_grid'))
    device_network_template_pd.to_csv('./teleworker_sdwan_device_report.csv')

    device_network_template_dict = device_network_template_pd.to_dict('records')

    get_tasks = []
    for device in device_network_template_dict:
        get_tasks.append(gather_clients(aiomeraki, dev_serial=device['serial'], net_name=device['net_name'], net_id=device['networkId'], temp_name=device['configTemplateName'], temp_id=device['configTemplateId']))

    results = []
    for task in asyncio.as_completed(get_tasks):
        result = await task
        for item in result:
            results.append(item)

    results_pd = pd.DataFrame(results)
    print(tabulate(results_pd.head(), headers='keys', tablefmt='fancy_grid'))

    results_pd.to_csv('./clients_report.csv')

    return org_devices_pd, org_templates_pd, org_networks_pd

async def main(aiomeraki):
    async with aiomeraki:
        org_devices_pd, org_templates_pd, org_networks_pd = await gather_teleworker_devices(aiomeraki)

    return org_devices_pd, org_templates_pd, org_networks_pd

if __name__ == "__main__":
    # -------------------Gather switch specific data-------------------
    loop = asyncio.get_event_loop()
    org_devices_pd, org_templates_pd, org_networks_pd = loop.run_until_complete(main(aiomeraki))
