#!/bin/sh
# Deploy the front end to Cloudflare Pages: the page, logos, SEO files and the two Pages Functions.
# One-time setup:
#   npx wrangler pages project create <name> --production-branch main
#   printf '%s' "https://your-race-server.example.com" | npx wrangler pages secret put RH_ORIGIN --project-name <name>
#   printf '%s' "<same value as RH_PROXY_SECRET in .env>" | npx wrangler pages secret put RH_PROXY_SECRET --project-name <name>
#   (optional) RH_SITE = your public URL, used in link previews
set -e
cd "$(dirname "$0")"
PROJECT="${1:-airabbithole}"
rm -rf dist && mkdir -p dist
cp ../web/index.html dist/ && cp -R ../web/logos dist/logos
cp -R functions dist/functions && cp robots.txt sitemap.xml llms.txt dist/
cd dist && npx wrangler pages deploy . --project-name "$PROJECT" --branch main
