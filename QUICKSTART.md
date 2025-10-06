# ImageCraft - Quick Start Guide

## Prerequisites

- Python 3.8+
- MongoDB (local or Atlas)
- Redis Server
- Razorpay Account (for payments)
- Hugging Face API Token (for AI features)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-change-this
FLASK_ENV=development

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=image_editor

# Redis (Task Queue)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
RQ_QUEUE_NAME=image_tasks
ALLOW_START_WITHOUT_REDIS=1

# File Upload
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_USER=100
UPLOAD_FOLDER=uploads
PROCESSED_FOLDER=processed

# Razorpay Payment Gateway
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_CURRENCY=INR
PREMIUM_PLAN_AMOUNT=29900

# AI Configuration (Hugging Face)
HF_API_TOKEN=hf_your_huggingface_api_token
HF_MODEL=stabilityai/stable-diffusion-xl-base-1.0
AI_PRIMARY_PROVIDER=huggingface

# Supabase (Optional - for future migration)
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

### 3. Create Required Directories

```bash
mkdir -p uploads processed
```

### 4. Start Services

#### Terminal 1: Start MongoDB
```bash
# If using local MongoDB
mongod

# Or use MongoDB Atlas connection string in .env
```

#### Terminal 2: Start Redis
```bash
redis-server
```

#### Terminal 3: Start RQ Worker
```bash
rq worker image_tasks
```

#### Terminal 4: Start Flask Application
```bash
python run.py
```

## Quick Test

1. Open browser to `http://localhost:5000`
2. Register a new account
3. Upload an image
4. Try basic edits (rotate, flip, filters)
5. Navigate to **Generate** tab to create AI images
6. Test the "nano banana" prompt!

## Feature Overview

### Image Editor (`/editing`)
- **Basic Operations:** Rotate, flip, crop, resize
- **Filters:** Brightness, contrast, saturation, sharpness, blur
- **Advanced:** Sharpen, emboss, edges, enhance
- **AI Edit:** Edit images using text prompts

### AI Generator (`/generate`)
- **Text-to-Image:** Create images from descriptions
- **Example:** "nano banana with intricate microscopic details"
- **Customizable:** Size, quality steps
- **Free Tier:** 512×512, 20 steps max
- **Premium:** Up to 1024×1024, 50 steps

### Subscription (`/pricing`)
- **Free:** Limited daily operations, temporary history (24h)
- **Premium:** Unlimited operations, permanent history, priority queue
- **Payment:** Razorpay integration (INR 299/month)

### Profile (`/profile`)
- Update name and personal info
- Change password securely
- View subscription status

## API Endpoints Reference

### Public
- `GET /` - Home page
- `GET /login` - Login page
- `POST /login` - Login user
- `GET /register` - Registration page
- `POST /register` - Register user
- `GET /forgot-password` - Password reset request

### Authenticated
- `GET /editing` - Image editor interface
- `POST /upload` - Upload image
- `POST /edit-task/<op>/<filename>` - Queue edit operation
- `POST /ai-edit-task/<filename>` - Queue AI edit
- `GET /job-status/<job_id>` - Check task status
- `GET /generate` - AI image generator
- `POST /generate-task` - Generate image from prompt
- `GET /profile` - User profile
- `POST /profile/update` - Update profile
- `POST /profile/change-password` - Change password
- `GET /subscription/manage` - Manage subscription
- `POST /subscription/create-order` - Create payment
- `POST /subscription/verify-payment` - Verify payment

## Troubleshooting

### Redis Connection Error
```
Error: Connection refused (Redis)
```
**Solution:** Start Redis server: `redis-server`

### RQ Worker Not Processing
```
Tasks stuck in queue
```
**Solution:** Start RQ worker: `rq worker image_tasks`

### MongoDB Connection Error
```
Error: ServerSelectionTimeoutError
```
**Solution:**
- Start MongoDB: `mongod`
- Or update `MONGO_URI` in `.env` with Atlas connection string

### AI Generation Fails
```
Error: AI API error: Unauthorized
```
**Solution:**
- Get valid Hugging Face API token from https://huggingface.co/settings/tokens
- Update `HF_API_TOKEN` in `.env`

### Image Upload Fails
```
Error: No such file or directory: 'uploads'
```
**Solution:** Create directories: `mkdir -p uploads processed`

### Payment Verification Fails
```
Error: Invalid payment signature
```
**Solution:**
- Check `RAZORPAY_KEY_SECRET` matches your Razorpay dashboard
- Ensure webhook secret is correctly configured

## Development Tips

### View RQ Job Status
```bash
rq info
```

### Clear Redis Queue
```bash
redis-cli
> FLUSHALL
```

### View MongoDB Data
```bash
mongo
> use image_editor
> db.users.find()
> db.uploads.find()
> db.processed_images.find()
```

### Check Logs
```bash
# Application logs
tail -f logs/app.log  # (if configured)

# RQ worker logs
rq info --url redis://localhost:6379
```

## Production Deployment

For production deployment, refer to `UPDATES.md` section 13 for complete checklist including:
- Use Gunicorn/uWSGI
- Set up Nginx reverse proxy
- Configure SSL certificates
- Set up monitoring
- Configure auto-scaling
- Use production MongoDB/Redis clusters

## Getting Help

1. Check `UPDATES.md` for detailed feature documentation
2. Review `README.md` for project overview
3. Check application logs for errors
4. Verify all environment variables are set correctly
5. Ensure all required services (MongoDB, Redis) are running

## Next Steps

- Set up automated testing (pytest)
- Configure email service for password resets
- Migrate to Supabase for better scalability
- Implement batch processing UI
- Add more AI models and features
- Set up CI/CD pipeline

## License & Support

This project is maintained as part of ImageCraft. For support, refer to the documentation or contact the development team.

---

**Happy Editing! 🎨✨**
