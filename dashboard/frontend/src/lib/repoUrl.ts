/**
 * Parse a pasted git repository URL.
 *
 * The Repos step lets you paste a link. Before this, that link was written into
 * `bitbucket_url` unconditionally — so a GitHub URL landed in the Bitbucket
 * field, made the domain look configured, and left discovery failing with
 * "no Bitbucket project key or URL". Identifying the host is what stops one
 * host's address being stored as another's.
 *
 * Two things come out of a parse, and they are deliberately separate:
 *
 *  - **A link target.** Owner and slug are readable from the path shape alone,
 *    so a repo can be linked from any git host without an API, a token, or a
 *    discovery call. That is what makes GitHub usable today.
 *  - **A host.** Only claimed when the URL actually says so — by hostname, or
 *    by a path shape unique to one product. Everything else is `unknown`, and
 *    an unknown host still links fine; it just does not get filed as a source,
 *    because guessing is how the original bug happened.
 */

export type RepoHost = "github" | "bitbucket" | "unknown";

/** What the URL points at: one repository, or a container of them. */
export type RepoUrlKind = "repo" | "project" | "unknown";

export type ParsedRepoUrl = {
  host: RepoHost;
  kind: RepoUrlKind;
  /** GitHub org/user, or Bitbucket project key. */
  owner: string;
  /** Repository slug — empty unless `kind === "repo"`. */
  slug: string;
  /** Normalised https URL for cloning, or "" when it cannot be built. */
  cloneUrl: string;
  /** The input, trimmed. */
  input: string;
};

const EMPTY: ParsedRepoUrl = {
  host: "unknown", kind: "unknown", owner: "", slug: "", cloneUrl: "", input: "",
};

/** `git@host:owner/repo.git` → `https://host/owner/repo.git`. */
function normaliseScp(raw: string): string {
  const m = /^(?:ssh:\/\/)?(?:[\w.-]+@)([^/:]+):(?!\d)(.+)$/.exec(raw);
  return m ? `https://${m[1]}/${m[2]}` : raw;
}

function stripGitSuffix(segment: string): string {
  return segment.replace(/\.git$/i, "");
}

export function parseRepoUrl(raw: string): ParsedRepoUrl {
  const input = (raw || "").trim();
  if (!input) return { ...EMPTY };

  let url: URL;
  try {
    url = new URL(normaliseScp(input));
  } catch {
    return { ...EMPTY, input };
  }
  if (!/^https?:$/.test(url.protocol)) return { ...EMPTY, input };

  const segments = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const hostname = url.hostname.toLowerCase();

  // Bitbucket Server's /projects/<KEY>/repos/<slug> is unmistakable, so it is
  // matched by shape as well as by hostname — self-hosted instances are
  // routinely named something else entirely.
  const projectsAt = segments.findIndex((s) => s.toLowerCase() === "projects");
  if (projectsAt !== -1 && segments.length > projectsAt + 1) {
    const owner = segments[projectsAt + 1];
    const reposAt = segments.findIndex((s) => s.toLowerCase() === "repos");
    const slug =
      reposAt !== -1 && segments.length > reposAt + 1
        ? stripGitSuffix(segments[reposAt + 1])
        : "";
    return {
      host: "bitbucket",
      kind: slug ? "repo" : "project",
      owner,
      slug,
      cloneUrl: slug ? `${url.origin}/scm/${owner.toLowerCase()}/${slug}.git` : "",
      input,
    };
  }

  // Hostname tells us the product for the hosted services and for enterprise
  // installs that keep the vendor in the name (github.acme.com).
  const host: RepoHost = /(^|\.)github\./.test(hostname)
    ? "github"
    : /(^|\.)bitbucket\./.test(hostname)
      ? "bitbucket"
      : "unknown";

  // <owner>/<repo> is the shape every mainstream host uses, so the link target
  // is readable even when the host is not.
  if (segments.length >= 2) {
    const owner = segments[0];
    const slug = stripGitSuffix(segments[1]);
    return {
      host,
      kind: "repo",
      owner,
      slug,
      cloneUrl: `${url.origin}/${owner}/${slug}.git`,
      input,
    };
  }
  if (segments.length === 1) {
    return { host, kind: "project", owner: segments[0], slug: "", cloneUrl: "", input };
  }
  return { ...EMPTY, host, input };
}

/**
 * Which domain field this URL belongs in, or null when we cannot tell.
 *
 * Returning null rather than a default is the fix: the previous code had no
 * null case and defaulted to Bitbucket.
 */
export function sourceFieldFor(
  parsed: ParsedRepoUrl,
): "bitbucket_url" | "github_url" | null {
  if (parsed.host === "github") return "github_url";
  if (parsed.host === "bitbucket") return "bitbucket_url";
  return null;
}
