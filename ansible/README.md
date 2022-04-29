## Ansible
### Example
```
# ansible-playbook
ansible-playbook ./playbook/demo_deploy_1_cp_files.yml --inventory-file=my.hosts
ansible-playbook ./playbook/demo_deploy_2_up_container.yml --inventory-file=my.hosts

```
## Release an updated version
1. docker build -t "mdaas_manager:2021.1.26" -f server_env/Dockerfile .
2. docker save "mdaas_manager:2021.1.26" | xz > ./mdaas_manager.tar.xz
3. use ansible to deploy `ansible-playbook ./playbook/demo_deploy_1_cp_files.yml --inventory-file=my.hosts`  
   use ansible to deploy `ansible-playbook ./playbook/demo_deploy_2_up_container.yml --inventory-file=my.hosts`
4. test service alive `http://0.0.0.0:9796/apidocs`