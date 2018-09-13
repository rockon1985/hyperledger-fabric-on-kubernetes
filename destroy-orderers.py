#!/usr/bin/env python

import os

charts = os.popen("helm list | grep orderer | awk '{print $1}'").read().split()
for chart in charts:
  os.system("helm delete %s --purge" %chart)
