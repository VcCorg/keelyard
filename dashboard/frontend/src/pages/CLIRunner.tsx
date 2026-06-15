import { useEffect, useState } from "react";
import { TerminalSquare, Play, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StreamConsole } from "@/components/StreamConsole";
import { RunHistory } from "@/components/RunHistory";
import { api } from "@/lib/api";

const EXAMPLES = [
  "kg stats",
  "domain list",
  "product list",
  "data list",
  "eval list",
  "history recent",
  "skill list",
];

export function CLIRunner() {
  const [groups, setGroups] = useState<string[]>([]);
  const [blocked, setBlocked] = useState<string[]>([]);
  const [command, setCommand] = useState("kg stats");
  const [danger, setDanger] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  useEffect(() => {
    api.listCliGroups().then(setGroups).catch(() => setGroups([]));
    api.listCliBlocked().then(setBlocked).catch(() => setBlocked([]));
  }, []);

  const run = () => {
    if (!command.trim()) return;
    setRunning(true);
    setStreamUrl(api.cliRunStreamUrl(command.trim(), danger));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
          <TerminalSquare className="h-7 w-7 text-indigo-500" />
          CLI Console
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Run whitelisted <code className="font-mono">dva</code> commands and stream their output
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-4">
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500 block mb-1">Command (the leading "dva" is optional)</label>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-gray-400">dva</span>
              <Input
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && run()}
                placeholder="kg stats"
                className="font-mono"
              />
            </div>
          </div>
          <Button disabled={running || !command.trim()} onClick={run}>
            <Play className="h-4 w-4 mr-1.5" /> Run
          </Button>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setCommand(ex)}
              className="text-xs font-mono px-2 py-1 rounded-md border border-gray-200 dark:border-gray-700 text-gray-500 hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>

        {/* Danger mode */}
        <div
          className={`rounded-lg border p-3 flex items-start gap-3 transition-colors ${
            danger
              ? "border-red-300 bg-red-50 dark:border-red-900/50 dark:bg-red-900/20"
              : "border-gray-200 dark:border-gray-700"
          }`}
        >
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={danger}
              onChange={(e) => setDanger(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <span className="text-sm font-medium flex items-center gap-1.5">
              <AlertTriangle className={`h-4 w-4 ${danger ? "text-red-500" : "text-gray-400"}`} />
              Danger mode
            </span>
          </label>
          <p className="text-xs text-gray-500 flex-1">
            {danger ? (
              <span className="text-red-600 dark:text-red-400">
                Destructive subcommands are now permitted. These can delete or reset data irreversibly.
              </span>
            ) : (
              <>
                Blocked subcommands:{" "}
                <span className="font-mono">{(blocked.length ? blocked : ["delete", "remove", "clear", "cleanup", "reset"]).join(", ")}</span>.
                Enable to override.
              </>
            )}
          </p>
        </div>

        {groups.length > 0 && (
          <p className="text-xs text-gray-400">
            Allowed groups: <span className="font-mono">{groups.join(", ")}</span>.
          </p>
        )}
      </div>

      <StreamConsole
        url={streamUrl}
        title="dva"
        onDone={() => {
          setRunning(false);
          setHistoryKey((k) => k + 1);
        }}
      />

      <RunHistory kind="cli" refreshKey={historyKey} title="Command History" />
    </div>
  );
}
