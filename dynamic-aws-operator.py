import boto3
import kopf
import json
import kubernetes
from kubernetes import config, client
import os
import yaml


config.load_config()


ec2_ids = []
ec2_states = []
availability_zones = []


def aws_connect():
    ec2 = boto3.client('ec2')
    data = ec2.describe_instances()

    inst_data = data['Reservations']

    for i in inst_data:
        zone = i['Instances'][0]['Placement']['AvailabilityZone']

        availability_zones.append(zone)

        ec2_id = i['Instances'][0]['InstanceId']
        ec2_state = i['Instances'][0]['State']['Name'].capitalize()
        ec2_states.append(ec2_state)
        ec2_ids.append(ec2_id)



@kopf.on.create('listinstances')
def crd_create(spec, **kwargs):
    global resource_kind
    resource_kind = kwargs['body']['kind']
    global resource_name
    resource_name = kwargs['body']['metadata']['name']
    print("Invoking Kopf Create functions and Looking for Child Resources")

    aws_connect()

    global num

    num = len(ec2_ids)

    i = 0
    while i < len(ec2_ids):
          manifest_instance = yaml.safe_load(f"""
                      apiVersion: aws.com/v1alpha1
                      kind: Instance
                      metadata:
                        name: {resource_name}-{i}
                      spec:
                        instanceId: {ec2_ids[i]}
                        instanceState: {ec2_states[i]}
                        instanceLocation: {availability_zones[i]}
                                """)
          i += 1

          crd_create = kubernetes.client.CustomObjectsApi()
          resource_create = crd_create.create_cluster_custom_object(group="aws.com", version="v1alpha1", plural="instances",
                                                        body= manifest_instance)
          print(f"Successfully Created Child Resources: {resource_name}-{i}")
    print("Completed Kopf Create Handler Successfully")
    return num

@kopf.timer('listinstances', interval=10, retries=1, idle=5, backoff=5)
def crd_patch(spec, num=len(ec2_ids), **kwargs):
    global resource_child_name
    
    resource_child_name = kwargs['body']['metadata']['name']
    print("Invoking Kopf Timer functions and Patching The Resources")
    ec2_ids.clear()
    ec2_states.clear()
    availability_zones.clear()
    aws_connect()

    
    if num ==len(ec2_ids):


         i = 0
         while i < len(ec2_ids):

               value = {'spec': {'instanceId': ec2_ids[i], 'instanceState': ec2_states[i],
                                                                    'instanceLocation': availability_zones[i]}}
               print("Below Spec will be Patched")
               print(value)


               crd_create = kubernetes.client.CustomObjectsApi()
               resource_patch = crd_create.patch_cluster_custom_object(group="aws.com", version="v1alpha1", plural="instances",
                                                        name=f'{resource_child_name}-{i}', body= value)
               i +=1
               print(f"Successfully Patched Spec for {resource_child_name}-{i}")
        

    else:

         delete_crd = kubernetes.client.CustomObjectsApi().delete_collection_cluster_custom_object(group="aws.com", version="v1alpha1", plural="instances")
 
         i = 0
         while i < len(ec2_ids):
            manifest_instance = yaml.safe_load(f"""
                             apiVersion: aws.com/v1alpha1
                             kind: Instance
                             metadata:
                               name: {resource_name}-{i}
                             spec:
                               instanceId: {ec2_ids[i]}
                               instanceState: {ec2_states[i]}
                               instanceLocation: {availability_zones[i]}
                                       """)
   
            i += 1

            crd_create = kubernetes.client.CustomObjectsApi()
            resource_create = crd_create.create_cluster_custom_object(group="aws.com", version="v1alpha1",
                                                                  plural="instances",
                                                                  body=manifest_instance)
            print(f"Successfully Created Child Resources: {resource_name}-{i}")
         if num is not None:
             num = len(ec2_ids)





print("Error! Did you activated kopf Timer or  Try Creating the Resource")
