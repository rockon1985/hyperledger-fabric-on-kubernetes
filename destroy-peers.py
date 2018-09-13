#!/usr/bin/env python
import yaml
import os
import sys

print("""\033[93m
    | |                            
  __| | __ _ _ __   __ _  ___ _ __ 
 / _` |/ _` | '_ \ / _` |/ _ \ '__|
| (_| | (_| | | | | (_| |  __/ |   
 \__,_|\__,_|_| |_|\__, |\___|_|   
                    __/ |          
                   |___/           
""")
print("NOTE: This operation will remove the existing fabric peer cluster \033[0m")
res = raw_input("Do you wish to continue (y/n):")
if res != 'y':
  sys.exit(0)

with open("./crypto-config.yaml", 'r') as stream:
  try:
    config = yaml.load(stream)
    os.system('helm del --purge public-certs-pvc')
    for org in config['PeerOrgs']:
      namespace = org['Name'].lower()
      os.system("helm del --purge %s-geotrade-node" %namespace)
      os.system("helm del --purge cli-%s-pvc" %namespace)
      os.system("helm del --purge cli-%s" %namespace)
      for p in org['Specs']:
        os.system("helm del --purge pvc-%s" %p['CommonName'])
        os.system("helm del --purge %s" %p['CommonName'])
      
  except yaml.YAMLError as exc:
    print(exc)