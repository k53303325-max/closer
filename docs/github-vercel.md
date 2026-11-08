# GitHub + Vercel

## GitHub (один раз)

```bash
cd /Users/mark/Desktop/Closer-app   # путь только латиницей — иначе Vercel CLI ломается
/tmp/gh_2.67.0_macOS_amd64/bin/gh auth login -h github.com -p https -w
bash scripts/setup_github.sh
```

Или вручную: [github.com/new](https://github.com/new) → репо `closer-deal` →

```bash
git remote add origin git@github.com:YOU/closer-deal.git
git push -u origin main
```

## Vercel ↔ Git

В [vercel.com](https://vercel.com) → проект **closer-deal** → Settings → Git → Connect Repository.

CLI `vercel git connect` иногда падает из‑за не-ASCII пути; рабочая копия: `~/Desktop/Closer-app`.
