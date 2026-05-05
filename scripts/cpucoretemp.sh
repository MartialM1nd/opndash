#!/bin/sh

cores=0

until [ $cores -eq 20 ]
do
        echo Core \#$cores: `sysctl -n dev.cpu.$cores.temperature`
        cores=`expr $cores + 1`
done

