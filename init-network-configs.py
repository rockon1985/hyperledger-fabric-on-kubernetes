#!/usr/bin/env python

import yaml
import os
import sys
import time
import subprocess
from utils import puts, gets, exec_when_pod_up

flatten = lambda l: [item for sublist in l for item in sublist]

##############################################
########## SETTING UP NFS STORAGE ############
##############################################
def set_nfs_volume():
  os.system("kubectl apply -f ./public-certs-pvc/public-certs-nfs-service.yaml --namespace=peers")
  # wait for NFS server to get the clusterIP
  time.sleep(2)
  nfsClusterIP = subprocess.check_output("kubectl get svc nfs-server --namespace=peers -o=jsonpath={.spec.clusterIP}", shell=True)

  puts("INFO: Creating PVC for public certificates..")
  helmCmd = ("helm install --name=public-certs-pvc ./public-certs-pvc --namespace=peers"
  " --set nfs.clusterIP=%s" %nfsClusterIP)
  os.system(helmCmd)
  exec_when_pod_up("kubectl exec public-certs-injector-pod --namespace=peers -- ls /etc/hyperledger")
  return

def copy_public_certs():
  # Copy certs except private keys from crypto-config
  # os.system("find ./crypto-config -type f -name '*_sk' -delete")
  # os.system("find ./crypto-config -type f -name '*.key' -delete")
  puts("INFO: Copying public certs in ./crypto-config folder..")
  os.system("kubectl cp ./crypto-config peers/public-certs-injector-pod:/etc/hyperledger")
  puts("INFO: Public Certs Copied!! Deleting injector pod..")
  os.system("kubectl delete pod public-certs-injector-pod --namespace=peers")
  return

##############################################
####### CREATE PRIVATE KEYS SECRET ###########
##############################################
def create_org_secrets(domain):
  admin = gets(("find crypto-config/peerOrganizations/%s/users/Admin@%s/msp/keystore "
    "-type f -name '*_sk'" %(domain, domain)
  ))
  signed = gets(("find crypto-config/peerOrganizations/%s/users/Admin@%s/msp/signcerts "
    "-type f -name '*.pem'" %(domain, domain)
  ))
  puts("INFO: Creating Secrets for %s" %domain)
  os.system(("kubectl create secret generic %s-secret --from-file=admin-sign-cert=%s "
    "--from-file=tls-cert=%s --namespace=peers" %(domain, admin.strip(), signed.strip())
  ))

  # Mapping of key files form which the secret would get created
  # use this mapping to create org level secret from an external file
  KEY_PATHS = {
    'cert-p12': "keys/%s/cert.p12" %domain,
    'id-rsa': "keys/%s/id_rsa" %domain,
    'id-rsa-pub': "keys/%s/id_rsa.pub" %domain,
    'totp-key': "keys/%s/totp.key" %domain,
  }
  from_files = ' '.join(map(lambda x: '--from-file='+ x + '=' + KEY_PATHS[x], KEY_PATHS))
  os.system(("kubectl create secret generic %s-keys-secret %s "
    "--namespace=peers" %(domain, from_files)
  ))

##############################################
########## GENERATING NW CONFIG ##############
##############################################
def create_network_config(org, config):
  # fetching dynamic values
  peers = flatten(map(lambda o: map(lambda p: {'name': p['CommonName'], 'orgname': o['Domain']} ,o['Specs']),
    config['PeerOrgs'])
  )
  orderers = map(lambda o: map(lambda p: p['CommonName'] ,o['Specs']), config['OrdererOrgs'])
  domain = config['OrdererOrgs'][0]['Domain']
  admin_cert = ("/etc/%s/crypto-config/peerOrganizations/%s/users/Admin@%s/msp/"
    "keystore/keystore_sk" %(org['Domain'], org['Domain'], org['Domain'])
  )
  signed_cert = gets(("find crypto-config/peerOrganizations/%s/users/Admin@%s/msp/signcerts "
    "-type f -name '*.pem'" %(org['Domain'], org['Domain'])
  ))
  admin = gets(("find crypto-config/peerOrganizations/%s/users/Admin@%s/msp/keystore "
    "-type f -name '*_sk'" %(org['Domain'], org['Domain'])
  ))
  signed = gets(("find crypto-config/peerOrganizations/%s/users/Admin@%s/msp/signcerts "
    "-type f -name '*.pem'" %(org['Domain'], org['Domain'])
  ))

  
  # creating network-config object
  result = {
    'name': 'Network',
    'version': '1.0',
    'channels': {
      'buyer1seller1channel1': {
        'orderers': map(lambda o: o['CommonName'], config['OrdererOrgs'][0]['Specs']),
        'peers': {}
      },
    },
    'client': { 'organization': org['Name'] },
    'organizations': {},
    'orderers': {},
    'peers': {}
  }

  result['organizations'][org['Name']] = {
    'mspid': org['Name'] + 'MSP',
    'peers': map(lambda p: p['CommonName'],org['Specs']),
    'adminPrivateKey': { 'path': '/etc/hyperledger/' + admin.strip() },
    'signedCert': { 'path': '/etc/hyperledger/' + signed.strip() }
  }

  for ord in flatten(orderers):
    tls_ca_cert = gets(("find crypto-config/ordererOrganizations/%s"
      "/users/Admin@%s/msp/tlscacerts/ -type f -name 'tlsca*.pem'" %(domain, domain)
    ))
    result['orderers'][ord] = {
      'url': "grpcs://%s:7050" %ord,
      'grpcOptions': {
        "ssl-target-name-override": ord
      },
      'tlsCACerts': { 'path': '/etc/hyperledger/' + tls_ca_cert.strip() },
    }

  for peer in peers:
    tls_ca_cert = gets(("find crypto-config/peerOrganizations/%s"
      "/peers/%s/msp/tlscacerts/ -type f -name 'tlsca*.pem'" %(peer['orgname'], peer['name'])
    ))
    result['peers'][peer['name']] = {
      'url': "grpcs://%s:7051" %peer['name'],
      'grpcOptions': {
        "ssl-target-name-override": peer['name'],
        "default-authority": peer['name']
        },
      'tlsCACerts': { 'path': '/etc/hyperledger/' + tls_ca_cert.strip() }
    }
    result['channels']['buyer1seller1channel1']['peers'][peer['name']] = {
      'endorsingPeer': True,
      'chaincodeQuery': True,
      'ledgerQuery': True,
      'eventSource': True
    }
    if(peer['orgname'] == org['Domain']):
      result['peers'][peer['name']]['eventUrl'] = "grpcs://%s:7053" %peer['name']

  return result

def generate_network_configs():
  # Check for the crypto-config folder
  if (not os.path.isdir('crypto-config')):
    print("ERROR: Can't create network config without `crypto-config` folder")
  os.system("mkdir ./network-configs")
  with open("crypto-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)
      for org in config['PeerOrgs']:
        # Creating a sub directory for org pods' data storing purposes
        os.system(("kubectl exec public-certs-injector-pod --namespace=peers -- mkdir -p "
          "/etc/hyperledger/data/%s/chaincode /etc/hyperledger/data/%s/workingDir" %(org['Domain'], org['Domain'])
        ))
        # Generating dynamic network-config file for org
        network_config = create_network_config(org, config)
        stream = file("./network-configs/%s-network-config.yaml" %org['Domain'], 'w')
        puts("INFO: creating network-config for %s" %org['Name'])
        yaml.dump(network_config, stream)
        puts("INFO: Copying network config, File location /etc/hyperledger/data/%s/" %org['Domain'])
        # Copying network config file to org directory in NFS
        cmd = ("kubectl cp ./network-configs/%s-network-config.yaml "
          "peers/public-certs-injector-pod:/etc/hyperledger/data/%s/" %(org['Domain'], org['Domain'])
        )
        
        os.system(cmd)
        create_org_secrets(org['Domain'])

      
    except yaml.YAMLError as exc:
      print(exc)
  return


##############################################
############ SCRIPT STARTS HERE ##############
##############################################
set_nfs_volume()
generate_network_configs()
copy_public_certs()
