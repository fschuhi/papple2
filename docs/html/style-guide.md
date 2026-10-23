# papple2 -- Style guide for the HTML pages

You translate one markdown file of `papple2` into one HTML page. The markdown stays the source; the page is a reading version of it. Before you start, read `example.md` and `example.html` in this folder: they are a pair, a markdown file and its translation. Do everything the way `example.html` does it.

---

## The page

- The page has the name of the markdown file, with `.html` instead of `.md`, and lies in `docs/html/`: `docs/routine.md` becomes `docs/html/routine.html`.
- Take the frame from `example.html`: the doctype, the head with `charset`, `viewport`, `title` and the link to `style.css`, then `<body>` and `<main>`. The title is the text of the first heading.
- Use only `style.css`: no `<style>`, no `style="..."`, no script, no fonts or images from the web.
- Use only the classes that `style.css` defines.

## The text

- Translate, don't rewrite. Keep every sentence and every word, in their order. Add nothing, leave nothing out, explain nothing.
- Keep the typography as it is: `--`, `->`, straight quotes.
- In HTML text, write `<` as `&lt;` and `&` as `&amp;`.

## Element by element

| Markdown | HTML |
|----------|------|
| `# Heading` | `<h1>` |
| `## Heading`, `### Heading` | `<h2>`, `<h3>` |
| A paragraph (one line) | `<p>` |
| `---` | `<hr>` |
| `- item` | `<ul>` with `<li>` |
| `1. item` | `<ol>` with `<li>` |
| `` `name` `` | `<code>` |
| `**word**` | `<strong>` |
| `*word*` | `<em>` |
| `> quote` | `<blockquote>` |
| `[text](path)` | `<a href="path">`, with the path changed so that it leads to the same file from `docs/html/` (see below) |
| A table | `<table>` with `<thead>` and `<tbody>` (see below) |
| A code fence | `<pre>` or a diagram (see below) |

**Links.** The page lies in `docs/html/`, so a path from a file in `docs/` gets `../` in front: `[glossary.md](glossary.md)` in `docs/routine.md` becomes `<a href="../glossary.md">`. A link to a web address stays as it is.

**Tables.** The header row goes into `<thead>`, the other rows into `<tbody>`. A column aligned right in the markdown (`---:`) gets `class="number"` on its `<th>` and on each of its `<td>`.

## Code fences

A code fence is one of three kinds. Tell them apart by their lines:

1. **A listing:** lines that start with a four-digit hex address (`6267`), maybe after arrows on the left (`+--`, `|`, `+->`), followed by bytes or a mnemonic (`LDA`, `JSR`, ...).
2. **A diagram:** names joined by arrows drawn with characters (`-->`, `<--`, `|`, `v`), not code.
3. **Anything else:** commands, data, text laid out by hand.

**Anything else** becomes `<pre>` with the text of the fence exactly: every space, every line. No `<code>` inside.

**A listing** becomes `<pre>` with the text of the fence exactly, too. Then add spans, and nothing else:

- The bytes: `<span class="bytes">a4 86</span>`. Only the hex bytes go inside; the spaces before and after stay outside.
- Each mnemonic in the code part of a line: `<span class="mn-load">LDA</span>`, with the class from the table below. The comment, from `;` to the end of the line, gets no spans.
- A row that says "never ran": `<span class="gap">... 629a-629c: 2 bytes never ran ...</span>`. The arrows before it stay outside.
- Everything else gets no span: the arrows, the address, labels, operands, comments.
- A mnemonic that is not in the table (`.byte`, `???`) gets no span.

| Class | Mnemonics |
|-------|-----------|
| `mn-load` | LDA LDX LDY STA STX STY |
| `mn-trans` | TAX TAY TSX TXA TXS TYA |
| `mn-stack` | PHA PHP PLA PLP |
| `mn-shift` | ASL LSR ROL ROR |
| `mn-logic` | AND BIT EOR ORA |
| `mn-arith` | ADC CMP CPX CPY SBC |
| `mn-inc` | DEC DEX DEY INC INX INY |
| `mn-ctrl` | BRK JMP JSR RTI RTS |
| `mn-bra` | BCC BCS BEQ BMI BNE BPL BVC BVS |
| `mn-flags` | CLC CLD CLI CLV SEC SED SEI |
| `mn-nop` | NOP |

**A diagram** becomes an inline SVG inside `<div class="diagram">`, in the same layout as the characters: what stands to the left stays left, what stands below stays below.

- Each name becomes a box with its text: `<rect class="box">` and `<text class="name">`. A box is 28 high and about 8 per character wide, plus 24. The text sits in the middle of the box, with `text-anchor="middle"` and `dominant-baseline="central"`.
- Each arrow becomes `<line class="arrow">`, or `<path class="arrow">` where it bends, with `marker-end` pointing at the arrow head.
- The text on an arrow, and any loose text, becomes `<text class="label">`.
- Copy the `<defs>` with the `<marker>` from `example.html`. Give the marker an id that no other diagram on the page uses, and use that id in `marker-end`.
- Keep every word of the diagram.
- Make `width`, `height` and `viewBox` large enough for everything, with a margin of 10.
- If you are not sure how to draw a diagram, keep it as `<pre>` with its characters exactly. A diagram kept as text is better than a wrong drawing.

## Before you finish

- Every sentence of the markdown is on the page.
- Every listing, with its tags removed, is the text of its fence exactly.
- Every class you used is in `style.css`.
- Every tag you opened is closed.
