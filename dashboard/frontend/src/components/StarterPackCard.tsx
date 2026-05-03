import { Download, CheckCircle, Star } from "lucide-react";

interface StarterPackCardProps {
  pack: {
    id: string;
    name: string;
    description: string;
    category: string;
    useCase: string;
    tags: string[];
    installed: boolean;
    popularity: number;
    rating: number;
    version: string;
  };
  onInstall: () => void;
}

export function StarterPackCard({ pack, onInstall }: StarterPackCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 flex flex-col h-full hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{pack.name}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 capitalize">{pack.category}</p>
        </div>
        {pack.installed && (
          <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 ml-2" />
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 flex-grow">
        {pack.description}
      </p>

      {/* Use Case */}
      <div className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-800">
        <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">
          Use Case
        </p>
        <p className="text-sm text-gray-900 dark:text-white mt-1">{pack.useCase}</p>
      </div>

      {/* Tags */}
      <div className="mb-4 flex flex-wrap gap-2">
        {pack.tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-700 dark:text-gray-300"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-4 pb-4 border-b border-gray-200 dark:border-gray-800">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Popularity</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{pack.popularity}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Rating</p>
          <div className="flex items-center gap-1">
            <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{pack.rating}</p>
          </div>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Version</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{pack.version}</p>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={onInstall}
        disabled={pack.installed}
        className={`w-full py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
          pack.installed
            ? "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 cursor-not-allowed"
            : "bg-indigo-600 text-white hover:bg-indigo-700 dark:bg-indigo-700 dark:hover:bg-indigo-600"
        }`}
      >
        {pack.installed ? (
          <>
            <CheckCircle className="h-4 w-4" />
            Installed
          </>
        ) : (
          <>
            <Download className="h-4 w-4" />
            Install
          </>
        )}
      </button>
    </div>
  );
}
