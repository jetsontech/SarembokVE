# SarembokVE & Sarembok — Technical SEO and Entity Handoff

## Objective

Establish `SarembokVE` and `Sarembok` as one authoritative software brand and platform, while prioritizing `SarembokVE` for exact-match discovery.

## Implementation Status

- Homepage title, description, canonical, Open Graph, Twitter, robots, and JSON-LD added to the local `production-index.html` artifact and tracked `fabric/ui/index.html` fallback.
- Primary visible homepage identity now begins with `SarembokVE` and includes its AI compute and orchestration purpose.
- Organization, Website, and SoftwareApplication entities added as a linked JSON-LD graph.
- `public/robots.txt`, `public/sitemap.xml`, `public/logo.svg`, and `public/og-banner.svg` created; high-resolution `public/logo.png` and `public/og-banner.png` generated for social/schema metadata.
- `package.json` and `README.md` updated with exact-match brand language and an official homepage link.

## Deployment Requirements

1. **Resolve the homepage source before release.** `production-index.html` is ignored by `.gitignore` and is not included in Git commits. `fabric/ui/server_ui.js` serves `frontend/index.html` when present, otherwise it serves `fabric/ui/index.html`; the latter is tracked and now contains the metadata. The live homepage currently has a different title and only a basic `WebSite` JSON-LD object, so verify which source is deployed and port the metadata into that source.
2. Publish or copy these public assets to the domain root:
   - `/robots.txt`
   - `/sitemap.xml`
   - `/logo.png`
   - `/og-banner.png`
3. The live audit found `/logo.png` and `/og-banner.png` currently return HTTP 404. Deploy the PNGs and verify both return HTTP 200 with `image/png` before requesting social-card crawls.
4. Configure the canonical host to serve `https://sarembok.com/` with redirects from `www`, HTTP, and alternate hostnames.
5. Do not create duplicate landing pages for Sarembok and SarembokVE. Link both names consistently to the canonical homepage.

## Entity Data

Primary entity name: `SarembokVE`

Alternative names:
- `Sarembok`
- `Sarembok VE`
- `Sarembok AI`

Canonical URL: `https://sarembok.com`

Official repository: `https://github.com/jetsontech/SarembokVE`

Official npm package: `https://www.npmjs.com/package/sarembok`

## Source of Truth

`README.md`, `package.json`, `production-index.html`, and `public/robots.txt` must use the same primary and alternate brand names. Do not introduce invented companies, publication claims, awards, or customer names.

## Claims Guidance

Accurate product categories include:
- AI-native execution runtime
- Distributed heterogeneous compute mesh
- Deterministic multi-agent orchestration
- Zero-trust execution fabric
- OpenAPI contract verification and drift gating
- SQLite-WAL state management
- Distributed consensus

Only describe GPU or agent capabilities as available when matching implementation and deployment documentation are present.

## Search Console Actions

The following actions require access to the domain and Google/Bing properties; they cannot be completed by code alone:

1. Add `sarembok.com` as a Domain property in Google Search Console.
2. Verify domain ownership using the provider DNS TXT record.
3. Submit `https://sarembok.com/sitemap.xml`.
4. Inspect `https://sarembok.com/` and request indexing after deployment.
5. Repeat the request only after significant canonical or metadata changes.
6. Add and verify the equivalent property in Bing Webmaster Tools.

## Directory and Registry Actions

1. Ensure the GitHub repository description prominently contains `SarembokVE (Sarembok)` and the website field is `https://sarembok.com`.
2. Ensure the npm package README contains direct, exact-match links to `https://sarembok.com`.
3. Preserve the npm repository and homepage fields.
4. Publish an npm patch or minor release after deployment to expose updated metadata.
5. Add additional official `sameAs` links only after GitHub, npm, LinkedIn, or other profiles are actually owned and public.

## Wikidata Guidance

Do not create a Wikidata item until independently verifiable publication, package, repository, or documentation citations exist. The item should use verifiable sources and should not claim a broad market category without evidence.

## Validation Checklist

- Homepage returns HTTP 200 and includes the canonical link in its rendered `<head>`.
- `/robots.txt` returns HTTP 200 and is plain text.
- `/sitemap.xml` returns HTTP 200 and is valid XML.
- `/logo.png` and `/og-banner.png` return HTTP 200 with `image/png` content types.
- The homepage's primary visible heading begins with `SarembokVE`.
- The JSON-LD script parses with no syntax errors.
- Organization `@id`, Website `publisher`, and SoftwareApplication `publisher` resolve to `https://sarembok.com/#organization`.
- Google Rich Results Test, Schema.org validator, and Bing URL inspection report no errors.
- npm and GitHub README links resolve and use exact brand names.

## Launch Priority

Treat `SarembokVE` as the primary product and engineering name. Use `Sarembok` as the established brand and alternate name. Maintain both in titles, descriptions, repository text, package metadata, and launch citations.
