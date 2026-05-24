import { describe, it, expect } from "vitest";
import { renderMarkdown, renderInlineMarkdown, escapeHtml } from "./markdown";

describe("Markdown Parser", () => {
  it("should escape HTML tags to prevent XSS", () => {
    const input = '<script>alert("xss")</script>';
    const output = renderMarkdown(input);
    expect(output).not.toContain("<script>");
    expect(output).toContain("&lt;script&gt;");
  });

  it("should parse headings correctly", () => {
    expect(renderMarkdown("# Header 1")).toBe("<h3>Header 1</h3>");
    expect(renderMarkdown("## Header 2")).toBe("<h4>Header 2</h4>");
    expect(renderMarkdown("### Header 3")).toBe("<h5>Header 3</h5>"); // Wait, math.min level+2 limit is 5.
  });

  it("should parse ordered list correctly", () => {
    const input = "1. First item\n2. Second item";
    const output = renderMarkdown(input);
    expect(output).toBe("<ol><li>First item</li><li>Second item</li></ol>");
  });

  it("should parse unordered bullet list correctly (using - or *)", () => {
    const input1 = "- Bullet A\n- Bullet B";
    const output1 = renderMarkdown(input1);
    expect(output1).toBe("<ul><li>Bullet A</li><li>Bullet B</li></ul>");

    const input2 = "* Bullet C\n* Bullet D";
    const output2 = renderMarkdown(input2);
    expect(output2).toBe("<ul><li>Bullet C</li><li>Bullet D</li></ul>");
  });

  it("should parse inline markdown format correctly", () => {
    expect(renderInlineMarkdown("This is **bold** text")).toBe("This is <strong>bold</strong> text");
    expect(renderInlineMarkdown("This is `code` element")).toBe("This is <code>code</code> element");
  });

  it("should escape HTML entities correctly", () => {
    expect(escapeHtml("<div>&\"'</div>")).toBe("&lt;div&gt;&amp;&quot;&#039;&lt;/div&gt;");
  });
});
