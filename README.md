# ImageCraft - AI Image Editor

A powerful web-based image editing application with AI-powered features, including traditional editing tools, AI image enhancement, and **text-to-image generation** (like "nano banana").

## Key Features

### Traditional Image Editing
- **Basic Operations:** Rotate, flip, crop, resize
- **Filters:** Brightness, contrast, saturation, sharpness, blur
- **Advanced:** Sharpen, emboss, edges, enhance, grayscale
- **Interactive Tools:** Modal-based crop and resize with presets

### AI-Powered Features
- **AI Image Editing:** Modify images using text prompts
- **AI Image Generation:** Create images from text descriptions (nano banana feature!)
- **Text-to-Image:** Powered by Stable Diffusion XL
- **Customizable:** Control size, quality, and generation parameters

### Subscription System
- **Free Tier:** Limited operations, temporary storage (24h)
- **Premium Tier:** Unlimited operations, permanent storage, priority queue
- **Payment:** Razorpay integration for seamless subscriptions

### User Management
- User registration and authentication
- Profile management
- Password change and reset
- Subscription management portal
- Download history tracking

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p uploads processed

# Configure environment (copy and edit .env)
cp .env.example .env

# Start services (in separate terminals)
mongod                    # MongoDB
redis-server             # Redis
rq worker image_tasks    # RQ Worker
python run.py           # Flask App
```

Visit `http://localhost:5000` and start editing!

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Installation and setup guide
- **[UPDATES.md](UPDATES.md)** - Comprehensive feature documentation
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production deployment guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Project overview

## 🔧 Technology Stack

- **Backend:** Flask, Python, Pillow, RQ
- **Database:** MongoDB (Supabase migration ready)
- **Queue:** Redis
- **AI:** Hugging Face (Stable Diffusion XL)
- **Payment:** Razorpay
- **Frontend:** HTML5, CSS3, JavaScript

## 🎯 Project Status

✅ **Development Complete** - All features implemented
🟡 **Testing Pending** - Requires external service configuration
🟡 **Deployment Ready** - Comprehensive guides provided

## 📦 Requirements

- Python 3.8+
- MongoDB
- Redis
- Razorpay Account (for payments)
- Hugging Face API Token (for AI features)

## 🔐 Security

- Bcrypt password hashing
- CSRF protection
- Secure payment verification
- File validation and size limits
- Rate limiting
- User authentication

## 📝 License

This project is part of ImageCraft. All rights reserved.

## 🤝 Support

For setup help, troubleshooting, or deployment assistance, refer to the comprehensive documentation provided in the project.
