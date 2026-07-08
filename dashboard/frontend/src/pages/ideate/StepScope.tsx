export function StepScope({
  projects,
  project,
  onProject,
}: {
  projects: string[];
  project: string;
  onProject: (p: string) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-sm font-medium">Target Jira project</label>
        <p className="text-xs text-gray-500">
          Where approved stories are created; determines available fields/epics.
        </p>
      </div>
      {projects.length ? (
        <select
          value={project}
          onChange={(e) => onProject(e.target.value)}
          className="w-full max-w-sm text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 outline-none"
        >
          {projects.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      ) : (
        <p className="text-xs text-amber-600">
          No onboarded Jira projects found. You can still draft; set a project before pushing.
        </p>
      )}
    </div>
  );
}
