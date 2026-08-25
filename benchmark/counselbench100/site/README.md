# CounselBench-100 benchmark page

Public release page for CounselBench-100. It is a static, anonymous-compatible
vinext site with no database or runtime secrets.

## Development

```bash
npm install
npm run dev
```

## Verification

```bash
npm run lint
npm test
```

The rendered-page tests pin the public dataset links, benchmark counts, release
metadata, accessibility motion fallback, and removal of the starter scaffold.
