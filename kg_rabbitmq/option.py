import uuid
from typing import Sequence, Optional, Any

from kubragen.configfile import ConfigFile
from kubragen.kdata import KData_Secret
from kubragen.kdatahelper import KDataHelper_Volume
from kubragen.option import OptionDef, OptionDefFormat
from kubragen.options import Options


class RabbitMQOptions(Options):
    """
    Options for the RabbitMQ builder.

    .. list-table::
        :header-rows: 1

        * - option
          - description
          - allowed types
          - default value
        * - basename
          - object names prefix
          - str
          - ```rabbitmq```
        * - namespace
          - namespace
          - str
          - ```rabbitmq```
        * - config |rarr| enabled_plugins
          - enabled plugins
          - Sequence
          - ```['rabbitmq_peer_discovery_k8s']```
        * - config |rarr| rabbitmq_conf
          - rabbitmq.conf file
          - :class:`kubragen.configfile.ConfigFile`
          - :class:`kg_rabbitmq.RabbitMQConfigFile`
        * - config |rarr| erlang_cookie
          - erlang cookie
          - str, dict, :class:`KData_Secret`
          - ```uuid.uuid4()```
        * - config |rarr| loglevel
          - server log level
          - str
          - ```info```
        * - config |rarr| enable_prometheus
          - enable prometheus
          - bool
          - ```True```
        * - config |rarr| prometheus_annotation
          - add prometheus annotations
          - bool
          - ```False```
        * - config |rarr| load_definitions
          - load RabbitMQ definitions
          - bool, :class:`KData_Secret`
          -
        * - config |rarr| authorization |rarr| serviceaccount_create
          - whether to create a service account
          - bool
          - ```True```
        * - config |rarr| authorization |rarr| serviceaccount_use
          - service account to use if not creating
          - str
          -
        * - config |rarr| authorization |rarr| roles_create
          - whether create roles
          - bool
          - ```True```
        * - config |rarr| authorization |rarr| roles_bind
          - whether to bind roles to service account
          - bool
          - ```True```
        * - container |rarr| busybox
          - busybox container image
          - str
          - ```busybox:<version>```
        * - container |rarr| rabbitmq
          - rabbitmq container image
          - str
          - ```rabbitmq:<version>```
        * - kubernetes |rarr| volumes |rarr| data
          - Kubernetes data volume
          - dict, :class:`KData_Value`, :class:`KData_ConfigMap`, :class:`KData_Secret`
          -
        * - kubernetes |rarr| resources |rarr| statefulset
          - Kubernetes StatefulSet resources
          - dict
          -
    """
    def define_options(self) -> Optional[Any]:
        """
        Declare the options for the RabbitMQ builder.

        :return: The supported options
        """
        return {
            'basename': OptionDef(required=True, default_value='rabbitmq', allowed_types=[str]),
            'namespace': OptionDef(required=True, default_value='rabbitmq', allowed_types=[str]),
            'config': {
                'enabled_plugins': OptionDef(default_value=['rabbitmq_peer_discovery_k8s'], allowed_types=[Sequence]),
                'rabbitmq_conf': OptionDef(allowed_types=[ConfigFile]),
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
