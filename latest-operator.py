import boto3
import kopf
import json
import kubernetes
from kubernetes import config, client
import os
import yaml

# os.putenv("AWS_DEFAULT_REGION", "ap-south-1")

# config.load_config()
# config.load_kube_config(config_file='./config')
config.load_config()

# manifest_instance = yaml.safe_load(f"""
#                     apiVersion: aws.com/v1alpha1
#                     kind: Instance
#                     metadata:
#                       name: {resource_name}
#                     spec:
#                       instanceList: true
#                       showTags: true
#                               """)
# print(manifest_instance)

# crd_create = kubernetes.client.CustomObjectsApi()
# resource_create = crd_create.create_cluster_custom_object(group="aws.com", version="v1alpha1", plural="instances", body=manifest_instance)
# print(resource_create)


ec2_ids = []
ec2_states = []
availability_zones = []


def aws_connect():
    ec2 = boto3.client('ec2')
    data = ec2.describe_instances()
    # print(data)
    inst_data = data['Reservations']
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


aws_connect()


@kopf.on.create('instances')
def crd(spec, **kwargs):
    global resource_name
    resource_name = kwargs['body']['metadata']['name']
    print("Invoking Crd functions")
    aws_connect()


#kopf.adopt()
i = 0
while i < len(ec2_ids):
    manifest_instance = yaml.safe_load(f"""
                      apiVersion: aws.com/v1alpha1
                      kind: Instance
                      metadata:
                        name: vinay-{i}
                      spec:
                        instanceId: {ec2_ids[i]}
                        instanceState: {ec2_states[i]}
                                """)
    print(manifest_instance)
    i += 1

    #crd_create = kubernetes.client.CustomObjectsApi()
    #resource_create = crd_create.create_cluster_custom_object(group="aws.com", version="v1alpha1", plural="instances", body=manifest_instance)
    #print(resource_create)

# zone_patch = '{"spec": {"location": "' + f'{availability_zones[0].capitalize()}' + '"}}'
