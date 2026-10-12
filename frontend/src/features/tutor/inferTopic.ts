type Topic = { id: string; label: string };

// Label words too generic to identify a topic on their own.
const GENERIC_WORDS = new Set(['types', 'statements', 'objects', 'handling']);

function escapeRegExp(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Finds the topic a free-text message is about, so a message can be sent
// without picking a topic first. Matches the full label or one of its longer
// words (case-insensitive, whole words only) and returns the topic mentioned
// earliest.
export function inferTopic(text: string, topics: Topic[]): Topic | null {
  let best: { topic: Topic; at: number } | null = null;
  for (const topic of topics) {
    const label = topic.label.toLowerCase();
    const needles = [label, ...label.split(/[^a-z]+/).filter((word) => word.length >= 5 && !GENERIC_WORDS.has(word))];
    for (const needle of needles) {
      // Whole words only: "functions" must not match inside "dysfunctions".
      const at = text.search(new RegExp(`\\b${escapeRegExp(needle)}\\b`, 'i'));
      if (at !== -1 && (!best || at < best.at)) best = { topic, at };
    }
  }
  return best?.topic ?? null;
}
