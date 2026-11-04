/**
 * A page title whose words slide up one after another from behind a hidden edge, with a slight
 * tilt (`.slide-word` in globals.css). Plain CSS, played once when the page opens; the words stay
 * real text, so nothing changes for screen readers or without scripts. `from` numbers the first
 * word, so a second part (the peach `rest`) carries on after the first.
 */
export function SlideWords({
  text,
  from = 0,
}: {
  text: string;
  from?: number;
}) {
  const words = text.split(/\s+/).filter(Boolean);
  return words.map((word, i) => (
    <span key={`${word}-${i}`}>
      {i > 0 ? " " : null}
      <span className="slide-word">
        <span style={{ "--wi": from + i } as React.CSSProperties}>{word}</span>
      </span>
    </span>
  ));
}

/** How many words `SlideWords` shows, for the part that follows. */
export const wordCount = (text: string) =>
  text.split(/\s+/).filter(Boolean).length;
