import uuid
from typing import Sequence

from kubragen.kdata import KData_Secret
from kubragen.kdatahelper import KDataHelper_Volume
from kubragen.option import OptionDef, OptionDefFormat
from kubragen.options import Options


class RabbitMQOptions(Options):
    def define_options(self):
        return {
            'basename': OptionDef(required=True, default_value='rabbitmq', allowed_types=[str]),
            'namespace': OptionDef(required=True, default_value='rabbitmq', allowed_types=[str]),
            'config': {
                'enabled_plugins': OptionDef(
                    default_value=['rabbitmq_peer_discovery_k8s', 'rabbitmq_management', 'rabbitmq_prometheus'],
                    allowed_types=[Sequence]),
                'rabbitmq_conf_extra': OptionDef(allowed_types=[str]),
                'erlang_cookie': OptionDef(required=True, default_value=str(uuid.uuid4()),
                                           format=OptionDefFormat.KDATA_VOLUME,
                                           allowed_types=[str, dict, KData_Secret]),
                'loglevel': OptionDef(required=True, default_value='info', allowed_types=[str]),
                'enable_prometheus': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                'prometheus_annotation': OptionDef(required=True, default_value=False, allowed_types=[bool]),
                'load_definitions': OptionDef(format=OptionDefFormat.KDATA_VOLUME, allowed_types=[str, KData_Secret]),
                'authorization': {
                    'serviceaccount_create': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                    'serviceaccount_use': OptionDef(allowed_types=[str]),
                    'roles_create': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                    'roles_bind': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                },
            },
            'container': {
                'busybox': OptionDef(required=True, default_value='busybox:1.32.0', allowed_types=[str]),
                'rabbitmq': OptionDef(required=True, default_value='rabbitmq:3.8.9-alpine', allowed_types=[str]),
            },
            'kubernetes': {
                'volumes': {
                    'data': OptionDef(required=True, format=OptionDefFormat.KDATA_VOLUME,
                                      allowed_types=[dict, *KDataHelper_Volume.allowed_kdata()]),
                },
                'resources': {
                    'statefulset': OptionDef(allowed_types=[dict]),
                }
            },
        }
