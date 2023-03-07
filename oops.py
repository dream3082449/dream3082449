#!env python3
import sys
import openstack
import MySQLdb


openstack.enable_logging(True, stream=sys.stdout)


class oops_helper(object):

    def __init__(self, config):
        self.config = config
        self.mysql_conn = MySQLdb.connect(
            host=config.get('BillingDB', 'host'),
            port=int(config.get('BillingDB', 'port')),
            user=config.get('BillingDB', 'user'),
            password=config.get('BillingDB', 'password'),
            db=config.get('BillingDB', 'db_name')
        )
        self.mysql_cursor = self.mysql_conn.cursor()
        # Initialize connection
        self.conn = openstack.connect(cloud='openstack')
    

    def product_id_to_username(self, product_id, username_only=False):
        query = """SELECT i.account as id, u.email FROM item i LEFT JOIN user u on i.account=u.account WHERE i.id =%s"""
        self.mysql_cursor.execute(query, [product_id,])

        user_id, email = self.mysql_cursor.fetchone()
        username = "user_{0}".format(user_id)

        if username_only:
            return username
        else:
            return (user_id, username, email)

    def get_or_create_user(self, username, password, project_id, email):
        response = self.conn.identity.find_user(username, ignore_missing=True)
        if response:
            return response
        else:
            attrs = {
                'name': username,
                'password': password,
                'default_project_id': project_id,
                'email': email,
                'is_enabled': True
            }
            return self.conn.identity.create_user(**attrs)

    def get_or_create_project(self, project_name):
        resp = self.conn.identity.find_project(project_name)
        if resp:
            return resp
        else:
            attrs = {
                'domain_id': 'default',
                'name': project_name
            }
            return self.conn.create_project(**attrs)

    def update_project_quotas(self, project, params):
        project_id = project.get('id')
        current_quotas = self.conn.get_compute_quotas(project_id)

        if current_quotas.get('instances', 0) < 1:
            instances = 1
        else:
            instances = current_quotas.get('instances', 0) + 1

        if current_quotas.get('cores', 0) < params.get('cores'):
            cores = params.get('cores')
        else:
            cores = current_quotas.get('cores', 0) + params.get('cores')

        # bump Gigabytes to megabytes for OpenStack cli
        new_ram = params.get('ram') * 1024

        if current_quotas.get('ram', 0) < new_ram:
            ram = new_ram
        else:
            ram = current_quotas.get('ram', 0) + new_ram

        p = {
            "cores": cores,
            "instances": instances,
            "ram": ram,
        }
        self.conn.set_compute_quotas(project_id, **p)
        return True

    def create_flavor(self, project, params):
        flavor = self.conn.compute.create_flavor(**params)
        self.conn.add_flavor_access(flavor.id, project.id)
        return flavor

    def create_flavor_extra_specs(self, flavor, extra_specs):
        return self.conn.compute.create_flavor_extra_specs(flavor, extra_specs)

    def get_free_hive_gpu(conn):
        pass

    def list_images(self):
        return [(i.id, i.name, i.created_at) for i in sorted(self.conn.list_images(), key=lambda d:d['created_at'])]

    def create_instance(self, project, params):
        network = self.conn.network.find_network(self.config.get('openstack', 'use_network'))
        p = {"name": params.get("instance_name"),
             "image_id": params.get("os_image_id"),
             "flavor_id": params.get("flavor_id"),
             "disk_config": "AUTO",
             "admin_password": params.get("password"),
             "metadata": {
                "Server_Name": params.get("meta_name"),
                },
            "networks": [{"uuid": network.id}],
        }

        # logic for creating instance in project with hive gpu
        return self.conn.compute.create_server(**p)

    def get_instance_status(self, instance_id):
        """
            Return instance_status, instance or None, None
        """
        ii = self.conn.compute.find_server(instance_id)
        if ii:
            instance = ii.to_dict()
            # ACTIVE, BUILDING, DELETED, ERROR, HARD_REBOOT, PASSWORD,
            # PAUSED, REBOOT, REBUILD, RESCUED, RESIZED, REVERT_RESIZE,
            # SHUTOFF, SOFT_DELETED, STOPPED, SUSPENDED, UNKNOWN, or VERIFY_RESIZE
            return instance.get('status'), instance
        else:
            return None, None

    def remove_instance(self, instance_id):
        self.conn.compute.delete_server(instance_id)
        return True

    def resume_instance(self, instance_id):
        self.conn.compute.resume_server(instance_id)
        return True

    def suspend_instance(self, instance_id):
        self.conn.compute.suspend_server(instance_id)
        return True
