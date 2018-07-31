# wallet_deposit

#### Description
Cross chain

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
"mysql_passwd":"root123456",
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
```

3. create database 'wallet'
```
create database wallet charset utf8;
```

4. generate keys
```bash
mkdir /tmp/keys

#Generate a 2048 bit RSA Key
openssl genrsa -des3 -out /tmp/keys/private.pem 2048

#Export the RSA Public Key to a File
openssl rsa -in /tmp/keys/private.pem -outform PEM -pubout -out /tmp/keys/public.pem
```
modify key path in config/service.json.

#### Instructions

Run:
```bash
python3 main.py
```

Enable coin address in explorer:
```
http://127.0.0.1:8081/service/{coin_name}/address
```

#### Requirements
跨链代币透传系统开发需求，暂时命名 TokenDroplet 吧（三体中水滴计划，穿透力超强的水滴）

##### 功能性需求：
1. 代币映射，ERC20 <=> MST 的双向映射，建议做成可配置的
2. 开发 TokenDroplet 系统，支持双向透传，用户发起 ERC20 系代币转移时，可以透传到元界主网，反向成立，即 ERC20=>MST，MST=>ERC20
3. 系统暂时不需要UI界面，但是需要日报表给运营部
4. 要求服务的高可用，断点可恢复，跨链转账最好是事务性的。
5. 产品形式，Imtoken 钱包的 ERC20 可以转账到元界 MyETPWallet，反向也成立，用户仅需要在 Imtoken 和 MyETPWallet 中的备注栏填写目标主网的钱包地址

##### 建议的实现思路：
1. 首先是代币映射，圈定支持的代币范围
2. 从交易所获取充提币系统的源码，进行改良，然后加上一套高可用的python服务（Flask等其他），命名
3. 编写以太坊智能合约（跨链透传合约）
4. 注册元界跨链透传数字身份ETH，例如 ETH.xxx （xxx代表映射的ERC20代币符号）
5. 使用 TokenDroplet 连接上述智能合约和元界数字身份ETH.xxx

##### 未考虑清楚的点：
1. 使用销毁机制，还是冻结？
2. 开放增发逻辑吗？安全性如何保证
3. 透传的本质是？


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