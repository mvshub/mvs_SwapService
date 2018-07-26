target_path=~/deposit/

for i in `cat coins.sh`;do
echo $i;
cp ~/deposit/config/$i.json ${target_path}$i/wallet_service/config/service.json && cd  ~/deposit/$i/wallet_service  && nohup python main.py $i &


done
