import { Users } from "lucide-react";
import { PlaceholderPage } from "@/components/PlaceholderPage";

export function People() {
  return (
    <PlaceholderPage
      icon={Users}
      title="People"
      subtitle="Team directory, roles, and per-user workload."
      phase="Phase 4"
      planned={[
        "Shared `users` directory (id, name, email, avatar, role).",
        "Users self-register on first sync from the local identity profile.",
        "Roles (member / lead / admin) drive Admin-section visibility.",
        "Per-user active assignments and session load at a glance.",
        "Phase 5: local identity swapped for example SSO/OIDC behind the same seam.",
      ]}
    />
  );
}
