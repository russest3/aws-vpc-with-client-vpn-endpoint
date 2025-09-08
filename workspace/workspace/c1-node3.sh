#!/bin/bash
hostname c1-node3
echo 'c1-node3' > /etc/hostname
# add-apt-repository -y ppa:deadsnakes/ppa
# apt install -y python3.10 python3-pip python3-apt containerd apt-transport-https ca-certificates curl gpg
# apt update -y
# apt upgrade -y
# sed -i 's/^#\s*PasswordAuthentication.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
# sed -i 's/^KbdInteractiveAuthentication.*$/#KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
# systemctl restart sshd
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
# reboot