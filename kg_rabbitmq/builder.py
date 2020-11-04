from typing import List, Optional

from kubragen import KubraGen
from kubragen.builder import Builder
from kubragen.configfile import ConfigFile, ConfigFileRender, ConfigFileRenderMulti, ConfigFileRender_SysCtl, \
    ConfigFileRender_RawStr
from kubragen.data import ValueData
from kubragen.exception import InvalidParamError, InvalidNameError
from kubragen.helper import LiteralStr, QuotedStr
from kubragen.kdata import IsKData
from kubragen.kdatahelper import KDataHelper_Volume
from kubragen.object import ObjectItem, Object
from kubragen.types import TBuild, TBuildItem

from .configfile import RabbitMQConfigFile
from .option import RabbitMQOptions


class RabbitMQBuilder(Builder):
    """
    RabbitMQ builder.

    Based on `rabbitmq/diy-kubernetes-examples <https://github.com/rabbitmq/diy-kubernetes-examples>`_.

    .. list-table::
        :header-rows: 1

        * - build
          - description
        * - BUILD_ACCESSCONTROL
          - creates service account, roles, and roles bindings
        * - BUILD_CONFIG
          - creates ConfigMap
        * - BUILD_SERVICE
          - creates StatefulSet and Services

    .. list-table::
        :header-rows: 1

        * - build item
          - description
        * - BUILDITEM_SERVICE_ACCOUNT
          - ServiceAccount
        * - BUILDITEM_ROLE
          - Role
        * - BUILDITEM_ROLE_BINDING
          - RoleBinding
        * - BUILDITEM_CONFIG
          - ConfigMap
        * - BUILDITEM_CONFIG_SECRET
          - Secret
        * - BUILDITEM_SERVICE_HEADLESS
          - Service (headless, internal, needed for RabbitMQ)
        * - BUILDITEM_STATEFULSET
          - StatefulSet
        * - BUILDITEM_SERVICE
          - Service (for application use)

    .. list-table::
        :header-rows: 1

        * - object name
          - description
          - default value
        * - config
          - ConfigMap
          - ```<basename>-config```
        * - config-secret
          - Secret
          - ```<basename>-config-secret```
        * - service-headless
          - Service (headless)
          - ```<basename>-headless```
        * - service
          - Service
          - ```<basename>```
        * - service-account
          - ServiceAccount
          - ```<basename>```
        * - role
          - Role
          - ```<basename>```
        * - role-binding
          - RoleBinding
          - ```<basename>```
        * - statefulset
          - StatefulSet
          - ```<basename>```
        * - pod-label-all
          - label *app* to be used by selection
          - ```<basename>```
    """

    options: RabbitMQOptions
    configfile: ConfigFile
    configfilerender: ConfigFileRender
    _namespace: str

    SOURCE_NAME = 'kg_rabbitmq'

    BUILD_ACCESSCONTROL: TBuild = 'accesscontrol'
    BUILD_CONFIG: TBuild = 'config'
    BUILD_SERVICE: TBuild = 'service'

    BUILDITEM_SERVICE_ACCOUNT: TBuildItem = 'service-account'
    BUILDITEM_ROLE: TBuildItem = 'role'
    BUILDITEM_ROLE_BINDING: TBuildItem = 'role-binding'
    BUILDITEM_CONFIG: TBuildItem = 'config'
    BUILDITEM_CONFIG_SECRET: TBuildItem = 'config-secret'
    BUILDITEM_SERVICE_HEADLESS: TBuildItem = 'service-headless'
    BUILDITEM_STATEFULSET: TBuildItem = 'statefulset'
    BUILDITEM_SERVICE: TBuildItem = 'service'

    def __init__(self, kubragen: KubraGen, options: Optional[RabbitMQOptions] = None):
        super().__init__(kubragen)
        if options is None:
            options = RabbitMQOptions()
        self.options = options

        self._namespace = self.option_get('namespace')
        self.configfile = self.option_get('config.rabbitmq_conf')
        if self.configfile is None:
            self.configfile = RabbitMQConfigFile()
        self.configfilerender = ConfigFileRenderMulti([
            ConfigFileRender_SysCtl(),
            ConfigFileRender_RawStr()
        ])

        if self.option_get('config.authorization.serviceaccount_create') is not False:
            serviceaccount_name = self.basename()
        else:
            serviceaccount_name = self.option_get('config.authorization.serviceaccount_use')
            if serviceaccount_name == '':
                serviceaccount_name = None

        if self.option_get('config.authorization.roles_create') is not False:
            role_name = self.basename()
        else:
            role_name = None

        if self.option_get('config.authorization.roles_bind') is not False:
            if serviceaccount_name is None:
                raise InvalidParamError('To bind roles a service account is required')
            if role_name is None:
                raise InvalidParamError('To bind roles the role must be created')
            rolebinding_name = self.basename()
        else:
            rolebinding_name = None

        self.object_names_update({
            'config': self.basename('-config'),
            'config-secret': self.basename('-config-secret'),
            'service-headless': self.basename('-headless'),
            'service': self.basename(),
            'service-account': serviceaccount_name,
            'role': role_name,
            'role-binding': rolebinding_name,
            'statefulset': self.basename(),
            'pod-label-app': self.basename(),
        })

    def option_get(self, name: str):
        return self.kubragen.option_root_get(self.options, name)

    def basename(self, suffix: str = ''):
        return '{}{}'.format(self.option_get('basename'), suffix)

    def namespace(self):
        return self._namespace

    def build_names(self) -> List[TBuild]:
        return [self.BUILD_ACCESSCONTROL, self.BUILD_CONFIG, self.BUILD_SERVICE]

    def build_names_required(self) -> List[TBuild]:
        ret = [self.BUILD_CONFIG, self.BUILD_SERVICE]
        if self.option_get('config.authorization.serviceaccount_create') is not False or \
                self.option_get('config.authorization.roles_create') is not False:
            ret.append(self.BUILD_ACCESSCONTROL)
        return ret

    def builditem_names(self) -> List[TBuildItem]:
        return [
            self.BUILDITEM_SERVICE_ACCOUNT,
            self.BUILDITEM_ROLE,
            self.BUILDITEM_ROLE_BINDING,
            self.BUILDITEM_CONFIG,
            self.BUILDITEM_CONFIG_SECRET,
            self.BUILDITEM_SERVICE_HEADLESS,
            self.BUILDITEM_STATEFULSET,
            self.BUILDITEM_SERVICE,
        ]

    def internal_build(self, buildname: TBuild) -> List[ObjectItem]:
        if buildname == self.BUILD_ACCESSCONTROL:
            return self.internal_build_accesscontrol()
        elif buildname == self.BUILD_CONFIG:
            return self.internal_build_config()
        elif buildname == self.BUILD_SERVICE:
            return self.internal_build_service()
        else:
            raise InvalidNameError('Invalid build name: "{}"'.format(buildname))

    def internal_build_accesscontrol(self) -> List[ObjectItem]:
        ret = []

        if self.option_get('config.authorization.serviceaccount_create') is not False:
            ret.extend([
                Object({
                    'apiVersion': 'v1',
                    'kind': 'ServiceAccount',
                    'metadata': {
                        'name': self.object_name('service-account'),
                        'namespace': self.namespace(),
                    }
                }, name=self.BUILDITEM_SERVICE_ACCOUNT, source=self.SOURCE_NAME, instance=self.basename()),
            ])

        if self.option_get('config.authorization.roles_create') is not False:
            ret.extend([
                Object({
                    'kind': 'Role',
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'metadata': {
                        'name': self.object_name('role'),
                        'namespace': self.namespace(),
                    },
                    'rules': [{'apiGroups': [''], 'resources': ['endpoints'], 'verbs': ['get']},
                              {'apiGroups': [''], 'resources': ['events'], 'verbs': ['create']}]
                }, name=self.BUILDITEM_ROLE, source=self.SOURCE_NAME, instance=self.basename()),
            ])

        if self.option_get('config.authorization.roles_bind') is not False:
            ret.extend([
                Object({
                    'kind': 'RoleBinding',
                    'apiVersion': 'rbac.authorization.k8s.io/v1beta1',
                    'metadata': {
                        'name': self.object_name('role-binding'),
                        'namespace': self.namespace(),
                    },
                    'subjects': [{
                        'kind': 'ServiceAccount',
                        'name': self.object_name('service-account'),
                    }],
                    'roleRef': {
                        'apiGroup': 'rbac.authorization.k8s.io',
                        'kind': 'Role',
                        'name': self.object_name('role'),
                    }
                }, name=self.BUILDITEM_ROLE_BINDING, source=self.SOURCE_NAME, instance=self.basename())
            ])

        return ret

    def internal_build_config(self) -> List[ObjectItem]:
        ret = [Object({
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': self.object_name('config'),
                'namespace': self.namespace(),
            },
            'data': {
                'enabled_plugins': LiteralStr('[{}].'.format(', '.join(self.option_get('config.enabled_plugins')))),
                # 'rabbitmq.conf': LiteralStr(self.file_rabbitmq_conf())
                # 'rabbitmq.conf': LiteralStr(self.configfile.get_value(self))
                'rabbitmq.conf': LiteralStr(self.configfilerender.render(self.configfile.get_value(self))),
            }
        }, name=self.BUILDITEM_CONFIG, source=self.SOURCE_NAME, instance=self.basename())]

        config_secret = {}
        if not IsKData(self.option_get('config.erlang_cookie')):
            config_secret.update({
                'erlang_cookie': self.kubragen.secret_data_encode(self.option_get('config.erlang_cookie')),
            })

        if not IsKData(self.option_get('config.load_definitions')):
            if self.option_get('config.load_definitions') is not None:
                config_secret.update({
                    'load_definition.json': self.kubragen.secret_data_encode(self.option_get('config.load_definitions')),
                })

        if len(config_secret) > 0:
            ret.append(Object({
                'apiVersion': 'v1',
                'kind': 'Secret',
                'metadata': {
                    'name': self.object_name('config-secret'),
                    'namespace': self.namespace(),
                },
                'type': 'Opaque',
                'data': config_secret,
            }, name=self.BUILDITEM_CONFIG_SECRET, source=self.SOURCE_NAME, instance=self.basename()))

        return ret

    def internal_build_service(self) -> List[ObjectItem]:
        ret = []
        ret.extend([Object({
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': self.object_name('service-headless'),
                'namespace': self.namespace(),
            },
            'spec': {
                'clusterIP': 'None',
                'ports': [{
                    'name': 'epmd',
                    'port': 4369,
                    'protocol': 'TCP',
                    'targetPort': 4369
                },
                {
                    'name': 'cluster-links',
                    'port': 25672,
                    'protocol': 'TCP',
                    'targetPort': 25672
                }],
                'selector': {
                    'app': self.object_name('pod-label-app'),
                },
                'type': 'ClusterIP',
                'sessionAffinity': 'None'
            }
        }, name=self.BUILDITEM_SERVICE_HEADLESS, source=self.SOURCE_NAME, instance=self.basename()), Object({
            'apiVersion': 'apps/v1',
            'kind': 'StatefulSet',
            'metadata': {
                'name': self.object_name('statefulset'),
                'namespace': self.namespace(),
                'labels': {
                    'app': self.object_name('pod-label-app'),
                },
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': self.object_name('pod-label-app'),
                    }
                },
                'serviceName': self.object_name('service-headless'),
                'replicas': 1,
                'template': {
                    'metadata': {
                        'name': self.object_name('pod-label-app'),
                        'namespace': self.namespace(),
                        'labels': {
                            'app': self.object_name('pod-label-app'),
                        },
                        'annotations': ValueData({
                            'prometheus.io/scrape': QuotedStr('true'),
                            'prometheus.io/path': QuotedStr('/metrics'),
                            'prometheus.io/port': QuotedStr('15692'),
                        }, enabled=self.option_get('config.enable_prometheus') is not False and self.option_get('config.prometheus_annotation') is not False),
                    },
                    'spec': {
                        'initContainers': [{
                            'name': 'rabbitmq-config',
                            'image': self.option_get('container.busybox'),
                            'securityContext': {
                                'runAsUser': 0,
                                'runAsGroup': 0
                            },
                            'volumeMounts': [{
                                'name': 'rabbitmq-config',
                                'mountPath': '/tmp/rabbitmq'
                            },
                            {
                                'name': 'rabbitmq-config-rw',
                                'mountPath': '/etc/rabbitmq'
                            },
                            {
                                'name': 'rabbitmq-config-erlang-cookie',
                                'mountPath': '/tmp/rabbitmq-cookie'
                            }],
                            'command': ['sh',
                                        '-c',
                                        'cp '
                                        '/tmp/rabbitmq/rabbitmq.conf '
                                        '/etc/rabbitmq/rabbitmq.conf '
                                        "&& echo '' "
                                        '>> '
                                        '/etc/rabbitmq/rabbitmq.conf; '
                                        'cp '
                                        '/tmp/rabbitmq/enabled_plugins '
                                        '/etc/rabbitmq/enabled_plugins; '
                                        'mkdir -p '
                                        '/var/lib/rabbitmq; '
                                        'cp '
                                        '/tmp/rabbitmq-cookie/erlang_cookie '
                                        '/var/lib/rabbitmq/.erlang.cookie; '
                                        'chmod 600 '
                                        '/var/lib/rabbitmq/.erlang.cookie; '
                                        'chown '
                                        '999.999 '
                                        '/etc/rabbitmq/rabbitmq.conf '
                                        '/etc/rabbitmq/enabled_plugins '
                                        '/var/lib/rabbitmq '
                                        '/var/lib/rabbitmq/.erlang.cookie']
                        }],
                        'volumes': [
                            {
                                'name': 'rabbitmq-config',
                                'configMap': {
                                    'name': self.object_name('config'),
                                    'optional': False,
                                    'items': [{
                                        'key': 'enabled_plugins',
                                        'path': 'enabled_plugins'
                                    },
                                        {
                                            'key': 'rabbitmq.conf',
                                            'path': 'rabbitmq.conf'
                                        }]
                                }
                            },
                            {
                                'name': 'rabbitmq-config-rw',
                                'emptyDir': {}
                            },
                            KDataHelper_Volume.info(base_value={
                                'name': 'rabbitmq-config-erlang-cookie',
                            }, kdata=self.option_get('config.erlang_cookie'), default_value={
                                'secret': {
                                    'secretName': self.object_name('config-secret'),
                                    'items': [{
                                        'key': 'erlang_cookie',
                                        'path': 'erlang_cookie',
                                    }]
                                },
                            }, key_path='erlang_cookie'),
                            KDataHelper_Volume.info(base_value={
                                'name': 'rabbitmq-config-load-definition',
                            }, kdata=self.option_get('config.load_definitions'), default_value={
                                'secret': {
                                    'secretName': self.object_name('config-secret'),
                                    'items': [{
                                        'key': 'load_definition.json',
                                        'path': 'load_definition.json',
                                    }]
                                }
                            }, key_path='load_definition.json',
                                enabled=self.option_get('config.load_definitions') is not None),
                            KDataHelper_Volume.info(base_value={
                                'name': 'rabbitmq-data',
                            }, kdata=self.option_get('kubernetes.volumes.data')),
                        ],
                        'serviceAccountName': ValueData(value=self.object_name('service-account'),
                                                        enabled=self.object_name('service-account') is not None),
                        'securityContext': {
                            'fsGroup': 999,
                            'runAsUser': 999,
                            'runAsGroup': 999
                        },
                        'containers': [{
                            'name': 'rabbitmq',
                            'image': self.option_get('container.rabbitmq'),
                            'volumeMounts': [{
                                'name': 'rabbitmq-config-rw',
                                'mountPath': '/etc/rabbitmq'
                            },
                            {
                                'name': 'rabbitmq-data',
                                'mountPath': '/var/lib/rabbitmq/mnesia'
                            }, ValueData(value={
                                'name': 'rabbitmq-config-load-definition',
                                'mountPath': '/etc/rabbitmq-load-definition',
                                'readOnly': True,
                            }, enabled=self.option_get('config.load_definitions') is not None)],
                            'ports': [{
                                'name': 'amqp',
                                'containerPort': 5672,
                                'protocol': 'TCP'
                            },
                            {
                                'name': 'management',
                                'containerPort': 15672,
                                'protocol': 'TCP'
                            },
                            ValueData(value={
                                'name': 'prometheus',
                                'containerPort': 15692,
                                'protocol': 'TCP'
                            }, enabled=self.option_get('config.enable_prometheus') is not False),
                            {
                                'name': 'epmd',
                                'containerPort': 4369,
                                'protocol': 'TCP'
                            }],
                            'livenessProbe': {
                                'exec': {
                                    'command': ['rabbitmq-diagnostics', 'status']
                                },
                                'initialDelaySeconds': 60,
                                'periodSeconds': 60,
                                'timeoutSeconds': 15
                            },
                            'readinessProbe': {
                                'exec': {
                                    'command': ['rabbitmq-diagnostics', 'ping']
                                },
                                'initialDelaySeconds': 20,
                                'periodSeconds': 60,
                                'timeoutSeconds': 10
                            },
                            'resources': ValueData(value=self.option_get('kubernetes.resources.statefulset'),
                                                   disabled_if_none=True),
                        }]
                    }
                }
            }
        }, name=self.BUILDITEM_STATEFULSET, source=self.SOURCE_NAME, instance=self.basename()), Object({
            'kind': 'Service',
            'apiVersion': 'v1',
            'metadata': {
                'name': self.object_name('service'),
                'namespace': self.namespace(),
                'labels': {
                    'app': self.object_name('pod-label-app')
                },
            },
            'spec': {
                'type': 'ClusterIP',
                'ports': [{
                    'name': 'http',
                    'protocol': 'TCP',
                    'port': 15672,
                }, ValueData(value={
                    'name': 'prometheus',
                    'protocol': 'TCP',
                    'port': 15692
                }, enabled=self.option_get('config.enable_prometheus') is not False), {
                    'name': 'amqp',
                    'protocol': 'TCP',
                    'port': 5672
                }],
                'selector': {
                    'app': self.object_name('pod-label-app')
                }
            }
        }, name=self.BUILDITEM_SERVICE, source=self.SOURCE_NAME, instance=self.basename())])
        return ret
