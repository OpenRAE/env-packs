# Documentation style guide

This guide tells how to write the documents of this repository. Follow it, so
that a new page reads like the other pages. The model for the public pages is
[Stripe's documentation](https://docs.stripe.com): plain, short, and built
around a working example.

## Writing standard

Write all text in ASD-STE100 Simplified Technical English. The standard
applies to documents, comments, commit messages, issues, and pull requests.

- A procedural sentence has 20 words or fewer. A descriptive sentence has 25
  words or fewer.
- Use the active voice and simple tenses. Write one instruction in each
  sentence.
- Use simple, common words, and use one word for one meaning. Do not use
  idioms or phrasal verbs.
- A paragraph has 6 sentences or fewer. Use lists and tables where they make
  the text clearer.

When you change a document, bring the complete document into the standard. Do
not change a document only to pass the prose gate.

### The prose gate

`make prose` checks the Markdown files that a change adds or changes since
`BASE`. It runs Vale, which `mise.toml` pins, with the rules in
`.vale/styles/STE/`:

| Rule | Check |
| --- | --- |
| `SentenceLength` | Each sentence has 25 words or fewer. |
| `ParagraphLength` | Each paragraph has 6 sentences or fewer. |
| `PassiveVoice` | No form of "be" comes before a past participle. |
| `PlainWords` | The text does not use a word from a list of complex words. The message gives the simple word. |

The `docs` CI job runs the gate, and `verify` requires that job. A tool cannot
tell a procedural sentence from a descriptive sentence, so review checks the
20-word limit. Review also checks the rules that no tool can check.

The gate does not check these files:

- `CHANGELOG.md`, because release-please writes it;
- the test fixtures in `testdata` directories and in `tests/fixtures/`;
- the assets of packs and kits, because they can hold in-world content.

## Voice

- Write to the reader. Use "you", the present tense, and active verbs.
- Write one idea in each sentence. A short sentence is better than a long
  sentence with a clause.
- Start with the concrete. A worked example is better than a paragraph of
  abstraction.
- Define a term once, where it first occurs. Then use it with that meaning
  only.
- Remove hedges and context that the reader already has. State the fact.

## What to avoid

- Do not start a page with a boundary statement, a mission, or a list of
  caveats. First tell what the thing is and what it is for. Then tell the
  limits.
- Do not use strings of abstract nouns, such as "the canonical shared contract
  boundary". Name the concrete thing that does the work.
- Do not use marketing words, such as "seamless", "powerful", or "robust". Do
  not promise a roadmap, and do not claim adoption.
- Keep internal process words out of the public pages: issue numbers,
  milestones, and review state. They belong in the developer documents.

## Structure for a task page

An entry page, such as a quickstart or a how-to page, has this order:

1. The task and its outcome, in one line.
2. The prerequisites.
3. The exact steps, as commands.
4. The meaning of each placeholder.
5. The real output.
6. The boundary: what the reader has not done.
7. A link to the next page.

## Examples and commands

- Show each command with its real output. Run the command, and do not
  paraphrase the output.
- Make each example synthetic and temporary. Create it in a scratch directory,
  as the test suite does.
- Show the smallest example that is valid, not a small example that fails.

## Links

- Link between public pages with relative `.md` paths.
- To refer to a developer record from a public page, use an absolute GitHub
  URL. A developer record is, for example, an ADR or the CI notes.
- Do not use a relative path out of `docs/public/`. Such a path breaks the
  build, and it puts an internal record on the site.

## The boundary is a build gate

`docs/public/` is the only tree that the site builds (ADR 0030). Keep internal
records out of it. The docs build treats warnings as errors, and it is part of
the `verify` merge gate. So CI finds a broken cross-reference before a reader
does.

## Go documentation

- Each package has a package comment in one file of the package. The comment
  starts with "Package" and the package name, and it tells what the package
  does.
- Each exported identifier has a doc comment that starts with the name of the
  identifier.
- Write each doc comment in complete sentences, and end each sentence with a
  period.
- Give the main operations of a library package a runnable example. An example
  is a function `ExampleXxx` in a test file, with an `// Output:` comment. `go
  test` runs the example and compares its output with the comment.
- `make go-lint` checks the package comments, the doc comments, and the final
  periods. It also checks that each example has an output comment. See the
  [Go style map](go-style-map.md).
