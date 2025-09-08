#!/bin/bash
hostname c1-cp1
echo 'c1-cp1' > /etc/hostname
######## This should be in the image
# add-apt-repository -y ppa:deadsnakes/ppa
# apt install -y python3.10 python3-pip python3-apt python3-venv containerd apt-transport-https ca-certificates curl gpg net-tools
# apt update -y
# apt upgrade -y
# wget https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb
# dpkg -i -E ./amazon-cloudwatch-agent.deb
# cat << 'END_OF_FILE' > /opt/aws/amazon-cloudwatch-agent/bin/config.json
# {
#   "agent": {
#     "run_as_user": "cwagent"
#   },
#   "metrics": {
#     "metrics_collected": {
#       "procstat": [
#         {
#           "pid_file": "/var/run/sshd.pid",
#           "measurement": [
#             "cpu_usage",
#             "memory_rss"
#           ],
#           "metrics_collection_interval": 60
#         }
#       ]
#     }
#   }
# }
# END_OF_FILE
# /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json -s
# sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
# sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
# systemctl restart ssh
# echo 'overlay' > /etc/modules-load.d/k8s.conf
# echo 'br_netfilter' >> /etc/modules-load.d/k8s.conf
# modprobe overlay
# modprobe br_netfilter
# echo 'net.bridge.bridge-nf-call-iptables=1' | tee -a /etc/sysctl.conf
# echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.conf
# sed -i 's/^#net.ipv4.ip_forward.*$/net.ipv4.ip_forward=1/' /etc/sysctl.conf
# sysctl -p
# mkdir /etc/containerd
# containerd config default | tee /etc/containerd/config.toml
# sed -i 's/            SystemdCgroup = false/            SystemdCgroup = true/' /etc/containerd/config.toml
# curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
# echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
# apt update -y
# apt install -y kubelet kubeadm kubectl
# apt-mark hold kubelet kubeadm kubectl containerd
#############################
kubeadm init --kubernetes-version v1.30.5 --pod-network-cidr=10.244.0.0/16 --ignore-preflight-errors=NumCPU,Mem
mkdir -p /home/ubuntu/.kube
chown ubuntu:ubuntu /home/ubuntu/.kube
cp /etc/kubernetes/admin.conf /home/ubuntu/.kube/config
chown ubuntu:ubuntu /home/ubuntu/.kube/config
sudo su - ubuntu
cd /home/ubuntu
wget https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
kubectl apply -f /home/ubuntu/kube-flannel.yml
sleep 60
wget https://get.helm.sh/helm-v3.15.3-linux-amd64.tar.gz
tar -xvzf helm-v3.15.3-linux-amd64.tar.gz
cp linux-amd64/helm /usr/bin/helm
kubeadm token create --print-join-command
reboot