import json
from pdns_funcs import *
import logging
import yaml

def load_json_safely(json_string):
    try:
        logging.debug("EVENT LOAD_JSON: loading potential json: %s", json_string)
        py_object = json.loads(json_string)
        logging.debug("EVENT LOAD_JSON: returning python object: %s", py_object)
        return (py_object)
    except:
        logging.debug("EVENT LOAD_JSON: Invalid json.")
        return None

def read_yaml(filename=''):
    with open(filename, 'r') as file:
        configs = yaml.safe_load(file)
    return configs

def addto_struct(dns_struct, hostname, ip, weight):
    hostname = fix_hostname(hostname)
    logging.debug("EVENT ADD_TO_STRUCT: hostname: %s, ip: %s, weight: %s", hostname, ip, weight)
    if hostname in dns_struct:
        logging.debug("EVENT ADD_TO_STRUCT: hostname %s already in dns_struct.", hostname)
        dns_struct[hostname].append((ip, weight))
    else:
        logging.debug("EVENT ADD_TO_STRUCT: creating entry for hostname %s in dns_struct.", hostname)
        dns_struct[hostname] = [(ip, weight)]
    logging.debug("EVENT ADD_TO_STRUCT: after addition dns_struct: %s", dns_struct)

def removefrom_struct(dns_struct, hostname, ip, weight):
    hostname = fix_hostname(hostname)
    logging.debug("EVENT REMOVE_FROM_STRUCT: hostname: %s, ip: %s, weight: %s", hostname, ip, weight)
    if hostname in dns_struct:
        logging.debug("EVENT REMOVE_FROM_STRUCT: hostname %s present in dns_struct", hostname)
        dns_struct[hostname].remove((ip, weight))
        logging.debug("EVENT REMOVE_FROM_STRUCT: after removal dns_struct: %s", dns_struct)

def handle_added(pdnsHost, pdnsAPIKey, dns_struct, pod):
    multus_networks = get_multus_networks(pod)
    logging.debug("EVENT ADDED: Pod Name: %s", pod.metadata.name)
    logging.debug("EVENT ADDED: Pod Annotations: %s", pod.metadata.annotations)
    logging.debug("EVENT ADDED: Multus Networks: %s", multus_networks)
    if multus_networks:
        logging.debug("EVENT ADDED: Multus Networks: %s", "True")
        for network in multus_networks:
            logging.debug("EVENT ADDED: (Looping Through) Multus Network: %s", network)
            addto_struct(dns_struct=dns_struct, hostname=network['hostname'], \
                         ip=network['ip'], weight=network['weight'])
            logging.debug("EVENT ADDED: Updated DNS Structure: %s", dns_struct)
            commit_pdns(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, dns_struct=dns_struct, \
                        hostname=network['hostname'])
            logging.debug("EVENT ADDED: DNS Structure Commited for hostname: %s", network['hostname'])

def handle_modified(pdnsHost, pdnsAPIKey, dns_struct, pod, pending_pods):
    if pod.status.phase == 'Pending':
        pending_pods.append(pod.metadata.name)
        logging.debug("EVENT MODIFIED1: Pending Pods: %s", pending_pods)
    elif pod.status.phase == 'Running' and pod.metadata.name in pending_pods:
        multus_networks = get_multus_networks(pod)
        logging.debug("EVENT MODIFIED2: Pod Name: %s", pod.metadata.name)
        logging.debug("EVENT MODIFIED2: Pod Annotations: %s", pod.metadata.annotations)
        logging.debug("EVENT MODIFIED2: Multus Networks: %s", multus_networks)
        if multus_networks:
            for network in multus_networks:
                logging.debug("EVENT MODIFIED2: (Looping Through) Multus Network: %s", network)
                addto_struct(dns_struct=dns_struct, hostname=network['hostname'], \
                         ip=network['ip'], weight=network['weight'])
                logging.debug("EVENT MODIFIED2: Updated DNS Structure: %s", dns_struct)
                commit_pdns(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, dns_struct=dns_struct, \
                        hostname=network['hostname'])
                logging.debug("EVENT MODIFIED2: DNS Structure Commited for hostname: %s", network['hostname'])                
            pending_pods.remove(pod.metadata.name)
            logging.debug("EVENT MODIFIED2: Pending Pods: %s", pending_pods)

def handle_deleted(pdnsHost, pdnsAPIKey, dns_struct, pod):
    multus_networks = get_multus_networks(pod)
    logging.debug("EVENT DELETED: Pod Name: %s", pod.metadata.name)
    logging.debug("EVENT DELETED: Pod Annotations: %s", pod.metadata.annotations)
    logging.debug("EVENT DELETED: Multus Networks: %s", multus_networks)
    if multus_networks:
        for network in multus_networks:
            logging.debug("EVENT DELETED: (Looping Through) Multus Network: %s", network)
            removefrom_struct(dns_struct=dns_struct, hostname=network['hostname'], \
                              ip=network['ip'], weight=network['weight'])
            logging.debug("EVENT DELETED: Updated DNS Structure: %s", dns_struct)
            commit_pdns(pdnsHost=pdnsHost, pdnsAPIKey=pdnsAPIKey, dns_struct=dns_struct, \
                        hostname=network['hostname'])
            logging.debug("EVENT DELETED: DNS Structure Commited for hostname: %s", network['hostname'])
            

def valid_multus_pod(pod):
    annotations = pod.metadata.annotations
    if annotations:
        logging.debug("Pod Validation: Pod %s has some annotations.", pod.metadata.name)
        if 'k8s.v1.cni.cncf.io/network-status' in annotations and \
                'k8s.v1.cni.cncf.io/network-hostnames' in annotations:
            logging.debug("Pod Validation: Pod %s has required annotations.", pod.metadata.name)
            network_status_ann = annotations['k8s.v1.cni.cncf.io/network-status']
            network_hostnames_ann = annotations['k8s.v1.cni.cncf.io/network-hostnames']
            logging.debug("Pod Validation: Pod %s has network status: %s", pod.metadata.name, network_status_ann)
            logging.debug("Pod Validation: Pod %s has network hostnames: %s", pod.metadata.name, network_hostnames_ann)
            multus_networks = load_json_safely(network_status_ann)
            network_hostnames = load_json_safely(network_hostnames_ann)
            if multus_networks and network_hostnames:
                logging.debug("Pod Validation: Pod %s annotations are valid json.", pod.metadata.name)
                return True
    else:
        logging.debug("Pod Validation: Pod %s validation failed.", pod.metadata.name)
        return False

def get_multus_networks(pod):
    network_status = pod.metadata.annotations['k8s.v1.cni.cncf.io/network-status']
    network_hostnames = pod.metadata.annotations['k8s.v1.cni.cncf.io/network-hostnames']
    net_status = load_json_safely(network_status)
    net_hostnames = load_json_safely(network_hostnames)
    logging.debug("Get Multus Networks: Pod %s has network status: %s", pod.metadata.name, net_status)
    logging.debug("Get Multus Networks: Pod %s has network status: %s", pod.metadata.name, net_hostnames)
    net_struct = []
    if net_status and net_hostnames and \
        isinstance(net_status, list) and isinstance(net_hostnames, dict):
        logging.debug("Get Multus Networks: Pod %s annotations are valid json.", pod.metadata.name)
        for net in net_status:
            net_name = net['name'].split('/')[-1]
            if net_name in net_hostnames:
                logging.debug("Get Multus Networks: Multus network %s detected.", net_name)
                if net['ips'] and net_hostnames[net_name]['hostname'] and net_hostnames[net_name]['weight']:
                    logging.debug("Get Multus Networks: Multus network name: %s, ip: %s, hostname: %s, weight: %s.", \
                                  net_name, net['ips'][0], net_hostnames[net_name]['hostname'], net_hostnames[net_name]['weight'])
                    net_struct.append({'name': net_name, \
                                        'ip': net['ips'][0], \
                                        'hostname': net_hostnames[net_name]['hostname'], \
                                        'weight': net_hostnames[net_name]['weight']})
    return(net_struct)
        
