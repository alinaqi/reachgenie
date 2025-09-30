# LinkedIn Integration - Implementation Checklist

## 🚀 Quick Start (Estimated: 2-3 hours)

### 1. ⚙️ Environment Setup (15 min)
- [ ] ✅ Updated `.env` with Unipile credentials
- [ ] Get your DSN from [Unipile Dashboard](https://dashboard.unipile.com) (top-right corner)
- [ ] Replace `UNIPILE_DSN` in `.env` with your actual DSN
- [ ] Generate webhook secret: `openssl rand -hex 16`

### 2. 🗄️ Database Migration (10 min)
```bash
cd /Users/admin/Documents/AI-Playground/ReachGenie/backend

# Run migration
psql -U your_user -d your_database -f migrations/linkedin_support/001_add_linkedin_support.sql

# Verify tables created
psql -U your_user -d your_database -c "\dt linkedin_*"
```

### 3. 📝 Update Config (5 min)
Add to `src/config.py`:
```python
# Unipile API settings
unipile_api_key: str = Field(..., env='UNIPILE_API_KEY')
unipile_dsn: str = Field(..., env='UNIPILE_DSN')
unipile_webhook_secret: Optional[str] = Field(None, env='UNIPILE_WEBHOOK_SECRET')

# LinkedIn Feature Configuration
linkedin_messaging_enabled: bool = Field(True, env='LINKEDIN_MESSAGING_ENABLED')
linkedin_daily_invite_limit: int = Field(80, env='LINKEDIN_DAILY_INVITE_LIMIT')
linkedin_daily_profile_view_limit: int = Field(100, env='LINKEDIN_DAILY_PROFILE_VIEW_LIMIT')
linkedin_message_delay_seconds: int = Field(20, env='LINKEDIN_MESSAGE_DELAY_SECONDS')
```

### 4. 🔌 Register Routes (10 min)
In `src/main.py`, add:
```python
from src.routes import linkedin, unipile_webhooks

# Add after other route registrations
app.include_router(linkedin.router)
app.include_router(unipile_webhooks.router)
```

### 5. 📦 Install Dependencies (5 min)
```bash
# Add to requirements.txt
aiohttp>=3.8.0

# Install
pip install -r requirements.txt
```

### 6. 🔗 Configure Unipile Webhooks (15 min)
1. Log into [Unipile Dashboard](https://dashboard.unipile.com)
2. Go to **Webhooks** section
3. Add these webhooks:

| Event | URL | Headers |
|-------|-----|---------|
| Account Status | `https://your-domain.com/api/v1/webhooks/unipile/account-status` | `Content-Type: application/json` |
| New Message | `https://your-domain.com/api/v1/webhooks/unipile/new-message` | `Content-Type: application/json` |

4. Set webhook secret to match your `.env`

### 7. 🧪 Test Connection (20 min)
```bash
# Start backend
cd backend
nvm use node
python main.py

# Test API endpoint
curl -X POST http://localhost:8000/api/v1/linkedin/connect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "your-company-uuid"}'
```

### 8. 🎨 Frontend Integration (60-90 min)
1. Copy components from `frontend_example.tsx`
2. Add to your company settings page
3. Update campaign creation form
4. Add LinkedIn fields to campaign type

### 9. ✅ Verification Steps
- [ ] Can generate LinkedIn auth URL
- [ ] Webhook endpoints return 200 OK
- [ ] Database tables created correctly
- [ ] Config loads Unipile settings
- [ ] Routes registered in FastAPI

## 🔍 Common Issues & Solutions

### "Module not found: linkedin_service"
```bash
# Make sure you copied all service files
cp migrations/linkedin_support/*.py src/services/
cp migrations/linkedin_support/message_generation.py src/ai_services/
```

### "401 Unauthorized from Unipile"
- Check API key in `.env`
- Verify no extra spaces or quotes
- Confirm key is active in Unipile dashboard

### "Cannot connect to Redis"
```bash
# Install and start Redis
brew install redis  # macOS
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

### "Webhook signature validation failed"
- Ensure `UNIPILE_WEBHOOK_SECRET` matches dashboard
- Check for trailing newlines in secret
- Verify webhook URL is HTTPS in production

## 📊 Testing the Integration

### 1. Manual Testing Flow
1. Connect a test LinkedIn account
2. Create a campaign with 2-3 test leads
3. Send messages
4. Check webhook logs
5. Verify database entries

### 2. API Testing
```python
# test_linkedin.py
import asyncio
from src.services.linkedin_service import linkedin_service

async def test_connection():
    # Test creating auth link
    result = await linkedin_service.create_hosted_auth_link(
        company_id="test-company-id",
        user_id="test-user-id",
        success_redirect_url="http://localhost:5173/success",
        failure_redirect_url="http://localhost:5173/failure"
    )
    print(f"Auth URL: {result['url']}")

asyncio.run(test_connection())
```

### 3. Webhook Testing
```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/api/v1/webhooks/unipile/account-status \
  -H "Content-Type: application/json" \
  -H "X-Unipile-Signature: test" \
  -d '{
    "AccountStatus": {
      "account_id": "test-123",
      "account_type": "LINKEDIN",
      "message": "OK"
    }
  }'
```

## 🚦 Go-Live Checklist

### Pre-Production
- [ ] Test with 5+ different LinkedIn accounts
- [ ] Verify rate limiting works
- [ ] Test reconnection flow
- [ ] Confirm webhook security
- [ ] Load test with 100+ leads

### Production Deploy
- [ ] Update `WEBHOOK_BASE_URL` to production
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable HTTPS for webhooks
- [ ] Configure monitoring/alerts
- [ ] Document for team

### Post-Launch
- [ ] Monitor error logs
- [ ] Track daily limits
- [ ] Review campaign performance
- [ ] Gather user feedback
- [ ] Plan feature additions

## 💡 Next Features to Consider

1. **LinkedIn Sales Navigator Integration**
   - Advanced search filters
   - Lead recommendations
   - Account insights

2. **Smart Scheduling**
   - Timezone-aware sending
   - Optimal time detection
   - Calendar integration

3. **AI Enhancements**
   - Message variant testing
   - Response sentiment analysis
   - Auto-qualification

4. **Team Collaboration**
   - Multiple LinkedIn accounts
   - Shared templates
   - Territory management

## 📞 Need Help?

- **Unipile Support**: support@unipile.com
- **API Docs**: https://developer.unipile.com
- **Rate Limits**: Check dashboard for current usage
- **Webhooks**: Test with https://webhook.site

Remember: Start small, test thoroughly, scale gradually! 🎯
