import { useState } from "react";
import { Download, CheckCircle } from "lucide-react";
import { StarterPackCard } from "@/components/StarterPackCard";

interface StarterPack {
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
}

const STARTER_PACKS: StarterPack[] = [
  {
    id: "backend-dev",
    name: "Backend Developer",
    description: "Complete backend development setup with FastAPI, databases, and testing",
    category: "development",
    useCase: "Backend API development",
    tags: ["python", "fastapi", "databases", "testing"],
    installed: false,
    popularity: 95,
    rating: 4.8,
    version: "1.0.0",
  },
  {
    id: "data-science",
    name: "Data Science",
    description: "Data analysis, ML model development, and visualization toolkit",
    category: "data",
    useCase: "Data analysis and ML",
    tags: ["python", "pandas", "sklearn", "visualization"],
    installed: false,
    popularity: 88,
    rating: 4.7,
    version: "1.0.0",
  },
  {
    id: "devops-engineer",
    name: "DevOps Engineer",
    description: "Infrastructure, CI/CD pipelines, and deployment automation",
    category: "infrastructure",
    useCase: "DevOps and deployment",
    tags: ["docker", "kubernetes", "ci-cd", "terraform"],
    installed: false,
    popularity: 85,
    rating: 4.6,
    version: "1.0.0",
  },
  {
    id: "qa-engineer",
    name: "QA Engineer",
    description: "Testing automation, test case management, and quality assurance",
    category: "testing",
    useCase: "Quality assurance",
    tags: ["testing", "automation", "qa", "selenium"],
    installed: false,
    popularity: 78,
    rating: 4.5,
    version: "1.0.0",
  },
  {
    id: "code-reviewer",
    name: "Code Reviewer",
    description: "Code review automation with best practices and security checks",
    category: "code-quality",
    useCase: "Code review and analysis",
    tags: ["code-review", "security", "best-practices"],
    installed: false,
    popularity: 82,
    rating: 4.6,
    version: "1.0.0",
  },
  {
    id: "support-agent",
    name: "Support Agent",
    description: "Customer support automation with ticket management and FAQs",
    category: "customer-service",
    useCase: "Customer support",
    tags: ["support", "automation", "customer-service"],
    installed: false,
    popularity: 75,
    rating: 4.4,
    version: "1.0.0",
  },
];

export function StarterPacks() {
  const [packs, setPacks] = useState<StarterPack[]>(STARTER_PACKS);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = Array.from(new Set(packs.map((p) => p.category)));
  const filteredPacks = selectedCategory
    ? packs.filter((p) => p.category === selectedCategory)
    : packs;

  const handleInstall = (id: string) => {
    setPacks((prev) =>
      prev.map((p) =>
        p.id === id ? { ...p, installed: true } : p
      )
    );
  };

  const installedCount = packs.filter((p) => p.installed).length;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Starter Packs</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">Pre-configured agent templates for common workflows</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{installedCount}</div>
          <div className="text-xs text-gray-500">Installed</div>
        </div>
      </div>

      {/* Category Filter */}
      <div className="space-y-3">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter by category</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === null
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                selectedCategory === cat
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Starter Packs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPacks.map((pack) => (
          <StarterPackCard
            key={pack.id}
            pack={pack}
            onInstall={() => handleInstall(pack.id)}
          />
        ))}
      </div>
    </div>
  );
}
