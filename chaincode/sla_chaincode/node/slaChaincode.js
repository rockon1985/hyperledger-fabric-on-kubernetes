const shim = require('fabric-shim');
const util = require('util');
const ClientIdentity = require('fabric-shim').ClientIdentity;
const ContractSLA = 'CONTRACT_SLA';

class slaChaincode {

  // Init chaincode with new SLA
  // require SLA object
  async Init(stub) {
    console.info('========= SLA chaincode Init =========');
    let ret = stub.getFunctionAndParameters();
    let args = ret.params;
    if (args.length != 1) {
      return shim.error('Incorrect number of arguments. Expecting 1');
    }

    let sla = args[0];

    try {
      JSON.parse(sla)
    } catch(err) {
      return shim.error('Expecting SLA object as an argument');
    }

    try {
      await stub.putState(ContractSLA, Buffer.from(sla));
      return shim.success();
    } catch (err) {
      return shim.error(err);
    }
  }

  // Invoke SLA Chaincode
  async Invoke(stub) {
    console.info('========= SLA chaincode Invoke =========');
    let ret = stub.getFunctionAndParameters();

    let method = this[ret.fcn];
    if (!method) {
      console.log('no method of name:' + ret.fcn + ' found');
      return shim.error();
    }

    try {
      let payload = await method(stub, ret.params, this);
      return shim.success(payload);
    } catch (err) {
      console.log(err);
      return shim.error(err);
    }
  }

  // returns latest reporting data object
  async getReportingDataAddress(stub) {
    let mspId = new ClientIdentity(stub).getMSPID();
    if (!mspId) {
      throw new Error('Sender does not have a valid MSPID to get Reporting data')
    }

    let reportingDataAddress = await stub.getState(mspId);

    if (!reportingDataAddress || !reportingDataAddress.toString()) {
      throw new Error('Failed to get state for ' + mspId);
    }
    return reportingDataAddress;
  }

  // Check if reporting data address already exists
  async isExisting(stub, args, thisClass) {
    if(!args && args.length != 1 && typeof(args[0]) !== 'string') {
      throw new Error('Invalid number of arguments.')
    }
    let historicReportingDataMethod = thisClass['getHistoricReportingData'];
    let historicData = await historicReportingDataMethod(stub, args);
    let historicDataJson = JSON.parse(historicData);
    let length = historicDataJson.length;
    let found = false;
    for ( let i=0; i<length; i++) {
      if (JSON.parse(historicDataJson[i]["Value"]).address === args[0]) {
        found = true;
        break;
      }
    }
    return Buffer.from(found.toString());
  }

  // persist reporting data
  async addReportingDataAddress(stub, args) {
    if (args.length != 1) {
      throw new Error('Incorrect number of arguments. Expecting "<Reporting Data Object>"');
    }
    let reportingDataObject = args[0];
    try {
      JSON.parse(reportingDataObject)
    } catch(err) {
      return shim.error('Expecting Reporting data object as an argument');
    }

    let mspId = new ClientIdentity(stub).getMSPID();
    await stub.putState(mspId, Buffer.from(reportingDataObject));
  }

  // returns time period of SLA
  async getTimePeriod(stub, args, thisClass) {
    let sla;
    let getSlaMethod = thisClass['getSla'];
    sla = await getSlaMethod(stub, args);
    let json = JSON.parse(sla);
    return Buffer.from(JSON.stringify(json.timePeriod));
  }

  // returns entire SLA
  async getSla(stub, args) {
    let sla = await stub.getState(ContractSLA);
    if (!sla) {
      throw new Error('Failed to get state for ' + ContractSLA);
    }
    return sla;
  }

  // returns reporting frequency for this sla
  async getReportingFrequency (stub, args, thisClass) {
    let sla;
    let getSlaMethod = thisClass['getSla']
    sla = await getSlaMethod(stub, args)
    let json = JSON.parse(sla)
    return Buffer.from(json.reportingFrequency.toString());
  }

  // returns array of historic reporting data objects
  async getHistoricReportingData(stub) {
    let mspId = new ClientIdentity(stub).getMSPID();
    let iterator = await stub.getHistoryForKey(mspId)
    let allResults = [];
    if (!iterator) {
      console.log('No history found')
    } else {
      while (true) {
        let res = await iterator.next();
        if (res.value && res.value.value.toString()) {
          let jsonRes = {};
          jsonRes.TxId = res.value.tx_id;
          jsonRes.Timestamp = res.value.timestamp;
          jsonRes.Value = res.value.value.toString('utf8');
          allResults.push(jsonRes);
        }
        if (res.done) {
          await iterator.close();
          break;
        }
      }
    }
    return Buffer.from(JSON.stringify(allResults));
  }

};

shim.start(new slaChaincode());
