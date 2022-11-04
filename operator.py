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
availability_zones = []


def aws_connect():
     ec2 = boto3.client('ec2')
     data = ec2.describe_instances()
     #print(data)
     inst_data =  data['Reservations']
     print(inst_data)
     for i in inst_data:
           zone = i['Instances'][0]['Placement']['AvailabilityZone']
           print(zone)
           availability_zones.append(zone)

           ec2_id = i['Instances'][0]['InstanceId']
           ec2_state = i['Instances'][0]['State']['Name']
           ec2_states.append(ec2_state)
           ec2_ids.append(ec2_id)

     print(availability_zones)
     print(ec2_ids)
     print(ec2_states)


@kopf.on.create('instances')
def crd(spec, **kwargs):
    resource_name = kwargs['body']['metadata']['name']
    print("Invoking Crd functions")
    aws_connect()

    state_patch = '{"spec": {"states": "' + f'{ec2_states[0].capitalize()}' + '"}}'
    crd_state_patch = kubernetes.client.CustomObjectsApi().patch_cluster_custom_object(group='aws.com', version='v1alpha1',
                                                                                 plural='instances',
                                                                                 name=f'{resource_name}',
                                                                                 body=json.loads(state_patch))
    print(crd_state_patch)
    zone_patch = '{"spec": {"location": "' + f'{availability_zones[0].capitalize()}' + '"}}'
    crd_zone_patch = kubernetes.client.CustomObjectsApi().patch_cluster_custom_object(group='aws.com', version='v1alpha1',
                                                                                 plural='instances',
                                                                                 name=f'{resource_name}',
                                                                                 body=json.loads(zone_patch))
    print(crd_zone_patch)



#value = '{"spec": {"states": "'+f'{ec2_states[0].capitalize()}'+'"}}'
