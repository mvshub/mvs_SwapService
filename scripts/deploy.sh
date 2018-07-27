for i in `cat supported_tokens.txt`;do

local_path=~/swaptoken/$i/TokenDroplet
target_path=/home/ubuntu/swaptoken/$i

echo "deploy $i to ${target_path}";
ssh wallet_dev "test -d ${target_path} || mkdir -p ${target_path}"
rsync -avP --exclude '*.pyc' --exclude '*.log' ${local_path}  wallet_dev:${target_path}

done

