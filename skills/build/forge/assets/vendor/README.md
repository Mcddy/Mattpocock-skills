# Vendored files for scripts/design_page.py

Third-party files bundled so the design page renders with no network. Nothing here is edited by hand.

- **Mermaid 11.17.2** (published on npm 25 Aug 2025), MIT licence, text in `mermaid-LICENSE.txt`. `mermaid-11.17.2.min.js.gz` is the package's `dist/mermaid.min.js` (3,572,661 bytes) compressed with gzip, because the plain file is just over the 3.5 MB budget for this folder; `design_page.py` decompresses it in memory. SHA-256 of the decompressed file: `581ed7d74bd9048d0e3a91363927d72ef22942d7722546b27f7cc29e35390eb8`. Source: `https://registry.npmjs.org/mermaid/-/mermaid-11.17.2.tgz` (integrity `sha512-V6K3C8EBdEsPFZXSKMJe6ppQOENxuHARr9GvHX4hh47lAbhMRD9qf4oEK7LoaRQxULMa80/qt5gHO73aCleBBg==`). If this file is missing, the script fetches the same version with `npm pack` into `~/.cache/forge-mermaid` and checks the same SHA-256.
- **Hanken Grotesk** 400, 400 italic and 700, latin subset, from `@fontsource/hanken-grotesk` 5.3.0, SIL Open Font License 1.1, text in `fonts/hanken-grotesk-LICENSE.txt`. Embedded in every design page and used to draw the diagrams, so labels measured in Chromium fit their boxes on the reader's machine.

To check the Mermaid file: `python3 -c "import gzip,hashlib;print(hashlib.sha256(gzip.decompress(open('mermaid-11.17.2.min.js.gz','rb').read())).hexdigest())"`
