for i in `cat coins.sh`;do

 #echo $i'ddd';
 echo $i;
cp ~/deposit/config/$i.json ~/deposit/$i/wallet_service/config/service.json && cd  ~/deposit/$i


done