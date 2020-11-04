# KubraGen Builder: RabbitMQ

[![PyPI version](https://img.shields.io/pypi/v/kg_rabbitmq.svg)](https://pypi.python.org/pypi/kg_rabbitmq/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/kg_rabbitmq.svg)](https://pypi.python.org/pypi/kg_rabbitmq/)

kg_rabbitmq is a builder for [KubraGen](https://github.com/RangelReale/kubragen) that deploys 
a [RabbitMQ](https://www.rabbitmq.com/) server in Kubernetes.

[KubraGen](https://github.com/RangelReale/kubragen) is a Kubernetes YAML generator library that makes it possible to generate
configurations using the full power of the Python programming language.

* Website: https://github.com/RangelReale/kg_rabbitmq
* Repository: https://github.com/RangelReale/kg_rabbitmq.git
* Documentation: https://kg_rabbitmq.readthedocs.org/
* PyPI: https://pypi.python.org/pypi/kg_rabbitmq

## Example

```python
from kubragen import KubraGen
from kubragen.consts import PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE
from kubragen.object import Object
from kubragen.option import OptionRoot
from kubragen.options import Options
from kubragen.output import OutputProject, OD_FileTemplate
from kubragen.outputimpl import OutputFile_ShellScript, OutputFile_Kubernetes, OutputDriver_Print
from kubragen.provider import Provider

from kg_rabbitmq import RabbitMQBuilder, RabbitMQOptions

kg = KubraGen(provider=Provider(PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE), options=Options({
    'namespaces': {
        'mon': 'app-monitoring',
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

file.append([
    Object({
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': 'app-monitoring',
        },
    }, name='ns-monitoring', source='app', instance='app')
])

out.append(file)
shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

shell_script.append(f'kubectl config set-context --current --namespace=app-monitoring')

#
# SETUP: rabbitmq
#
rabbit_config = RabbitMQBuilder(kubragen=kg, options=RabbitMQOptions({
    'namespace': OptionRoot('namespaces.mon'),
    'basename': 'myrabbit',
    'config': {
        'erlang_cookie': 'my-secret-cookie',
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
}))

rabbit_config.ensure_build_names(rabbit_config.BUILD_ACCESSCONTROL, rabbit_config.BUILD_CONFIG,
                                 rabbit_config.BUILD_SERVICE)

#
# OUTPUTFILE: rabbitmq-config.yaml
#
file = OutputFile_Kubernetes('rabbitmq-config.yaml')
out.append(file)

file.append(rabbit_config.build(rabbit_config.BUILD_ACCESSCONTROL, rabbit_config.BUILD_CONFIG))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# OUTPUTFILE: rabbitmq.yaml
#
file = OutputFile_Kubernetes('rabbitmq.yaml')
out.append(file)

file.append(rabbit_config.build(rabbit_config.BUILD_SERVICE))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# Write files
#
out.output(OutputDriver_Print())
# out.output(OutputDriver_Directory('/tmp/build-gke'))
```

Output:

```text
****** BEGIN FILE: 001-app-namespace.yaml ********
apiVersion: v1
kind: Namespace
metadata:
  name: app-monitoring

****** END FILE: 001-app-namespace.yaml ********
****** BEGIN FILE: 002-rabbitmq-config.yaml ********
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myrabbit
  namespace: app-monitoring
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: myrabbit
  namespace: app-monitoring
rules:
- apiGroups: ['']
  resources: [endpoints]
  verbs: [get]
- apiGroups: ['']
  resources: [events]
  verbs: [create]
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: myrabbit
  namespace: app-monitoring
subjects:
- kind: ServiceAccount
  name: myrabbit
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: myrabbit
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: myrabbit-config
  namespace: app-monitoring
data:
  enabled_plugins: |-
    [rabbitmq_peer_discovery_k8s, rabbitmq_management, rabbitmq_prometheus].
  rabbitmq.conf: |-
    log.console.level = info
    cluster_formation.peer_discovery_backend = k8s
    cluster_formation.k8s.host = kubernetes.default.svc.cluster.local
    cluster_formation.k8s.address_type = hostname
    cluster_formation.k8s.service_name = myrabbit-headless
    queue_master_locator=min-masters
---
apiVersion: v1
kind: Secret
metadata:
  name: myrabbit-config-secret
  namespace: app-monitoring
type: Opaque
data:
  erlang_cookie: bXktc2VjcmV0LWNvb2tpZQ==

****** END FILE: 002-rabbitmq-config.yaml ********
****** BEGIN FILE: 003-rabbitmq.yaml ********
apiVersion: v1
kind: Service
metadata:
  name: myrabbit-headless
  namespace: app-monitoring
spec:
  clusterIP: None
  ports:
  - name: epmd
    port: 4369
    protocol: TCP
    targetPort: 4369
  - name: cluster-links
    port: 25672
    protocol: TCP
    targetPort: 25672
  selector:
    app: myrabbit
  type: ClusterIP
  sessionAffinity: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: myrabbit
  namespace: app-monitoring
  labels:
    app: myrabbit
spec:
  selector:
    matchLabels:
      app: myrabbit
  serviceName: myrabbit-headless
  replicas: 1
  template:
    metadata:
      name: myrabbit
      namespace: app-monitoring
      labels:
        app: myrabbit
    spec:
      initContainers:
      - name: rabbitmq-config
        image: busybox:1.32.0
        securityContext:
          runAsUser: 0
          runAsGroup: 0
        volumeMounts:
        - name: rabbitmq-config
          mountPath: /tmp/rabbitmq
        - name: rabbitmq-config-rw
          mountPath: /etc/rabbitmq
        - name: rabbitmq-config-erlang-cookie
          mountPath: /tmp/rabbitmq-cookie
        command: [sh, -c, cp /tmp/rabbitmq/rabbitmq.conf /etc/rabbitmq/rabbitmq.conf
            && echo '' >> /etc/rabbitmq/rabbitmq.conf; cp /tmp/rabbitmq/enabled_plugins
            /etc/rabbitmq/enabled_plugins; mkdir -p /var/lib/rabbitmq; cp /tmp/rabbitmq-cookie/erlang_cookie
            /var/lib/rabbitmq/.erlang.cookie; chmod 600 /var/lib/rabbitmq/.erlang.cookie;
            chown 999.999 /etc/rabbitmq/rabbitmq.conf /etc/rabbitmq/enabled_plugins
            /var/lib/rabbitmq /var/lib/rabbitmq/.erlang.cookie]
      volumes:
      - name: rabbitmq-config
        configMap:
          name: myrabbit-config
          optional: false
          items:
          - key: enabled_plugins
            path: enabled_plugins
          - key: rabbitmq.conf
            path: rabbitmq.conf
      - name: rabbitmq-config-rw
        emptyDir: {}
      - name: rabbitmq-config-erlang-cookie
        secret:
          secretName: myrabbit-config-secret
          items:
          - key: erlang_cookie
            path: erlang_cookie
      - name: rabbitmq-data
        persistentVolumeClaim:
          claimName: rabbitmq-storage-claim
      serviceAccountName: myrabbit
      securityContext:
        fsGroup: 999
        runAsUser: 999
        runAsGroup: 999
      containers:
      - name: rabbitmq
        image: rabbitmq:3.8.9-alpine
        volumeMounts:
        - name: rabbitmq-config-rw
          mountPath: /etc/rabbitmq
        - name: rabbitmq-data
          mountPath: /var/lib/rabbitmq/mnesia
        ports:
        - name: amqp
          containerPort: 5672
          protocol: TCP
        - name: management
          containerPort: 15672
          protocol: TCP
        - name: prometheus
          containerPort: 15692
          protocol: TCP
        - name: epmd
          containerPort: 4369
          protocol: TCP
        livenessProbe:
          exec:
            command: [rabbitmq-diagnostics, status]
          initialDelaySeconds: 60
          periodSeconds: 60
          timeoutSeconds: 15
        readinessProbe:
          exec:
            command: [rabbitmq-diagnostics, ping]
          initialDelaySeconds: 20
          periodSeconds: 60
          timeoutSeconds: 10
        resources:
          requests:
            cpu: 150m
            memory: 300Mi
          limits:
            cpu: 300m
            memory: 450Mi
---
kind: Service
apiVersion: v1
metadata:
  name: myrabbit
  namespace: app-monitoring
  labels:
    app: myrabbit
spec:
  type: ClusterIP
  ports:
  - name: http
    protocol: TCP
    port: 15672
  - name: prometheus
    protocol: TCP
    port: 15692
  - name: amqp
    protocol: TCP
    port: 5672
  selector:
    app: myrabbit

****** END FILE: 003-rabbitmq.yaml ********
****** BEGIN FILE: create_gke.sh ********
#!/bin/bash

set -e
kubectl apply -f 001-app-namespace.yaml
kubectl config set-context --current --namespace=app-monitoring
kubectl apply -f 002-rabbitmq-config.yaml
kubectl apply -f 003-rabbitmq.yaml

****** END FILE: create_gke.sh ********
```

## Credits

based on

[rabbitmq/diy-kubernetes-examples](https://github.com/rabbitmq/diy-kubernetes-examples)

## Author

Rangel Reale (rangelspam@gmail.com)
