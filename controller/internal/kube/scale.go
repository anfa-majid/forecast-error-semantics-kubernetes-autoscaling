package kube

import (
	"context"

	"github.com/anfa-research/predictive-autoscaler/internal/controller"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

type DeploymentScaler struct {
	Client         kubernetes.Interface
	Namespace      string
	DeploymentName string
}

func (s DeploymentScaler) Current(ctx context.Context) (controller.ScaleResult, error) {
	scale, err := s.Client.AppsV1().Deployments(s.Namespace).GetScale(ctx, s.DeploymentName, metav1.GetOptions{})
	if err != nil {
		return controller.ScaleResult{}, err
	}
	return controller.ScaleResult{Replicas: int(scale.Spec.Replicas), ResourceVersion: scale.ResourceVersion}, nil
}

func (s DeploymentScaler) Update(ctx context.Context, replicas int) (controller.ScaleResult, error) {
	scale, err := s.Client.AppsV1().Deployments(s.Namespace).GetScale(ctx, s.DeploymentName, metav1.GetOptions{})
	if err != nil {
		return controller.ScaleResult{}, err
	}
	scale.Spec.Replicas = int32(replicas)
	updated, err := s.Client.AppsV1().Deployments(s.Namespace).UpdateScale(ctx, s.DeploymentName, scale, metav1.UpdateOptions{})
	if err != nil {
		return controller.ScaleResult{}, err
	}
	return controller.ScaleResult{Replicas: int(updated.Spec.Replicas), ResourceVersion: updated.ResourceVersion}, nil
}

func (s DeploymentScaler) ReadyReplicas(ctx context.Context) (int,error) {
	deployment,err:=s.Client.AppsV1().Deployments(s.Namespace).Get(ctx,s.DeploymentName,metav1.GetOptions{})
	if err!=nil{return 0,err}
	return int(deployment.Status.ReadyReplicas),nil
}
