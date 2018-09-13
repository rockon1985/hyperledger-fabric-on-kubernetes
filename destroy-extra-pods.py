#!/usr/bin/env python
import yaml
import os

print("INFO: Removing Extra Pods for Organizations")

with open("./crypto-config.yaml", 'r') as stream:
  try:
    config = yaml.load(stream)
    for org in config['PeerOrgs']:
      os.system("kubectl delete secret %s-secret --namespace=peers" %org['Domain'])
      os.system("kubectl delete secret %s-keys-secret --namespace=peers" %org['Domain'])
      for p in org['ExtraPods']:
        os.system("helm del --purge %s" %p['Name'])
      
  except yaml.YAMLError as exc:
    print(exc)
