# ImageCraft - Deployment & Configuration Checklist

## ✅ Pre-Deployment Setup

### 1. External Services Configuration

#### MongoDB Setup
- [ ] Create MongoDB Atlas account (or set up local MongoDB)
- [ ] Create new cluster (M0 free tier for testing)
- [ ] Whitelist IP addresses for connection
- [ ] Get connection string
- [ ] Create database: `image_editor`
- [ ] Update `MONGO_URI` in `.env`

#### Redis Setup
- [ ] Install Redis locally OR use Redis Cloud
- [ ] For local: `brew install redis` (Mac) or `apt-get install redis-server` (Ubuntu)
- [ ] Start Redis: `redis-server`
- [ ] Update `REDIS_HOST` and `REDIS_PORT` in `.env`

#### Razorpay Setup
- [ ] Create account at https://razorpay.com
- [ ] Get Test API Keys from Dashboard → Settings → API Keys
- [ ] Update `RAZORPAY_KEY_ID` in `.env`
- [ ] Update `RAZORPAY_KEY_SECRET` in `.env`
- [ ] Generate webhook secret
- [ ] Update `RAZORPAY_WEBHOOK_SECRET` in `.env`
- [ ] For production: Switch to Live keys

#### Hugging Face Setup
- [ ] Create account at https://huggingface.co
- [ ] Go to Settings → Access Tokens
- [ ] Create new token with "read" permissions
- [ ] Update `HF_API_TOKEN` in `.env`
- [ ] Test with: `curl https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0 -H "Authorization: Bearer YOUR_TOKEN"`

#### Supabase Setup (Optional - Future)
- [ ] Create account at https://supabase.com
- [ ] Create new project
- [ ] Get project URL and anon key from Settings → API
- [ ] Update `VITE_SUPABASE_URL` in `.env`
- [ ] Update `VITE_SUPABASE_SUPABASE_ANON_KEY` in `.env`
- [ ] Run migration script (when ready)

---

## ✅ Local Development Setup

### 2. Installation Steps

- [ ] Clone repository
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate: `source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy `.env.example` to `.env` (if exists) or create new `.env`
- [ ] Fill in all environment variables in `.env`
- [ ] Create directories: `mkdir -p uploads processed`
- [ ] Verify MongoDB connection
- [ ] Verify Redis connection

### 3. Start Services

Terminal 1 - MongoDB:
```bash
mongod  # or use Atlas connection
```

Terminal 2 - Redis:
```bash
redis-server
```

Terminal 3 - RQ Worker:
```bash
source venv/bin/activate
rq worker image_tasks
```

Terminal 4 - Flask App:
```bash
source venv/bin/activate
python run.py
```

### 4. Initial Testing

- [ ] Visit `http://localhost:5000`
- [ ] Register test account
- [ ] Login successfully
- [ ] Upload test image
- [ ] Try basic edit (rotate/flip)
- [ ] Try filter (brightness)
- [ ] Try AI edit (if HF token configured)
- [ ] Generate AI image (nano banana!)
- [ ] Download edited image
- [ ] Test subscription flow (with Razorpay test keys)

---

## ✅ Production Deployment

### 5. Server Setup

#### Option A: VPS (DigitalOcean, Linode, AWS EC2)

- [ ] Provision Ubuntu 20.04+ server
- [ ] Update system: `sudo apt update && sudo apt upgrade`
- [ ] Install Python 3.8+: `sudo apt install python3.8 python3-pip`
- [ ] Install MongoDB: Follow official guide
- [ ] Install Redis: `sudo apt install redis-server`
- [ ] Install Nginx: `sudo apt install nginx`
- [ ] Install Supervisor: `sudo apt install supervisor`
- [ ] Clone repository to `/var/www/imagecraft`
- [ ] Set up virtual environment
- [ ] Install dependencies
- [ ] Configure `.env` with production values

#### Option B: Platform as a Service (Heroku, Render)

- [ ] Create account on chosen platform
- [ ] Install CLI tool
- [ ] Add buildpacks (Python)
- [ ] Configure environment variables
- [ ] Add MongoDB addon (mLab, MongoDB Atlas)
- [ ] Add Redis addon (Redis Cloud, Heroku Redis)
- [ ] Deploy application
- [ ] Scale worker dynos for RQ

### 6. Web Server Configuration

#### Nginx Configuration
Create `/etc/nginx/sites-available/imagecraft`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/imagecraft/app/static;
        expires 30d;
    }
}
```

- [ ] Enable site: `sudo ln -s /etc/nginx/sites-available/imagecraft /etc/nginx/sites-enabled/`
- [ ] Test config: `sudo nginx -t`
- [ ] Restart Nginx: `sudo systemctl restart nginx`

#### SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

- [ ] Install certbot
- [ ] Generate SSL certificate
- [ ] Enable auto-renewal: `sudo certbot renew --dry-run`

### 7. Process Management (Supervisor)

Create `/etc/supervisor/conf.d/imagecraft.conf`:

```ini
[program:imagecraft]
command=/var/www/imagecraft/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
directory=/var/www/imagecraft
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/imagecraft/app.err.log
stdout_logfile=/var/log/imagecraft/app.out.log

[program:imagecraft-worker]
command=/var/www/imagecraft/venv/bin/rq worker image_tasks
directory=/var/www/imagecraft
user=www-data
autostart=true
autorestart=true
numprocs=2
process_name=%(program_name)s_%(process_num)02d
stderr_logfile=/var/log/imagecraft/worker.err.log
stdout_logfile=/var/log/imagecraft/worker.out.log
```

- [ ] Create config file
- [ ] Create log directory: `sudo mkdir -p /var/log/imagecraft`
- [ ] Update supervisor: `sudo supervisorctl reread`
- [ ] Start processes: `sudo supervisorctl update`
- [ ] Check status: `sudo supervisorctl status`

### 8. Firewall Configuration

```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

- [ ] Configure UFW firewall
- [ ] Allow necessary ports
- [ ] Enable firewall

### 9. Database Security

- [ ] Enable MongoDB authentication
- [ ] Create application user with limited permissions
- [ ] Update connection string with credentials
- [ ] Enable SSL for MongoDB connections (production)
- [ ] Configure backup strategy
- [ ] Set up automated backups

### 10. Application Security

- [ ] Generate strong `FLASK_SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Update all secrets in `.env`
- [ ] Set `FLASK_ENV=production`
- [ ] Disable debug mode
- [ ] Configure rate limiting
- [ ] Set up CORS properly
- [ ] Review and tighten CSP headers
- [ ] Implement request logging
- [ ] Set up intrusion detection

---

## ✅ Monitoring & Maintenance

### 11. Monitoring Setup

- [ ] Set up error tracking (Sentry)
- [ ] Configure application monitoring (DataDog, New Relic)
- [ ] Set up uptime monitoring (UptimeRobot)
- [ ] Configure log aggregation (ELK stack, Papertrail)
- [ ] Set up alerts for errors and downtime
- [ ] Monitor disk space for uploads
- [ ] Monitor Redis memory usage
- [ ] Monitor MongoDB performance

### 12. Backup Strategy

- [ ] Configure daily MongoDB backups
- [ ] Set up S3/cloud storage for image backups
- [ ] Test restore procedure
- [ ] Document backup locations
- [ ] Set backup retention policy (30 days recommended)
- [ ] Automate backup verification

### 13. Maintenance Tasks

Daily:
- [ ] Check application logs for errors
- [ ] Monitor server resources
- [ ] Check RQ queue status

Weekly:
- [ ] Review error reports
- [ ] Check disk space usage
- [ ] Clean temporary files
- [ ] Review security logs

Monthly:
- [ ] Update dependencies (security patches)
- [ ] Review and optimize database indexes
- [ ] Analyze performance metrics
- [ ] Review and clean old processed images (based on expiration)
- [ ] Test backup restore

---

## ✅ Post-Deployment

### 14. Testing in Production

- [ ] Register test account
- [ ] Test complete user flow
- [ ] Test payment integration with Razorpay test mode
- [ ] Test AI generation (with rate limits)
- [ ] Test file upload/download
- [ ] Test on mobile devices
- [ ] Test with different browsers
- [ ] Load test with ab/siege
- [ ] Verify SSL certificate
- [ ] Test error pages (404, 500)

### 15. Documentation

- [ ] Document deployment process
- [ ] Create runbook for common issues
- [ ] Document backup/restore procedures
- [ ] Create user guide
- [ ] Document API endpoints
- [ ] Create admin documentation

### 16. Launch Preparation

- [ ] Switch Razorpay to Live keys
- [ ] Configure production email service (for password resets)
- [ ] Set up CDN for static assets (Cloudflare)
- [ ] Configure analytics (Google Analytics)
- [ ] Prepare marketing materials
- [ ] Set up support channels
- [ ] Create FAQ page
- [ ] Test customer journey end-to-end

---

## ✅ Optional Enhancements

### 17. Advanced Features

- [ ] Implement automated testing (pytest)
- [ ] Set up CI/CD pipeline (GitHub Actions, GitLab CI)
- [ ] Configure staging environment
- [ ] Set up load balancer (for multiple servers)
- [ ] Implement caching layer (Redis cache)
- [ ] Configure CDN for images
- [ ] Implement WebSocket for real-time updates
- [ ] Add batch processing UI
- [ ] Implement admin dashboard
- [ ] Add user analytics
- [ ] Implement referral system
- [ ] Add social media sharing
- [ ] Implement API rate limiting per user
- [ ] Add webhook notifications
- [ ] Implement team/organization features

### 18. Scalability

- [ ] Set up auto-scaling for RQ workers
- [ ] Implement horizontal scaling
- [ ] Use S3/Cloudinary for file storage
- [ ] Set up database read replicas
- [ ] Implement caching strategy
- [ ] Use message queue for heavy operations
- [ ] Implement job priority system
- [ ] Configure connection pooling
- [ ] Optimize database queries
- [ ] Implement lazy loading for images

---

## 🚨 Critical Environment Variables

**Required for production:**

```env
FLASK_SECRET_KEY=[REQUIRED - 32+ char random string]
FLASK_ENV=production
MONGO_URI=[REQUIRED - MongoDB connection string]
REDIS_HOST=[REQUIRED - Redis server]
RAZORPAY_KEY_ID=[REQUIRED - For payments]
RAZORPAY_KEY_SECRET=[REQUIRED - For payments]
HF_API_TOKEN=[REQUIRED - For AI features]
```

**Security:**
- Never commit `.env` to version control
- Use environment variables or secret management service
- Rotate secrets regularly
- Use different keys for dev/staging/production

---

## 📞 Support & Troubleshooting

### Common Issues

**App won't start:**
- Check MongoDB connection
- Verify Redis is running
- Check all environment variables are set
- Review application logs

**RQ jobs not processing:**
- Start RQ worker
- Check Redis connection
- Verify queue name matches configuration

**Payment fails:**
- Verify Razorpay keys are correct
- Check webhook signature matches
- Review Razorpay dashboard for errors

**AI features not working:**
- Verify HF_API_TOKEN is valid
- Check API quota/rate limits
- Review Hugging Face model status

---

## ✅ Sign-Off

### Development Team
- [ ] All features implemented
- [ ] Code reviewed
- [ ] Tests passed
- [ ] Documentation complete
- [ ] Deployment guide ready

### DevOps/Deployment
- [ ] Server configured
- [ ] Services running
- [ ] Monitoring active
- [ ] Backups configured
- [ ] SSL certificate installed

### Client/Stakeholder
- [ ] Features reviewed
- [ ] Testing complete
- [ ] Training completed (if needed)
- [ ] Go-live approved

---

**Deployment Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

Last Updated: [Date]
Deployed By: [Name]
Production URL: [URL]
