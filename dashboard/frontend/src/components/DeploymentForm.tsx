import { useState } from "react";
import { X } from "lucide-react";

interface DeploymentFormProps {
  onSubmit: (data: {
    agentName: string;
    target: string;
    environment: string;
    maxInstances: number;
  }) => void;
  onCancel: () => void;
}

export function DeploymentForm({ onSubmit, onCancel }: DeploymentFormProps) {
  const [agentName, setAgentName] = useState("");
  const [target, setTarget] = useState("docker");
  const [environment, setEnvironment] = useState("development");
  const [maxInstances, setMaxInstances] = useState(1);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const targets = [
    { value: "local", label: "Local Daemon", description: "Run on local machine" },
    { value: "docker", label: "Docker Container", description: "Run in Docker" },
    { value: "cloud-run", label: "Google Cloud Run", description: "Serverless on GCP" },
    { value: "kubernetes", label: "Kubernetes", description: "Run on K8s cluster" },
  ];

  const environments = [
    { value: "development", label: "Development" },
    { value: "staging", label: "Staging" },
    { value: "production", label: "Production" },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!agentName.trim()) {
      newErrors.agentName = "Agent name is required";
    }

    if (maxInstances < 1 || maxInstances > 10) {
      newErrors.maxInstances = "Instances must be between 1 and 10";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    onSubmit({
      agentName: agentName.trim(),
      target,
      environment,
      maxInstances,
    });
  };

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create New Deployment</h2>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label="Close form"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Agent Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Agent Name
          </label>
          <input
            type="text"
            value={agentName}
            onChange={(e) => {
              setAgentName(e.target.value);
              if (errors.agentName) {
                setErrors({ ...errors, agentName: "" });
              }
            }}
            placeholder="Enter agent name"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          {errors.agentName && (
            <p className="text-xs text-red-500 mt-1">{errors.agentName}</p>
          )}
        </div>

        {/* Target Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Deployment Target
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {targets.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setTarget(t.value)}
                className={`p-3 rounded-lg border-2 text-left transition-all ${
                  target === t.value
                    ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30"
                    : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-indigo-300"
                }`}
              >
                <p className="font-medium text-gray-900 dark:text-white">{t.label}</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">{t.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Environment */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Environment
          </label>
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {environments.map((e) => (
              <option key={e.value} value={e.value}>
                {e.label}
              </option>
            ))}
          </select>
        </div>

        {/* Max Instances */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Max Instances ({maxInstances})
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={maxInstances}
            onChange={(e) => {
              setMaxInstances(parseInt(e.target.value));
              if (errors.maxInstances) {
                setErrors({ ...errors, maxInstances: "" });
              }
            }}
            className="w-full"
          />
          {errors.maxInstances && (
            <p className="text-xs text-red-500 mt-1">{errors.maxInstances}</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            Maximum number of running instances
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="submit"
            className="flex-1 px-4 py-2 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700 transition-colors"
          >
            Create Deployment
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
