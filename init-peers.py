#!/usr/bin/env python

import yaml
import os
import time
import sys
import subprocess
from utils import puts, exec_when_pod_up

ordNamespace = sys.argv[1] if len(sys.argv) > 1 is not None else "orderers"

def set_org_peer_pods(namespace, orgPeers, domain, orgName):
  puts("%s : Creating Fabric Peer Pods.." %namespace)
  for p in orgPeers:
    # create secrets for MSP and TLS certs
    create_cert_secrets(p, namespace, domain)
    # create actual fabric peer pod
    create_fabric_peer_pod(p, namespace, domain, orgPeers, orgName)
  return

def create_fabric_peer_pod(peer, org, domain, orgPeers, orgName):
  gossipPeer = [p for p in orgPeers if p['Hostname'] != peer['Hostname']][0]
  env = ("--set hlfpeer.orgname=%s --set hlfpeer.peername=%s "
    "--set hlfpeer.orgdomain=%s --set hlfpeer.gossipPeer=%s "
    "--set hlfpeer.peerOrgName=%s" %(org, peer['Hostname'], domain, gossipPeer['Hostname'], orgName)
  )
  cmd = "helm install --name=%s ./org-peer --namespace=peers %s" %(peer['CommonName'], env)
  os.system(cmd)

def create_cert_secrets(peer, namespace, domain):
  for subfolder in ['msp', 'tls']:
    src = "./crypto-config/peerOrganizations/%s/peers/%s/%s" %(domain, peer['CommonName'], subfolder)
    srcTarFile = "./crypto-config/peerOrganizations/%s/peers/%s/%s.tar" %(domain, peer['CommonName'], subfolder)
    os.system("tar -cvf %s %s" %(srcTarFile, src))
    os.system(("kubectl create secret generic %s-%s-secret --from-file=%s=%s "
      "--namespace=peers" %(peer['CommonName'], subfolder, subfolder, srcTarFile)
    ))
    os.system("rm %s" %srcTarFile)


def set_org_cli(namespace, org, orderer):
  domain = org['Domain']
  # create persistent volume claims for CLI
  res = os.system("helm install --name=cli-%s-pvc ./org-cli-pvc"
    " --set orgname=%s --set ordDomain=%s --set ordNamespace=%s "
    "--namespace=peers" %(namespace, namespace, orderer['Specs'][0]['CommonName'], "peers")
  )
  if res != 0:
    return
  cmd = ("kubectl exec %s-cli-injector-pod --namespace=peers "
    "-- mkdir -p /opt/gopath/src/github.com/hyperledger/fabric/orderer/crypto "
    "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations "
    "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations " %namespace
  )
  # copy required files into the volume claim
  exec_when_pod_up(cmd)
  remoteBasePath = "/opt/gopath/src/github.com/hyperledger/fabric"
  pod = "peers/%s-cli-injector-pod" %namespace
  puts("INFO: Copying channel-artifacts into CLI pvc")
  os.system("kubectl cp ./channel-artifacts %s:%s/peer" %(pod, remoteBasePath))
  puts("INFO: Copying scripts into CLI pvc")  
  os.system("kubectl cp ./scripts %s:%s/peer" %(pod, remoteBasePath))
  puts("INFO: Copying chaincode into CLI pvc")  
  os.system("kubectl cp ./chaincode %s:/opt/gopath/src/github.com" %pod)
  puts("INFO: Copying peers certificates into CLI pvc")
  os.system(("kubectl cp ./crypto-config/peerOrganizations/%s "
    "%s:%s/peer/crypto/peerOrganizations" %(domain, pod, remoteBasePath)))
  puts("INFO: Copying orderer certificates into CLI pvc")  
  os.system("kubectl cp ./crypto-config/ordererOrganizations/%s/msp/tlscacerts "
    "%s:%s/peer/crypto/ordererOrganizations/%s" %(orderer['Domain'], pod, remoteBasePath, orderer['Domain']))
  puts("INFO: Copyied configs into CLI pvc!! Removing test pod")
  # delete the temporary injector pod
  os.system("kubectl delete pod %s-cli-injector-pod --namespace=peers" %namespace)
  # Setting up actual CLI pod
  os.system(("helm install --name=cli-%s ./org-cli --set orgName=%s "
    "--set orgDomain=%s --set corePeer=peer0 --set peerOrgName=%s "
    "--namespace=peers" %(namespace, namespace, domain, org['Name'])))
  return


##############################################
############ INITIALIZE METHOD ###############
##############################################

def init():
  # Generate crypto-config folder if not present via cryptogen tool
  if (not os.path.isdir('crypto-config')):
    os.system("./bin/cryptogen generate --config=./crypto-config.yaml")
    puts("Generating crypto-config via cryptogen tool")
  puts("Creating Namespace for all fabric components")
  os.system("kubectl create namespace peers")
  with open("crypto-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)

      # Setting the Fabric Peer pods for each organization
      # as per specified in file crypto-config.yaml
      for org in config['PeerOrgs']:
        set_org_peer_pods(org['Name'].lower(), org['Specs'], org['Domain'], org['Name'])

      for org in config['PeerOrgs']:
        set_org_cli(org['Name'].lower(), org, config['OrdererOrgs'][0])

    except yaml.YAMLError as exc:
      print(exc)
  return

init()
