import { useCallback, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { usePolling } from "@/hooks/usePolling";
import { api, type Deployment } from "@/lib/api";
import { DeploymentCard } from "@/components/DeploymentCard";
import { DeploymentForm } from "@/components/DeploymentForm";

export function Deployments() {
  const fetcher = useCallback(() => api.listDeployments(), []);
  const { data: deployments, loading, refresh } = usePolling<Deployment[]>(fetcher, 10000);
  const [showForm, setShowForm] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);

  const handleCreateDeployment = async (data: {
    agentName: string;
    target: string;
    environment: string;
    maxInstances: number;
  }) => {
    try {
      await api.createDeployment({
        agent_name: data.agentName,
        target: data.target,
        environment: data.environment,
        max_instances: data.maxInstances,
      });
      setShowForm(false);
      refresh();
    } catch (error) {
      console.error("Failed to create deployment:", error);
    }
  };

  const handleDeleteDeployment = async (deploymentId: string) => {
    if (confirm(`Delete deployment '${deploymentId}'?`)) {
      try {
        await api.deleteDeployment(deploymentId);
        refresh();
      } catch (error) {
        console.error("Failed to delete deployment:", error);
      }
    }
  };

  const deploymentsByTarget = deployments?.reduce((acc, d) => {
    if (!acc[d.target]) acc[d.target] = [];
    acc[d.target].push(d);
    return acc;
  }, {} as Record<string, Deployment[]>) || {};

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Deployments</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">Manage agent deployments across targets</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
          aria-label="Create new deployment"
        >
          <Plus className="h-4 w-4" />
          New Deployment
        </button>
      </div>

      {showForm && (
        <DeploymentForm
          onSubmit={handleCreateDeployment}
          onCancel={() => setShowForm(false)}
        />
      )}

      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-pulse text-gray-400">Loading deployments...</div>
        </div>
      )}

      {!loading && (!deployments || deployments.length === 0) && (
        <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-12 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">No deployments yet.</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">Create your first deployment to get started.</p>
        </div>
      )}

      {deployments && deployments.length > 0 && (
        <div className="space-y-6">
          {Object.entries(deploymentsByTarget).map(([target, targetDeployments]) => (
            <div key={target}>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 capitalize">
                {target.replace("-", " ")} Deployments
              </h2>
              <div className="grid gap-4">
                {targetDeployments.map((deployment) => (
                  <DeploymentCard
                    key={deployment.id}
                    deployment={deployment}
                    onDelete={() => handleDeleteDeployment(deployment.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
