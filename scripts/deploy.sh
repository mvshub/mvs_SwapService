destiny_path=/home/ubuntu/deposit
local_path=/home/jiang/PycharmProjects/wallet_service
for i in `cat coins.sh`;do
target_path=${destiny_path}/$i
echo ${target_path};
ssh wallet_dev  "test -d ${target_path} || mkdir -p ${target_path}"
rsync -avP --exclude '*.pyc' --exclude '*.log' ${local_path}  wallet_dev:${target_path}

done

