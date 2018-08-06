mysql -u root -p123456 <<EOF 2>/dev/null
drop database if exists wallet;
create database wallet charset utf8;
EOF
