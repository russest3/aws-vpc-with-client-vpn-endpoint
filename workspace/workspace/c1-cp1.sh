#!/bin/bash
hostname c1-cp1
echo 'c1-cp1' > /etc/hostname
python3 -m venv .venv
source /.venv/bin/activate
python3 -m pip install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz
ln -s /.venv/bin/cfn-init /usr/local/bin/cfn-init
ln -s /.venv/bin/cfn-signal /usr/local/bin/cfn-signal
ln -s /.venv/bin/cfn-get-metadata /usr/local/bin/cfn-get-metadata
ln -s /.venv/bin/cfn-hup /usr/local/bin/cfn-hup
f"cfn-init --stack {stack_id} -r ControlNode --region us-east-2 || error_exit ‘Failed to run cfn-init’"
INIT_STATUS=$?
f"cfn-signal -e $INIT_STATUS --stack {stack_id} --resource {wait_condition} --region us-east-2"
exit $INIT_STATUS