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