# Launch checklist

*Informative. Everything that must be done before this repository goes public. It is private until then.*

## Name and brand

- [ ] Choose the public name (currently the working name "Earned Autonomy").
- [ ] Trademark search in software and AI classes, in Australia and the main export markets.
- [ ] Secure domains and the GitHub organisation or repository name.
- [ ] Rename throughout: a search and replace, then re-run the tests.

## Licences and citation

- [x] Add `LICENSE` (Apache-2.0) for the engine, conformance tests and research code.
- [x] Add `LICENSE-docs` (CC BY 4.0) for the principles, guide, primer, specification and reports.
- [x] State in the README which licence covers which folder.
- [ ] Add `CITATION.cff` so the research can be cited.

## Research reports

- [ ] Produce **sanitised public copies** of the research reports and decisions log:
  - remove personal names;
  - move the commercial platform's internals (file paths, internal component names, how its checks and judges work)
    into a private appendix, and describe it as "a commercial agent platform".
- [ ] **Do not edit the originals.** The pre-registrations, reports and decisions log are evidence. Their value rests on
  being provably unchanged since they were written, so the public copies sit beside them, clearly marked as edited
  copies, and the originals stay in the private history.
- [ ] Add independent timestamping of the pre-registration commits (for example, publish the tag hashes publicly or use
  a timestamping service), so the dates don't rely only on our own machines.
- [ ] Re-check that no customer data, API keys or internal URLs remain anywhere in the history.

## Content

- [ ] Remove internal references (internal tools, private links, team memory paths).
- [ ] Verify every mapping in [CROSSWALKS.md](../CROSSWALKS.md) against the current version of each framework.
- [ ] External review of the specification and the research by someone outside Hivemind Labs.
- [ ] Results from at least one real-world pilot, or a clear statement that all evidence is synthetic.
- [ ] Final pass for plain language and no abbreviations.

## Release

- [ ] Freeze the specification at v1.0 (or a dated public review draft) and tag it.
- [ ] Publish the engine package.
- [ ] Announce: article, LinkedIn, partners.
