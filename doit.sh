CC=FR
YYYY=2022
MM=03
DD=19
TOP=30

HEGE_HOME=/Users/eaben/work/country-as-hegemony

$HEGE_HOME/country-hege -t $TOP -s $YYYY-$MM-$DD $CC | tee ./input-asns.txt
#for i in /mnt/ris/rrc01/$YYYY.$MM/bview.$YYYY$MM$DD.0000.gz
./create-graph.py $CC $YYYY-$MM-$DD

