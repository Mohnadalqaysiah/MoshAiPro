# Quick Deployment Guide — Confidence Fix

## What Was Fixed
Daily Telegram briefing showing `0%` confidence despite backend calculating correct scores.

## Root Cause
Bot tried to extract `ai_confidence_score` from top level but backend nests it inside `data` dict with multiple possible field names (`ai_confidence_score`, `ai_confidence`, `confidence_score`, etc.)

## Solution
Created unified `get_confidence()` helper that checks all known field names and nesting patterns.

## Modified Files
- `telegram-bot/bot.py` — 6 confidence extraction points updated

## Git Commit
```
067d790 fix: hardened Telegram bot confidence reporting with unified get_confidence() helper
```

## Deploy Commands

```bash
# SSH into server
ssh root@srv1263799

# Navigate to project
cd ~/mosh-ai-pro

# Pull latest changes
git pull origin main

# Rebuild Telegram bot container
docker compose -f docker-compose.prod.yml build --no-cache telegram

# Restart bot
docker compose -f docker-compose.prod.yml up -d telegram

# Verify running
docker ps | grep moshapi_telegram

# Check logs
docker logs moshapi_telegram -f --tail 50
```

## Verification Checklist
- [ ] Docker container restarted
- [ ] No errors in logs
- [ ] Next day's 05:00 UTC briefing shows confidence values
- [ ] Watchlist alerts display confidence
- [ ] Signal listing shows confidence values

## Expected Log Output
```
📰 بدء مهمة التقرير الصباحي…
🔍 دورة مراقبة — X مستخدم (من DB)
[broker_session...] Daily briefing: 3 markets analyzed, all successful
```

## Expected Daily Briefing Format
```
🌅 *صباح الخير — التقرير اليومي*
━━━━━━━━━━━━━━━━━━━━
📅 الاثنين 24/05/2026

📊 *نظرة 4H على الأسواق الرئيسية:*
• 🥇 الذهب: 📈 شراء | ثقة `65%` | `2350.25`
• ₿ بيتكوين: 📉 بيع | ثقة `58%` | `62500.00`
• 💶 EUR/USD: ⏳ انتظار | ثقة `45%` | `1.0850`
```

## Rollback (if needed)
```bash
git revert 067d790 --no-edit
git push origin main
docker compose -f docker-compose.prod.yml build --no-cache telegram
docker compose -f docker-compose.prod.yml up -d telegram
```

## Support Contact
Contact: GitHub issue or review in MoshAiPro repository
