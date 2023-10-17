import requests
import logging

def pdns_exists(pdnsHost='', pdnsAPIKey=''):
    logging.debug("EVENT CHECK_POWER_DNS: Checking PowerDNS at %s", pdnsHost)
    URL = pdnsHost + '/api/v1/servers/localhost/zones'
    logging.debug("EVENT CHECK_POWER_DNS: PowerDNS URL: %s", URL)
    headers = {"X-API-KEY": pdnsAPIKey, "Content-Type": "application/json"}
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        logging.debug("EVENT CHECK_POWER_DNS: PowerDNS Exists at %s", pdnsHost)
        return True
    else:
        return False

def fix_hostname(hostname):
    if hostname[-1] != '.':
        correct_hostname = hostname + '.'
        logging.debug("EVENT FIX_HOSTNAME: Fixed hostname: %s to %s", hostname, correct_hostname)
        return correct_hostname
    else:
        logging.debug("EVENT FIX_HOSTNAME: Hostname already in correct format: %s", hostname)
        return hostname

def zone_exists(pdnsHost='', pdnsAPIKey='', zonename=''): # hostname: test.example.org.
    URL = pdnsHost + '/api/v1/servers/localhost/zones' + '/' + zonename
    logging.debug("EVENT IF_ZONE_EXISTS: Checking Zone: %s URL %s", zonename, URL)
    headers = {"X-API-KEY": pdnsAPIKey, "Content-Type": "application/json"}
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        logging.debug("EVENT IF_ZONE_EXISTS: Zone %s Exists.", zonename)
        return True
    else:
        logging.debug("EVENT IF_ZONE_EXISTS: Zone %s Does Not Exists.", zonename)
        return False

def create_zone(pdnsHost='', pdnsAPIKey='', zonename=''):
    URL = pdnsHost + '/api/v1/servers/localhost/zones'
    logging.debug("EVENT CREATE_ZONE: Creating zone %s", zonename)
    headers = {"X-API-KEY": pdnsAPIKey, "Content-Type": "application/json"}
    data = {
        "name": zonename,
        "kind": "Native",
        "masters": [],
        "nameservers":[
            "ns1." + zonename,
            "ns2." + zonename
        ],
        "rrsets":[]
    }
    logging.debug("EVENT CREATE_ZONE: Request data: %s", data)
    try:
        response = requests.post(URL, headers=headers, json=data)
        logging.debug("EVENT CREATE_ZONE: Response status code: %s", response.status_code)
        return response.status_code
    except:
        logging.debug("EVENT CREATE_ZONE: Could not create zone: %s", zonename)
        return None

def add_powerdns_entry(pdnsHost='', pdnsAPIKey='', hostname='', entries=[]):
    # entries
        # option 1: ['10.0.0.1'] or ['10.0.0.1', '10.0.0.2']
        # option 2: [('10.0.0.1', 10), ('10.0.0.2', 20)]
    URL = pdnsHost + '/api/v1/servers/localhost/zones' + '/' + '.'.join(hostname.split('.')[1:])
    logging.debug("EVENT ADD_PDNS_ENTRY: hostname: %s, URL: %s:", hostname, URL)
    headers = {"X-API-KEY": pdnsAPIKey, "Content-Type": "application/json"}
    records = []
    for entry in entries:
        if isinstance(entry, tuple) and len(entry) == 2:
            records.append({"content": entry[0], "disabled": False, "weight": entry[1]})
        elif isinstance(entry, str):
            records.append({"content": entry, "disabled": False})
        else:
            logging.debug("EVENT ADD_PDNS_ENTRY: datatype of entry %s is not right.", entry)
            return None
    data = {
        "rrsets":
        [{
            "name": hostname,
            "type": "A",
            "ttl" : 3600,
            "changetype": "REPLACE",
            "records": records
    }]
    }
    logging.debug("EVENT ADD_PDNS_ENTRY: entry data: %s", data)
    try:
        response = requests.patch(URL, headers=headers, json=data)
        logging.debug("EVENT ADD_PDNS_ENTRY: response code: %s", response.status_code)
        return response.status_code
    except:
        logging.debug("EVENT ADD_PDNS_ENTRY: Failed to add entry.")
        return None

def delete_zone(pdnsHost='', pdnsAPIKey='', zonename=''):
    URL = pdnsHost + '/api/v1/servers/localhost/zones' + '/' + zonename
    logging.debug("EVENT DELETE_ZONE: deleting zone %s", zonename)
    headers = {"X-API-KEY": pdnsAPIKey, "Content-Type": "application/json"}
    try:
        response = requests.delete(URL, headers=headers)
        logging.debug("EVENT DELETE_ZONE: zone deletion response code %s", response.status_code)
        return response.status_code
    except:
        logging.debug("EVENT DELETE_ZONE: could not delete zone: %s", zonename)
        return None

def commit_pdns(pdnsHost='', pdnsAPIKey='', dns_struct=[], hostname=''):
    hostname = fix_hostname(hostname)
    zonename = '.'.join(hostname.split('.')[1:])
    logging.debug("EVENT COMMIT_PDNS: comiting to powerdns hostname: %s, data: %s", hostname, dns_struct[hostname])
    if pdns_exists(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey):
        logging.debug("EVENT COMMIT_PDNS: PowerDNS exists.")
        if zone_exists(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, zonename=zonename):
            logging.debug("EVENT COMMIT_PDNS: Zone %s exists.", zonename)
            response_code = add_powerdns_entry(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, \
                               hostname=hostname, entries=dns_struct[hostname])
            logging.debug("EVENT COMMIT_PDNS: Add entry response code: %s", response_code)
            return response_code
        else:
            print("Zone ", zonename, "Does Not Exists!")
            print("Creating Zone ", zonename, ".")
            logging.debug("EVENT COMMIT_PDNS: Zone %s does not exists.", zonename)
            logging.debug("EVENT COMMIT_PDNS: Creating zone: %s", zonename)
            create_zone_response_code = create_zone(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, zonename=zonename)
            if create_zone_response_code:
                logging.debug("EVENT COMMIT_PDNS: Create zone response code: %s", create_zone_response_code)
                response_code = add_powerdns_entry(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, \
                                    hostname=hostname, entries=dns_struct[hostname])
                logging.debug("EVENT COMMIT_PDNS: Add entry response code: %s", response_code)
                return response_code