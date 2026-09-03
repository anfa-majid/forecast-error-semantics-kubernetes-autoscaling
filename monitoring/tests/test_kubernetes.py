import unittest

from anfa_observability.kubernetes import deployment_state, endpoint_states, pod_state


class KubernetesTransformTests(unittest.TestCase):
    def test_deployment_state_distinguishes_all_replica_counts(self):
        value={"metadata":{"uid":"u","resourceVersion":"9","generation":3},"spec":{"replicas":4},"status":{"observedGeneration":3,"replicas":3,"updatedReplicas":2,"readyReplicas":1,"availableReplicas":1,"unavailableReplicas":3}}
        state=deployment_state(value)
        self.assertEqual((state["desired_replicas"],state["current_replicas"],state["ready_replicas"],state["available_replicas"]),(4,3,1,1))

    def test_pod_lifecycle_and_endpoint_conditions(self):
        pod={"metadata":{"name":"p","uid":"u","creationTimestamp":"2026-01-01T00:00:00Z"},"spec":{"nodeName":"n"},"status":{"phase":"Running","conditions":[{"type":"PodScheduled","status":"True","lastTransitionTime":"a"},{"type":"Ready","status":"True","lastTransitionTime":"b"}],"containerStatuses":[{"name":"benchmark-app","ready":True,"restartCount":2,"imageID":"sha256:x","state":{"running":{"startedAt":"c"}}}]}}
        self.assertTrue(pod_state(pod)["ready"]); self.assertEqual(pod_state(pod)["restart_count"],2)
        endpoints={"items":[{"metadata":{"name":"slice"},"endpoints":[{"addresses":["1"],"targetRef":{"name":"p","uid":"u"},"conditions":{"ready":True,"serving":True,"terminating":False}}]}]}
        self.assertTrue(endpoint_states(endpoints)[0]["serving"])


if __name__ == "__main__": unittest.main()
