# Blog

Personal website/blog built with Next.js, MDX, and Tailwind CSS.

## Local development

Install dependencies:

```bash
npm install
```

Create `.env.local`:

```bash
NEXT_PUBLIC_SITE_URL=https://example.com
```

Run dev server:

```bash
npm run dev
```

## Deploying to GitHub Pages

This repo is configured to deploy automatically with GitHub Actions from the `main` branch.

1. Create a GitHub repo and push this project.
2. In GitHub, go to `Settings` -> `Pages`.
3. Under `Build and deployment`, set `Source` to `GitHub Actions`.
4. Push to `main` and wait for the `Deploy to GitHub Pages` workflow to finish.

The workflow builds static output (`out/`) and publishes it to GitHub Pages.
