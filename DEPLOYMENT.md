# Amsterdam Restaurants Map - Deployment Guide

## Option 1: Quick Deploy to Vercel (Recommended)

### Step 1: Prepare Static Files
```bash
# Run this from your project directory
python3 prepare_static_deploy.py
```

This will create a `deploy/` folder with all static files.

### Step 2: Deploy to Vercel

**Method A: Using Vercel CLI (Fastest)**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd deploy
vercel --prod
```

**Method B: Using GitHub + Vercel Dashboard**
1. Create a new GitHub repository
2. Push the `deploy/` folder contents:
   ```bash
   cd deploy
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```
3. Go to [vercel.com](https://vercel.com)
4. Click "New Project"
5. Import your GitHub repository
6. Deploy!

---

## Option 2: Quick Local Sharing (No Setup Required)

Share your local server temporarily using ngrok:

```bash
# Install ngrok
brew install ngrok

# Share your local server
ngrok http 8000
```

This gives you a public URL like `https://abc123.ngrok.io` that anyone can access while your server is running.

---

## Option 3: GitHub Pages (Free, No Backend)

```bash
cd deploy
git init
git add .
git commit -m "Deploy to GitHub Pages"
git branch -M gh-pages
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin gh-pages
```

Then enable GitHub Pages in your repo settings.

---

## Notes

- The deployed version will be **static** (no live updates from scraper)
- To update data: Run `python3 prepare_static_deploy.py` again and redeploy
- Your local Python backend stays private
- The map and all features work perfectly as static files
