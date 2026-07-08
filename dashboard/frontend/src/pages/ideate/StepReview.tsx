import type { EditableStory, JiraMeta, PushResult } from "./types";
import { newStory } from "./types";
import { StoryCard } from "./StoryCard";

export function StepReview({
  stories,
  meta,
  onStories,
  pushResults,
  onPushOne,
}: {
  stories: EditableStory[];
  meta: JiraMeta | null;
  onStories: (s: EditableStory[]) => void;
  pushResults: Record<string, PushResult>;
  onPushOne: (story: EditableStory) => void;
}) {
  const patch = (id: string, p: Partial<EditableStory>) =>
    onStories(stories.map((s) => (s._id === id ? { ...s, ...p } : s)));
  const remove = (id: string) => onStories(stories.filter((s) => s._id !== id));
  const duplicate = (s: EditableStory) =>
    onStories([
      ...stories,
      { ...newStory(s), _id: `s${Date.now()}`, keep: true, title: `${s.title} (copy)` } as EditableStory,
    ]);

  if (!stories.length)
    return <p className="text-sm text-gray-400">No stories yet — draft some in the previous step.</p>;
  return (
    <div className="space-y-3">
      {stories.map((s) => (
        <StoryCard
          key={s._id}
          story={s}
          meta={meta}
          onChange={(p) => patch(s._id, p)}
          onRemove={() => remove(s._id)}
          onDuplicate={() => duplicate(s)}
          onPushOne={() => onPushOne(s)}
          pushed={pushResults[s._id]}
        />
      ))}
    </div>
  );
}
