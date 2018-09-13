#!/usr/bin/env python

import os
import time
import subprocess


##############################################
############ UTILITY METHODS #################
##############################################
def puts(str):
  print "\033[94m%s\033[0m" %str
  return

def gets(str):
  return subprocess.check_output(str, shell=True)

def exec_when_pod_up(cmd):
  res = os.system(cmd)
  while(res != 0):
    puts("INFO: Waiting for pod to be up. Don't stop the process..")
    time.sleep(1)
    res = os.system(cmd)
