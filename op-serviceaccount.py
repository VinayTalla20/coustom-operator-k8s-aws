import boto3
import kopf
import json
import kubernetes
from kubernetes import config, client
import os
import yaml


def main():
    # Define the barer token we are going to use to authenticate.
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IlkxYzh6a0RzVVo1OVNJNzhYRnBhUFBTaGJ0RDM2S3BJX1RSWEVuWE84dlkifQ.eyJhdWQiOlsiaHR0cHM6Ly9rdWJlcm5ldGVzLmRlZmF1bHQuc3ZjLmNsdXN0ZXIubG9jYWwiXSwiZXhwIjoxNjk5NDQ0NDM2LCJpYXQiOjE2Njc5MDg0MzYsImlzcyI6Imh0dHBzOi8va3ViZXJuZXRlcy5kZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsIiwia3ViZXJuZXRlcy5pbyI6eyJuYW1lc3BhY2UiOiJhd3Mtb3BlcmF0b3IiLCJwb2QiOnsibmFtZSI6ImN1cmwtcG9kIiwidWlkIjoiZTkxNTg4N2UtZGRmZC00ODU5LTliZmMtYzAzYTc4NzU1ZjY3In0sInNlcnZpY2VhY2NvdW50Ijp7Im5hbWUiOiJhd3Mtb3BlcmF0b3IiLCJ1aWQiOiIyNzQyMDVhYy0xYjI4LTQwZjgtYjYzMi00ODAwYmU5ZWMzOWMifSwid2FybmFmdGVyIjoxNjY3OTEyMDQzfSwibmJmIjoxNjY3OTA4NDM2LCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6YXdzLW9wZXJhdG9yOmF3cy1vcGVyYXRvciJ9.dLjAeS9_uMu2BZ7kDkusCSPwqHWlir1AOXs09_gvty-fD5z5UnR--oQvJxxEE0BacN-PbnilM-d6DyY9lyW5KlFzxQVZSvtca65KeUGFq6DslIqz1rElQbssmYYdj8eLhiDSVVgd5RPW__0NvklTNd7BPxKg6kkyDbud-s00i2ul5zyVWm0uPHIf-GQ3D66q_wdIdXAx6exN1z4xd3FC23JltLzKPLr9vln92mG36_hrKH8imDu-iw4hpCtVbv2-_PWN6b_jI2i0uaKbLbmXurJJQFbxttfZ0M0EgRgh135Mi_Q_4DxGVhvDSO8YxzM68EcNIaMpyS4oKbsIjMVt6g"

    # Create a configuration object
    connection = client.Configuration()

    # Specify the endpoint of your Kube cluster
    connection.host = "https://kubernetes.default.svc.cluster.local"

    # connection.verify_ssl = False

    # Nevertheless if you want to do it you can with these 2 parameters
    connection.verify_ssl = True

    # ssl_ca_cert is the filepath to the file that contains the certificate.
    connection.ssl_ca_cert = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

    connection.api_key = {"authorization": "Bearer " + token}

    # Create a ApiClient with our config
    global api_connection
    api_connection = client.ApiClient(connection)

    v1 = kubernetes.client.CustomObjectsApi(api_connection)
    ret = v1.list_cluster_custom_object(group="aws.com", version="v1alpha1", plural="instances")


main()

num = None
ec2_ids = []
ec2_states = []
availability_zones = []


def aws_connect():
    ec2_ids.clear()
    availability_zones.clear()
    ec2_states.clear()

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

    return len(ec2_ids)


@kopf.on.create('listinstances')
def crd_create(spec, **kwargs):
    global resource_kind
    resource_kind = kwargs['body']['kind']
    global resource_name
    resource_name = kwargs['body']['metadata']['name']
    print("Invoking Kopf Create functions and Looking for Child Resources")

    aws_connect()

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
        kopf.adopt(manifest_instance)


        crd_create = kubernetes.client.CustomObjectsApi(api_connection)
        resource_create = crd_create.create_cluster_custom_object(group="aws.com", version="v1alpha1",
                                                                  plural="instances",
                                                                  body=manifest_instance)
        print(f"Successfully Created Child Resources: {resource_name}-{i}")
        i += 1
    print("Completed Kopf Create Handler Successfully")
    return num


num = aws_connect()


def update_value():
    global num
    if num is not None:
        num = aws_connect()
    return num


@kopf.timer('listinstances', interval=10, retries=1, idle=5, backoff=5)
def crd_patch(spec, **kwargs):
    print(num)
    global resource_child_name
    print("Printing num value before method initiated AWS")

    resource_child_name = kwargs['body']['metadata']['name']
    print("Invoking Kopf Timer functions and Patching The Resources")
    ec2_ids.clear()
    ec2_states.clear()
    availability_zones.clear()

    aws_connect()


    if num == len(ec2_ids):

        i = 0
        while i < len(ec2_ids):
            value = {'spec': {'instanceId': ec2_ids[i], 'instanceState': ec2_states[i],
                              'instanceLocation': availability_zones[i]}}
            print("Below Spec will be Patched")
            print(value)

            crd_create = kubernetes.client.CustomObjectsApi(api_connection)

            resource_patch = crd_create.patch_cluster_custom_object(group="aws.com", version="v1alpha1",
                                                                    plural="instances",
                                                                    name=f'{resource_child_name}-{i}', body=value)

            print(f"Successfully Patched Spec for {resource_child_name}-{i}")
            i += 1

    else:

        delete_crd = kubernetes.client.CustomObjectsApi(api_connection).delete_collection_cluster_custom_object(group="aws.com",
                                                                                                  version="v1alpha1",
                                                                                                  plural="instances")
        print(delete_crd)
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



            crd_create = kubernetes.client.CustomObjectsApi(api_connection)
            resource_create = crd_create.create_cluster_custom_object(group="aws.com", version="v1alpha1",
                                                                      plural="instances",
                                                                      body=manifest_instance)
            print(f"Successfully Created Child Resources: {resource_name}-{i}")
            i +=1

        print("Printing No.of Instances After Addition of Instances")
        print(num)
        update_value()


print("Error! Did you activated kopf Timer or  Try Creating our Resources")
