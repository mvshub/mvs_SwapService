# Swap Service of CrossChain

#### Description
Swap Service of CrossChain

#### Software Architecture
Python3 & Flask

#### Installation

1. install mysqldb
```bash
sudo apt-get install mysql-server
sudo apt-get install libmysqlclient-dev
sudo apt-get install python-mysqldb
pip3 install mysqlclient

default mysql database config (see config/service.json)

"mysql_host":"127.0.0.1",
"mysql_port":3306,
"mysql_user":"root",
"mysql_passwd":"123456",
"mysql_db":"wallet",
```

2. install python3 packages
```bash
pip3 install gevent
pip3 install pycrypto

pip3 install flask
pip3 install flask-sqlalchemy
pip3 install sqlalchemy-utils
pip3 install flask-migrate
pip3 install flask_bootstrap
pip3 install flask_wtf
```

3. create database 'wallet'
```
create database wallet charset utf8;
```

#### Instructions

Run:
```bash
python3 main.py
```
or, use watcher script (it will watch and restart the service if it's stopped)
```
nohup ./scripts/start_swap_service.py >/dev/null 2>&1 &
```

#### Config file
1. service.json
```
服务:
host: 服务监听地址
port: 服务监听端口

mysql数据库：
mysql_host: 地址
mysql_port: 监听端口
mysql_user: 用户
mysql_passwd: 密码
mysql_db:  数据库名称

rpcs 服务:
id：唯一标志，不能重复
name：ETP， ETH，ETHToken
type：ETP为rpcs.etp.Etp， ETH代币 为 rpcs.eth_token.EthToken，ETH为 rpcs.eth.Eth
uri:全节点url
contract_mapaddress：ETPMap 合约地址，用于链接eth地址到etp did或者address

scans 扫描置换模块：
interval：扫描数据库间隔
services 交易模块:
rpc: rpc id,
coin: 货币类型，ETH,ETP,ETHToken
minconf: 最小块高确认,
minrenew: 最小重试块高，交易失败，未生成有效交易哈希且超过minrenew，重新发送交易(未开启)
account: 用户名
passphrase:用户密码
did:etp发行资产所需数字身份
enable:是否启用


tokens 监视代币模块：
name:代币symbol，不能重复
contract_address:代币创建合约地址
enable:是否激活
decimal: 小数位数
```


#### ETH
1. install & start
```
sudo npm install -g ganache-cli truffle
ganache-cli
```

2. truffle commands
```
cd project_dir
truffle init
truffle create contract contract_name
truffle compile

truffle migrate --reset
truffle migrate
truffle deploy

truffle console

contract_name.deployed().then(instance => contract = instance)
contract.function.call()
```

3. smart contract
##### ETPMAP
```
pragma solidity ^0.4.18;

   contract ETPMap {
     mapping (address => string) internal address_map;
     event MapAddress(address, string);
     function get_address(address addr) constant public returns (string) {
         return address_map[addr];
     }
     function map_address(string etpaddr) public {
         address addr = msg.sender;
         address_map[addr] = etpaddr;
         MapAddress(addr, etpaddr);
     }
  }

  abi接口:
    [{"constant":true,"inputs":[{"name":"addr","type":"address"}],"name":"get_address","outputs":[{"name":"","type":"string","value":""}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"etpaddr","type":"string"}],"name":"map_address","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"anonymous":false,"inputs":[{"indexed":false,"name":"","type":"address"},{"indexed":false,"name":"","type":"string"}],"name":"MapAddress","type":"event"}]
```
##### ERC20
```
pragma solidity ^0.4.18;

 contract Token {

    uint256 public totalSupply;

    function balanceOf(address _owner) constant public returns (uint256 balance);

    function transfer(address _to, uint256 _value) public returns (bool success);

    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success);

    function approve(address _spender, uint256 _value) public returns (bool success);

    function allowance(address _owner, address _spender) constant public returns (uint256 remaining);

    event Transfer(address indexed _from, address indexed _to, uint256 _value);
    event Approval(address indexed _owner, address indexed _spender, uint256 _value);
}

contract StandardToken is Token {

    function transfer(address _to, uint256 _value) public returns (bool success) {
        if (balances[msg.sender] >= _value && _value > 0) {
            balances[msg.sender] -= _value;
            balances[_to] += _value;
            Transfer(msg.sender, _to, _value);
            return true;
        } else { return false; }
    }

    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success) {
        if (balances[_from] >= _value && allowed[_from][msg.sender] >= _value && _value > 0) {
            balances[_to] += _value;
            balances[_from] -= _value;
            allowed[_from][msg.sender] -= _value;
            Transfer(_from, _to, _value);
            return true;
        } else { return false; }
    }

    function balanceOf(address _owner) constant public returns (uint256 balance) {
        return balances[_owner];
    }

    function approve(address _spender, uint256 _value) public returns (bool success) {
        allowed[msg.sender][_spender] = _value;
        Approval(msg.sender, _spender, _value);
        return true;
    }

    function allowance(address _owner, address _spender) constant public returns (uint256 remaining) {
      return allowed[_owner][_spender];
    }

    mapping (address => uint256) balances;
    mapping (address => mapping (address => uint256)) allowed;
}

contract HumanStandardToken is StandardToken {

    string public name;
    string public symbol;
    uint64 public decimals;

    function HumanStandardToken (
        uint256 _initialAmount,
        string _tokenName,
        uint8 _decimalUnits,
        string _tokenSymbol
        ) public{
        balances[msg.sender] = _initialAmount;
        totalSupply = _initialAmount;
        name = _tokenName;
        decimals = _decimalUnits;
        symbol = _tokenSymbol;
    }

}

abi 接口：
[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string","value":"ABC"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"success","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256","value":"10000000000000"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"success","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint64","value":"5"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256","value":"0"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string","value":"ABC"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"success","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256","value":"0"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[{"name":"_initialAmount","type":"uint256","index":0,"typeShort":"uint","bits":"256","displayName":" _ initial Amount","template":"elements_input_uint","value":"10000000000000"},{"name":"_tokenName","type":"string","index":1,"typeShort":"string","bits":"","displayName":" _ token Name","template":"elements_input_string","value":"ABC"},{"name":"_decimalUnits","type":"uint8","index":2,"typeShort":"uint","bits":"8","displayName":" _ decimal Units","template":"elements_input_uint","value":"5"},{"name":"_tokenSymbol","type":"string","index":3,"typeShort":"string","bits":"","displayName":" _ token Symbol","template":"elements_input_string","value":"ABC"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_owner","type":"address"},{"indexed":true,"name":"_spender","type":"address"},{"indexed":false,"name":"_value","type":"uint256"}],"name":"Approval","type":"event"}]
```



#### ETP
```
mvs-cli createnewaccount test1 test123456
mvs-cli registerdid test1 test123456 crosschain
mvs-cli createasset -i crosschain -n 18 -r -1 -s ERC.ETH -v 1 test1 test123456
mvs-cli issue test1 test123456 ERC.ETH
mvs-cli createasset -i crosschain -n 5 -r -1 -s ERC.ABC -v 1 test1 test123456
mvs-cli issue test1 test123456 ERC.ABC
mvs-cli createasset -i crosschain -n 4 -r -1 -s ERC.SMT -v 1 test1 test123456
mvs-cli issue test1 test123456 ERC.SMT
```


