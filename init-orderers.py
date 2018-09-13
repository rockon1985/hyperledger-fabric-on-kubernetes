#!/usr/bin/env python

import yaml
import os
import sys
import time
from utils import puts

namespace = sys.argv[1] if len(sys.argv) > 1 is not None else "orderers"
puts("INFO: using %s as namespace ..." %namespace)

def set_orderer_pvc(orderer, domain):
  puts("INFO: Creating Orderer Certificate Secrets")
  ordererDir = "%s-%s" %(orderer['Specs'][0]['Hostname'], orderer['Domain'])
  create_cert_secrets(domain, orderer['Domain'], ordererDir)
  create_genesis_secret(domain, orderer['Specs'][0]['Hostname'])

def create_orderer_pod(domain):
  puts("INFO: Creating orderer Pod")
  env = ("--set domain=%s" %domain)
  cmd = "helm install --name=%s ./orderer --namespace=%s %s" %(domain, namespace, env)
  return os.system(cmd)

def create_cert_secrets(domain, ordDomain, ordererDir):
  for subPath in ['msp', 'tls']:
    src = "./crypto-config/ordererOrganizations/%s/orderers/%s/%s" %(ordDomain, ordererDir, subPath)
    srcTarFile = "./crypto-config/ordererOrganizations/%s/orderers/%s/%s.tar" %(ordDomain, ordererDir, subPath)
    os.system("tar -cvf %s %s" %(srcTarFile, src))
    os.system(("kubectl create secret generic %s-%s-secret --from-file=%s=%s "
      "--namespace=peers" %(domain, subPath, subPath, srcTarFile)
    ))
    os.system("rm %s" %srcTarFile)

def create_genesis_secret(domain, hostname):
  # rename genesis block
  if (os.path.isfile('./channel-artifacts/genesis.block')):
    os.system("mv ./channel-artifacts/genesis.block ./channel-artifacts/%s.genesis.block" %hostname)
  os.system(("kubectl create secret generic %s-genesis-secret --from-file=%s.genesis.block=./channel-artifacts/%s.genesis.block "
    "--namespace=peers" %(domain, hostname, hostname)
  ))

def init():
  # generate crypto-config folder if not present
  if (not os.path.isdir('crypto-config')):
    puts("Generating crypto-config via cryptogen tool")
    os.system("./bin/cryptogen generate --config=./crypto-config.yaml")
  
  # generate channel-artifacts if not present
  if (not os.path.isdir('channel-artifacts')):
    puts("Generating channel-artifacts via configtxgen tool")
    os.system("mkdir channel-artifacts")
    os.system("./bin/configtxgen -profile AllOrgsOrdererGenesis -outputBlock ./channel-artifacts/genesis.block")
    os.system("./bin/configtxgen -profile AllOrgsChannel -outputCreateChannelTx ./channel-artifacts/buyer1seller1channel1.tx -channelID buyer1seller1channel1")
  with open("crypto-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)
      for orderer in config['OrdererOrgs']:
        name = orderer['Name'].lower()
        puts("%s : Creating Orderer Service.." %name)
        # TODO: use subprocess.Popen instead of os.system
        os.system("kubectl create namespace %s" %namespace)
        domain = orderer['Specs'][0]['CommonName']
        set_orderer_pvc(orderer, domain)
        create_orderer_pod(domain)

    except yaml.YAMLError as exc:
      puts(exc)
  return

init()
