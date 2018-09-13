SHELL=/bin/bash

peer-up:
	python init-peers.py peers

peer-down:
	python destroy-peers.py peers

orderer-up:
	python init-orderers.py peers

orderer-down:
	python destroy-orderers.py

nfs-up:
	python init-network-configs.py

nfs-down:
	python destroy-network-configs.py

extras-up:
	python init-extra-pods.py peers

extras-down:
	python destroy-extra-pods.py

fiber-up:
	orderer-up peer-up

fiber-down:
	peer-down orderer-down

fetch:
	python fetchPDF.py

# bring up the cluster
up: orderer-up peer-up nfs-up extras-up

# tear down the cluster
down: peer-down orderer-down nfs-down extras-down

