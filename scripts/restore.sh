for i in `cat supported_tokens.txt`;do

echo "restore $i";
cp -v ~/swaptoken/config/$i.json ~/swaptoken/$i/TokenDroplet/config/service.json

done
