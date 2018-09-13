const shim = require('fabric-shim');
const util = require('util');

var defaultChaincode = class {

  // Initialize the chaincode
  async Init(stub) {
    console.info('========= Default chaincode Init =========');
    let ret = stub.getFunctionAndParameters();
    console.info(ret);
    let args = ret.params;
    // initialise only if 2 parameters passed.
    if (args.length != 2) {
      return shim.error('Incorrect number of arguments. Expecting 2');
    }

    let type = args[0];
    let value = args[1];
    if (type !== 'key' || typeof value !== 'string') {
      return shim.error('Expecting string value for key');
    }

    try {
      await stub.putState(type, Buffer.from(value));
      return shim.success();
    } catch (err) {
      return shim.error(err);
    }
  }

  async Invoke(stub) {
    console.info('========= Default chaincode Invoke =========');
    let ret = stub.getFunctionAndParameters();
    console.info(ret);
    let method = this[ret.fcn];
    if (!method) {
      console.log('no method of name:' + ret.fcn + ' found');
      return shim.error();
    }

    try {
      let payload = await method(stub, ret.params);
      return shim.success(payload);
    } catch (err) {
      console.log(err);
      return shim.error(err);
    }
  }

  async updateKey(stub, args) {
    // initialise only if 2 parameters passed.
    if (args.length != 2) {
      throw new Error('Incorrect number of arguments. Expecting "key" and "<shared secret key>"');
    }
    let type = args[0];
    let value = args[1];

    if (type !== 'key' || typeof value !== 'string') {
      throw new Error('Invalid arguments. Expecting "key" and "<shared secret key>"');
    }
    await stub.putState(type, Buffer.from(value));
  }

  async updateContractAddress(stub, args) {
    // initialise only if 2 parameters passed.
    if (args.length != 2) {
      throw new Error('Invalid arguments. Expecting "contractAddress" and "<address of the contract>"');
    }
    let type = args[0];
    let address = args[1];

    if (type !== 'contractAddress' || typeof address !== 'string') {
      throw new Error('Incorrect number of arguments. Expecting "contractAddress" and "<address of the contract>"');
    }
    await stub.putState(type, Buffer.from(address));
  }

  // query callback representing the query of a chaincode
  async query(stub, args) {
    if (args.length != 1) {
      throw new Error('Incorrect number of arguments. Expecting type to query')
    }
    let type = args[0];

    // Get the state from the ledger
    let value = await stub.getState(type);
    if (!value) {
      throw new Error('Failed to get state for ' + type);
    }

    console.info('Query Response:');
    console.info(value);
    return value;
  }
};

shim.start(new defaultChaincode());
