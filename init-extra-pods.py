#!/usr/bin/env python

import yaml
import os
import sys
from utils import puts

# Extra Pods that needs to be run for every organization
# To run such pods, add the Name and Chart path in the `ExtraPods` field
# in crypto-config.yaml file under each OrgPeer entry.
def set_extra_pods(namespace, extraPods):
  puts("%s : Creating Extra Pods.." %namespace)
  for p in extraPods:
    env = ' '.join(map(lambda x: "--set %s=%s" %(x['name'], x['value']), p['Values']))
    extraPodHelmCmd = "helm install --name=%s %s --namespace=peers %s" %(p['Name'], p['Chart'], env)
    puts(extraPodHelmCmd)
    os.system(extraPodHelmCmd)
  return

def init():
  with open("crypto-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)
      for org in config['PeerOrgs']:
        namespace = sys.argv[1] if len(sys.argv) > 1 is not None else "orderers"
        set_extra_pods(namespace, org['ExtraPods'])
    except yaml.YAMLError as exc:
      print(exc)
  return

init()

print("""\033[92m
 _____                              
/  ___|                             
\ `--. _   _  ___ ___ ___  ___ ___  
 `--. \ | | |/ __/ __/ _ \/ __/ __| 
/\__/ / |_| | (_| (_|  __/\__ \__ \ 
\____/ \__,_|\___\___\___||___/___/
          
""")
print("==== Hyperledger cluster setup complete on your cluster! ==== \033[0m")
puts("* PODS RUNNING:")
os.system('kubectl get po --namespace=peers')
puts("* SERVICES RUNNING:")
os.system('kubectl get svc --namespace=peers')
