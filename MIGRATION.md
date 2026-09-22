# Blog migration

The Typecho backup was imported as 25 published posts and one page. Original
case-sensitive `/<slug>.html` URLs, timestamps and HTML bodies are preserved.
The Markdown friend-links page stays Markdown. No category assignments were
invented: the backup contains category definitions but no relationships.

## Local use

Install Hugo **0.166.0** and Python 3. Run `hugo server` to preview.
Run `python3 scripts/verify.py` to validate both deployment URL forms.
With Playwright available, run `hugo` and `node scripts/browser_check.cjs`
for desktop/mobile and search checks.

To re-import, run `python3 scripts/import_typecho.py /path/to/backup.dat`.
The original backup must stay outside the repository. The importer only exports
published, unprotected posts/pages, never account records or comments.
`migration/manifest.json` records the content inventory and attachment checksums.
Existing attachments are reused; all five were recovered from Internet Archive.
Source HTML is retained intentionally and enabled in Hugo's content policy.

The repository README and Metrics workflow retain their original roles.
The Hugo workflow ignores README/metrics-only changes, builds pull requests
without deployment, and deploys pushes to main using GitHub Actions Pages.
Generated `public/` output is not committed.

## Domain cutover

1. Enable Pages with GitHub Actions and first validate
   https://yangmame.github.io/YangMame/ .
2. Confirm all 26 old content paths, five attachments, search and layout work.
3. Set the repository's Pages custom domain to `blog.yangmame.org`; rerun
   Hugo Pages. Its build uses the URL returned by `actions/configure-pages`,
   so the custom domain does not retain `/YangMame/`.
4. Ask the domain owner to set the `blog` CNAME to `yangmame.github.io`
   (no scheme or path), replacing conflicting A/AAAA records at that name.
   The prior public DNS answers are in `migration/dns-before.json`.
5. Wait for DNS and GitHub certificate issuance, enable Enforce HTTPS,
   and verify the old URLs and assets through the custom domain.

Leave the old server running during the transition. To roll back, restore the
original DNS settings recorded by the DNS provider (public DNS answers may hide
an origin behind a proxy). Keep the recovered files and original backup.

External Wayback links remain intact. Only links to migrated pages and uploads
are localized. Source-era instructions and code examples are preserved as written.
