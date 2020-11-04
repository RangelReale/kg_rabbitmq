from kubragen import KubraGen
from kubragen.consts import PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE
from kubragen.data import ValueData
from kubragen.helper import QuotedStr
from kubragen.jsonpatch import FilterJSONPatches_Apply, FilterJSONPatch, ObjectFilter
from kubragen.kdata import KData_Secret
from kubragen.object import Object
from kubragen.option import OptionRoot
from kubragen.options import Options
from kubragen.output import OutputProject, OD_FileTemplate
from kubragen.outputimpl import OutputFile_ShellScript, OutputFile_Kubernetes, OutputDriver_Print
from kubragen.provider import Provider

from kg_rabbitmq import RabbitMQBuilder, RabbitMQOptions

kg = KubraGen(provider=Provider(PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE), options=Options({
    'namespaces': {
        'default': 'app-default',
        'monitoring': 'app-monitoring',
    },
}))

out = OutputProject(kg)

shell_script = OutputFile_ShellScript('create_gke.sh')
out.append(shell_script)

shell_script.append('set -e')

#
# OUTPUTFILE: app-namespace.yaml
#
file = OutputFile_Kubernetes('app-namespace.yaml')
out.append(file)

file.append(FilterJSONPatches_Apply([
    Object({
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': 'app-default',
            'annotations': {
                'will-not-output': ValueData(value='anything', enabled=False),
            }
        },
    }, name='ns-default', source='app'), Object({
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': 'app-monitoring',
        },
    }, name='ns-monitoring', source='app'),
], jsonpatches=[
    FilterJSONPatch(filters=ObjectFilter(names=['ns-monitoring']), patches=[
        {'op': 'add', 'path': '/metadata/annotations', 'value': {
                'kubragen.github.io/patches': QuotedStr('true'),
        }},
    ])
]))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

shell_script.append(f'kubectl config set-context --current --namespace=app-default')

#
# SETUP: rabbitmq-config.yaml
#
kg_rabbit = RabbitMQBuilder(kubragen=kg, options=RabbitMQOptions({
    'namespace': OptionRoot('namespaces.monitoring'),
    'basename': 'myrabbit',
    'config': {
        'erlang_cookie': KData_Secret(secretName='app-global-secrets', secretData='erlang_cookie'),
        'enable_prometheus': True,
        'prometheus_annotation': True,
        'authorization': {
            'serviceaccount_create': True,
            'roles_create': True,
            'roles_bind': True,
        },
    },
    'kubernetes': {
        'volumes': {
            'data': {
                'persistentVolumeClaim': {
                    'claimName': 'rabbitmq-storage-claim'
                }
            }
        },
        'resources': {
            'statefulset': {
                'requests': {
                    'cpu': '150m',
                    'memory': '300Mi'
                },
                'limits': {
                    'cpu': '300m',
                    'memory': '450Mi'
                },
            },
        },
    }
})).jsonpatches([
    FilterJSONPatch(filters={'names': [RabbitMQBuilder.BUILDITEM_SERVICE]}, patches=[
        {'op': 'check', 'path': '/spec/ports/0/name', 'cmp': 'equals', 'value': 'http'},
        {'op': 'replace', 'path': '/spec/type', 'value': 'LoadBalancer'},
    ]),
])

kg_rabbit.ensure_build_names(kg_rabbit.BUILD_ACCESSCONTROL, kg_rabbit.BUILD_CONFIG,
                             kg_rabbit.BUILD_SERVICE)

#
# OUTPUTFILE: rabbitmq-config.yaml
#
file = OutputFile_Kubernetes('rabbitmq-config.yaml')
out.append(file)

file.append(kg_rabbit.build(kg_rabbit.BUILD_ACCESSCONTROL, kg_rabbit.BUILD_CONFIG))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# OUTPUTFILE: rabbitmq.yaml
#
file = OutputFile_Kubernetes('rabbitmq.yaml')
out.append(file)

file.append(kg_rabbit.build(kg_rabbit.BUILD_SERVICE))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# OUTPUT
#
out.output(OutputDriver_Print())
# out.output(OutputDriver_Directory('/tmp/app-gke'))
