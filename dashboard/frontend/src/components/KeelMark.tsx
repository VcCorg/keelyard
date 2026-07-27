/**
 * Keel K monogram — the platform mark used in the sidebar header and
 * anywhere else the app identity is shown. Uses currentColor so it themes
 * from CSS `color:`. The waterline stays sea-glass so the mark reads even
 * on backgrounds close to the primary hue.
 */
export function KeelMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 96 130"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M 0 66 L 8 66 M 30 66 L 96 66"
        stroke="#89B7D3"
        strokeWidth="4"
        strokeLinecap="round"
        fill="none"
      />
      <path d="M 12 8 L 26 8 L 26 66 L 12 66 Z" fill="currentColor" />
      <path
        d="M 12 66 L 26 66 C 25 82, 22 102, 20 124 L 18 124 C 15 102, 12 82, 12 66 Z"
        fill="currentColor"
      />
      <path d="M 26 44 L 66 8 L 80 8 L 26 62 Z" fill="currentColor" />
      <path d="M 26 70 L 66 124 L 80 124 L 26 88 Z" fill="currentColor" />
    </svg>
  );
}
