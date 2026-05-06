import { Trash2, RotateCcw, Play, Square } from "lucide-react";
import { Deployment } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

interface DeploymentCardProps {
  deployment: Deployment;
  onDelete: () => void;
}

export function DeploymentCard({ deployment, onDelete }: DeploymentCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {deployment.agent_name}
          </h3>
          <div className="flex items-center gap-2 mt-2">
            <StatusBadge status={deployment.status} />
            <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">
              {deployment.environment}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              v{deployment.current_version}
            </span>
          </div>
        </div>
        <button
          onClick={onDelete}
          className="p-2 text-gray-400 hover:text-red-500 transition-colors"
          aria-label="Delete deployment"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Metrics */}
      {deployment.metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 py-4 border-y border-gray-200 dark:border-gray-800">
          {deployment.metrics.uptime_percent !== undefined && (
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Uptime</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                {deployment.metrics.uptime_percent.toFixed(1)}%
              </p>
            </div>
          )}
          {deployment.metrics.cpu_percent !== undefined && (
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">CPU</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                {deployment.metrics.cpu_percent.toFixed(1)}%
              </p>
            </div>
          )}
          {deployment.metrics.memory_mb !== undefined && (
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Memory</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                {deployment.metrics.memory_mb.toFixed(0)}MB
              </p>
            </div>
          )}
          {deployment.metrics.error_rate !== undefined && (
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Error Rate</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                {(deployment.metrics.error_rate * 100).toFixed(2)}%
              </p>
            </div>
          )}
        </div>
      )}

      {/* Configuration */}
      <div className="mb-4 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Target:</span>
          <span className="text-gray-900 dark:text-white capitalize font-medium">{deployment.target}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Replicas:</span>
          <span className="text-gray-900 dark:text-white font-medium">{deployment.replicas}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Created:</span>
          <span className="text-gray-900 dark:text-white font-medium">
            {new Date(deployment.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-800">
        {deployment.status === "running" ? (
          <button
            className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50 transition-colors text-sm font-medium"
            aria-label="Stop deployment"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        ) : (
          <button
            className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300 dark:hover:bg-emerald-900/50 transition-colors text-sm font-medium"
            aria-label="Start deployment"
          >
            <Play className="h-3.5 w-3.5" />
            Start
          </button>
        )}
        <button
          className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50 transition-colors text-sm font-medium"
          aria-label="Rollback deployment"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Rollback
        </button>
      </div>
    </div>
  );
}
