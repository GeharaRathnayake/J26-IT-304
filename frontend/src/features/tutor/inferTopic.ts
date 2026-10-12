type Topic = { id: string; label: string };

// Label words too generic to identify a topic on their own.
const GENERIC_WORDS = new Set(['types', 'statements', 'objects', 'handling']);

// Finds the topic a free-text message is about, so a message can be sent
// without picking a topic first. Matches the full label or one of its longer
// words (case-insensitive) and returns the topic mentioned earliest.
export function inferTopic(text: string, topics: Topic[]): Topic | null {
  const haystack = text.toLowerCase();
  let best: { topic: Topic; at: number } | null = null;
  for (const topic of topics) {
    const label = topic.label.toLowerCase();
    const needles = [label, ...label.split(/[^a-z]+/).filter((word) => word.length >= 5 && !GENERIC_WORDS.has(word))];
    for (const needle of needles) {
      const at = haystack.indexOf(needle);
      if (at !== -1 && (!best || at < best.at)) best = { topic, at };
    }
  }
  return best?.topic ?? null;
}
