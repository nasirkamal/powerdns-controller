# Custom objects should be non-namespaced
import logging
import os
import sys
from kubernetes import client, config, watch
from pdns_funcs import *
from kube_funcs import *

configuration_path = '/etc/pdns/pdns.yaml'

logging.basicConfig(level=logging.DEBUG)
if not os.path.exists(configuration_path):
    logging.debug("Configuration file not present at %s", configuration_path)
    sys.exit()
controller_config = read_yaml(configuration_path)
pdns_endpoint = controller_config['configs']['powerdns']['endpoint']
pdns_key = controller_config['configs']['powerdns']['key']

config.load_incluster_config()
api_instance = client.CoreV1Api()
w = watch.Watch()
pending_pods = []
dns_struct = {}

for event in w.stream(api_instance.list_pod_for_all_namespaces):
    pod = event['object']
    logging.debug("Pod %s detected.", pod.metadata.name)
    if valid_multus_pod(pod):
        logging.debug("Pod %s is a valid multus pod.", pod.metadata.name)
        if event['type'] == 'ADDED':
            logging.debug("Event ADDED triggered for pod %s", pod.metadata.name)
            handle_added(pdns_endpoint, pdns_key, dns_struct, pod)
        if event['type'] == 'MODIFIED':
            logging.debug("Event MODIFIED triggered for pod %s", pod.metadata.name)
            handle_modified(pdns_endpoint, pdns_key, dns_struct, pod, pending_pods)
        if event['type'] == 'DELETED':
            logging.debug("Event DELETED triggered for pod %s", pod.metadata.name)
            handle_deleted(pdns_endpoint, pdns_key, dns_struct, pod)
