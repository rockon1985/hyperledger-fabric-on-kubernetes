# Hyperledger Fabric on kubernetes cluster

This script and helm charts would set up the necessary components of Hyperledger fabric. By default, it creates the setup for 2 Organization and 2 peer pods per organization. You can change this configuration by modifying crpyto-config.yaml file.

## Prerequisites

Before the setup, you should have following prerequisites ready

- You should have kubectl and helm installed
- A kubernetes cluster created and kubectl connected to it
- Python 2.7 or above *(Python comes installed by default in modern linux OS)*

## Cluster Architechture

Script would by default have the following pods instantiated:

1. Orderer service Pod
2. Org 1 CLI pod
3. Org 1 Peer Pods
4. Org 2 CLI pod
5. Org 2 Peer Pods
6. NFS service Pod *(If specified)*
7. Org 1 Extra App Pods *(If specified)*
8. Org 2 Extra App Pods *(If specified)*

[hyperledger-fabric-kubernetes-architechture](http://funkyimg.com/i/2LcAa.png)

- We would be having organization specific pods in the cluster and there would be a dedicated volumes for each peer pod storing their certs and giving them run time writable space.

- Each of the peer pods has their dedicated volume claims (PVC) in which their respective MSP and TLS certificates would be present. Also, note that for each organization, we can run our own application’s instance having the business logic.
- The extra app would be able to communicate with the peer pods PVC. It would also have access to a shared NFS server. The NFS would also store network-config.yaml files that are needed to install and instantiate chaincode in fabric peers via nodeSDK.
- Alternatively, you can use CLI pods to install and instantiate the chaincode as well.


## Setup

### Step 1: Setup crpyto-config.yaml
 
Here we utilize the `crypto-config.yaml` file to setup our cluster requirement. This is the same file which is used by cryptogen tool to create peers’ and orderers’ certificates. We can modify this file to specify how many organizations we need, and how many peers are required in each organization. We may also specify our own unique application running for each organization by passing it in `ExtraPods` field.

By default it will have a 2 Organization setup, with 2 Peer pods per organization and a single channel between them.

### Step 2: Modify the configtx.yaml file

Next step, would be to modify the configtx.yaml file in the same fashion

### Step 3: Bring the fiber components up

Use the command `make fiber-up` to setup the fabric components in our cluster. This command will invoke the init_orderers.py and init_peers.py scripts that would generate the pods according to the modified files.
The script does the following tasks in chronological order:

- Create crypto-config folder having the peer and orderer certificates using cryptogen tool
- Create channel-artifact folder having the genesis-block for the fabric.
- Spin up the Persistent volume claims (PVC) for orderer pods and copy the required certificates for pods in their respective PVC via a test pod.
- Deletes the test pod and create Ordering Pods
- Spin up the Persistent volume claims (PVC) for all peer pods and copy the required certificates for pods in their respective PVC.
- Deletes the test pod and initialize Peer pods for all organizations

### Step 4(Optional): Setup Extra App Pods

You need to perform this step only if you want a separate app to run per organization. This app can be used to communicate with Fabric component using nodeSDK of hyperledger fabric.

#### Step 4.A: Updating crypto-config.yaml and adding helm chart for your app

- Setting up the Extra Pods that you need to run per organization. You can mention these in in ‘ExtraPods’ field for each PeerOrgs in crypto-config.yaml.

- A sample entry to have a simple app, would look like this:

```yaml
ExtraPods:
     - Name: buyerone-node-app
       Chart: ./buyerone
       Values:
         - name: "replicaCount"
           value: "1"
         - name: "name"
           value: buyerone-node-app
         - name: "NODE_ENV"
           value: "production"
```

- In the Chart field you need to pass the path of the helm chart of you app. You can also pass values to override in helm chart in Values field.

#### Step 4.B: Setting up NFS storage

- If your extra apps would be interacting with Fabric components using the SDK, you apps would need network-config.yaml files which stores the channel information and peer public certs path.

*NOTE*: If your extra app doesn’t need nodeSDK or network-config.yaml, you can skip Step 4.B

- To add the NFS server, we must first add a persistent disk in your project. To add a disk from cloud SDK, run the command:

```bash
cloud compute disks create --size=10GB --zone=us-east1-b nfs-disk
```

You can also go in gcloud console and create it using UI dashboard.

- In the file */public-certs-pvc/public-certs-nfs-service.yaml* , update the value of `gcePersistentDisk.pdName` to the name your persistent disk.

- Run the command make `nfs-up` to create the shared NFS storage and generate the network-config.yaml files for each organization.

#### Step 4.C: Setting up Extra App Pods

- Check if all the fiber pods are up by command: `kubectl get po --namespace=peers`

- Once all the pods are Running, run command: `make extras-up` to setup the extra App.

### Bring down the cluster

If we want to bring down the cluster we setup, we can simply run  `make down`  Alternatively, if you wish to remove or recreate only a portion of our cluster you can use following commands:

`make peer-down` : to tear down only the peer pods and other organizational pods
`make orderer-down` : to tear down only orderer pods and namespace.

For more details about these commands, check the Makefile in the repository.

 

