import boto3
import kopf
import json
import kubernetes

from kubernetes import config, client
import os

config.load_config()
#config.load_kube_config(config_file='./config')

ec2_ids = []
ec2_states = []


def aws_connect():
     ec2 = boto3.client('ec2')
     data = ec2.describe_instances()
     #print(data)
     inst_data =  data['Reservations']
     #print(inst_data)
     for i in inst_data:
           ec2_id = (i['Instances'][0]['InstanceId'])
           ec2_state = i['Instances'][0]['State']['Name']
           ec2_states.append(ec2_state)
           ec2_ids.append(ec2_id)
     print(ec2_ids)
     print(ec2_states)



@kopf.on.create('instances')
def crd(spec, **kwargs):
    resource_name = kwargs['body']['metadata']['name']
    print("Invoking Crd functions")
    aws_connect()
    crd_patch_fn()

#aws_connect()


#print(ec2_states[0])
#print(ec2_ids[0])

#value = '{"spec": {"states": ' + f'{ec2_states[0]}' + '}}'

#print(value)
def crd_patch_fn():
    #resource_name = crd.kwargs['body']['metadata']['name']
    value = '{"spec": {"states": "Running"}}'
    #crd_list = kubernetes.client.CustomObjectsApi().list_cluster_custom_object(group="aws.com", version="v1alpha1",
    #                                                                           plural="instances")
    #print(crd_list)

    #value = '{"spec": {"states": "running"}}'

    crd_patch = kubernetes.client.CustomObjectsApi().patch_cluster_custom_object(group='aws.com', version='v1alpha1',
                                                                                 plural='instances',
                                                                                 name='aws-instance',
                                                                                 body=json.loads(value))
    print(crd_patch)







"""
@kopf.on.create('instances')
def crd(spec, **kwargs):
    resource_name = kwargs['body']['metadata']['name']
    print("Invoking Crd functions")
    aws_connect()
    #crd_patch_fn()
"""
