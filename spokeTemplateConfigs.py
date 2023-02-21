import meraki
import pandas as pd
import config
from tabulate import tabulate

def print_tabulate(data):
    """
    Outputs a list of dictionaries in table format
    :param data: Dictionary to output
    :return:
    """
    print(tabulate(pd.DataFrame(data), headers='keys', tablefmt='fancy_grid'))

dashboard = meraki.DashboardAPI(config.API_KEY)

org_id = config.ORG_ID

networks = dashboard.organizations.getOrganizationNetworks(org_id, total_pages=-1)

templates = dashboard.organizations.getOrganizationConfigTemplates(org_id)
templates_df = pd.DataFrame(templates)

print_tabulate(templates_df)

networks_df = pd.DataFrame(networks)
print(networks_df['configTemplateId'].value_counts())

networks_by_template = {}
for configTemplateId, df in networks_df.groupby('configTemplateId'):
    #print("Template "+configTemplateId+"\n",df,"\n")
    networks_by_template[configTemplateId]=df

template_spokes = []
for key in networks_by_template.keys():
    vpn = dashboard.appliance.getNetworkApplianceVpnSiteToSiteVpn(networks_by_template[key].iloc[0]['id'])
    if vpn['mode']=='spoke':
        l3_fw = dashboard.appliance.getNetworkApplianceFirewallL3FirewallRules(networks_by_template[key].iloc[0]['id'])
        l7_fw = dashboard.appliance.getNetworkApplianceFirewallL7FirewallRules(networks_by_template[key].iloc[0]['id'])
        shaping = dashboard.appliance.getNetworkApplianceTrafficShaping(key)
        shaping_rules = dashboard.appliance.getNetworkApplianceTrafficShapingRules(
            key)
        splash = dashboard.appliance.getNetworkAppliancePorts()
        vpn['l3_fw']=l3_fw
        vpn['l7_fw']=l7_fw
        vpn['shaping']=shaping
        vpn['shaping_rules']=shaping_rules
        for template in templates:
            if template['id'] == key:
                vpn['template_name']=template['name']
        vpn['template_id'] = key
        for i in range(len(vpn['hubs'])):
            for net in networks:
                if net['id']==vpn['hubs'][i]['hubId']:
                    vpn['hubs'][i]['hubName']=net['name']
            vpn[f"hub_{i}"] = vpn['hubs'][i]
        template_spokes.append(vpn)

template_spoke_df = pd.DataFrame(template_spokes)
print_tabulate(template_spoke_df)

template_spoke_df.to_csv('./template_spoke_configs.csv')