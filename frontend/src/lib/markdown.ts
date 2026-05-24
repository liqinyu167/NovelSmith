export function renderMarkdown(text: string): string {
  const escaped = escapeHtml(text).replace(/\r\n/g, "\n").trim();
  if (!escaped) return "";
  const blocks: string[] = [];
  let olItems: string[] = [];
  let ulItems: string[] = [];

  function flushLists() {
    if (olItems.length) {
      blocks.push(`<ol>${olItems.join("")}</ol>`);
      olItems = [];
    }
    if (ulItems.length) {
      blocks.push(`<ul>${ulItems.join("")}</ul>`);
      ulItems = [];
    }
  }

  for (const rawLine of escaped.split("\n")) {
    const line = rawLine.trim();
    if (!line) {
      flushLists();
      continue;
    }
    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      flushLists();
      const level = Math.min(heading[1].length + 2, 5);
      blocks.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    const numbered = /^\d+[.、]\s*(.+)$/.exec(line);
    if (numbered) {
      if (ulItems.length) {
        blocks.push(`<ul>${ulItems.join("")}</ul>`);
        ulItems = [];
      }
      olItems.push(`<li>${renderInlineMarkdown(numbered[1])}</li>`);
      continue;
    }
    const bullet = /^[-*]\s+(.+)$/.exec(line);
    if (bullet) {
      if (olItems.length) {
        blocks.push(`<ol>${olItems.join("")}</ol>`);
        olItems = [];
      }
      ulItems.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
      continue;
    }
    if (/^---+$/.test(line)) {
      flushLists();
      blocks.push("<hr>");
      continue;
    }
    flushLists();
    blocks.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }
  flushLists();
  return blocks.join("");
}

export function renderInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
