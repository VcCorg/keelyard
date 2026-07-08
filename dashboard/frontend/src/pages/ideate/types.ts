export interface Story {
  title: string;
  description: string;
  acceptance_criteria: string[];
  priority: string;
  labels: string[];
  issue_type: string;
  epic_key: string | null;
  story_points: number | null;
  assignee: string | null;
  components: string[];
}

export interface EditableStory extends Story {
  _id: string;
  keep: boolean;
}

export interface JiraMeta {
  project: string;
  issue_types: string[];
  epics: { key: string; summary: string }[];
  fields: {
    epic_link: boolean;
    story_points: boolean;
    acceptance_criteria: boolean;
    components: boolean;
    assignee: boolean;
    priority: boolean;
  };
}

export interface PushResult {
  title: string;
  ok: boolean;
  key?: string;
  url?: string;
  error?: string;
}

export interface AgentEvent {
  type: "thinking" | "tool_call" | "tool_result" | "stories" | "final" | "error";
  text?: string | null;
  tool?: string | null;
  args?: Record<string, unknown> | null;
  result?: unknown;
  stories?: Story[] | null;
  error?: string | null;
}

export interface ToolSpec {
  name: string;
  kind: string;
  description: string;
  params: Record<string, unknown>;
  mutating: boolean;
}

export interface IdeateAgent {
  name: string;
  path: string;
  use_case?: string | null;
  tool_name: string;
}

export const PRIORITIES = ["High", "Medium", "Low"];
export const DEFAULT_ISSUE_TYPES = ["Story", "Task", "Bug", "Spike"];

export function newStory(partial: Partial<Story> = {}): Story {
  return {
    title: "",
    description: "",
    acceptance_criteria: [],
    priority: "Medium",
    labels: [],
    issue_type: "Story",
    epic_key: null,
    story_points: null,
    assignee: null,
    components: [],
    ...partial,
  };
}
