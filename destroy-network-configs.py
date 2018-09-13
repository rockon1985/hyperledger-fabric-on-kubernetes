#!/usr/bin/env python
import os

print "INFO: Destroying NFS Storage service and volume"
os.system("helm delete public-certs-pvc --purge")
os.system("kubectl delete deployment nfs-server --namespace=peers")
os.system("kubectl delete svc nfs-server --namespace=peers")