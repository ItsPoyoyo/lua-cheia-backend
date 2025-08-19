# 🚂 Railway Environment Variables Setup
## SuperParaguai E-commerce Platform

### **Step 1: Create .env file**
Create a file named `.env` in your `backend` folder and add the following content:

```bash
# ========================================
# DJANGO CORE SETTINGS
# ========================================
DEBUG=False
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ALLOWED_HOSTS=.railway.app,yourdomain.com,localhost,127.0.0.1

# ========================================
# DATABASE SETTINGS (Railway PostgreSQL)
# ========================================
# Railway automatically provides these, but you can override if needed
DATABASE_URL=postgresql://username:password@host:port/database_name
PGDATABASE=your_database_name
PGUSER=your_database_user
PGPASSWORD=your_database_password
PGHOST=your_database_host
PGPORT=5432

# ========================================
# CLOUDINARY SETTINGS
# ========================================
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here

# ========================================
# EMAIL SETTINGS (Gmail Example)
# ========================================
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password-here

# ========================================
# SECURITY SETTINGS
# ========================================
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://your-app.railway.app,https://your-app.vercel.app
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS=DENY

# ========================================
# CORS SETTINGS
# ========================================
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://your-app.vercel.app,https://your-app.railway.app
CORS_ALLOW_CREDENTIALS=True

# ========================================
# PAYMENT SETTINGS (if using)
# ========================================
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key_here
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_here
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_secret

# ========================================
# MONITORING & ANALYTICS
# ========================================
SENTRY_DSN=https://your-sentry-dsn-here

# ========================================
# CUSTOM DOMAIN SETTINGS
# ========================================
CUSTOM_DOMAIN=yourdomain.com
FRONTEND_URL=https://your-app.vercel.app

# ========================================
# FILE UPLOAD SETTINGS
# ========================================
MAX_UPLOAD_SIZE=10485760
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760

# ========================================
# CACHE SETTINGS
# ========================================
REDIS_URL=redis://localhost:6379/0

# ========================================
# ENVIRONMENT
# ========================================
ENVIRONMENT=production
RAILWAY_ENVIRONMENT=production
```

---

## 🔑 **How to Get Your Real Values:**

### **1. Railway Database Credentials:**
1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Go to "Connect" tab
4. Copy the connection details:
   - **Host**: `PGHOST`
   - **Database**: `PGDATABASE`
   - **Username**: `PGUSER`
   - **Password**: `PGPASSWORD`
   - **Port**: `PGPORT` (usually 5432)

### **2. Cloudinary Credentials:**
1. Go to [cloudinary.com/console](https://cloudinary.com/console)
2. Sign up/login to your account
3. Copy from Dashboard:
   - **Cloud Name**: `CLOUDINARY_CLOUD_NAME`
   - **API Key**: `CLOUDINARY_API_KEY`
   - **API Secret**: `CLOUDINARY_API_SECRET`

### **3. Generate Secret Key:**
```bash
# Run this command to generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### **4. Email Settings:**
- **Gmail**: Use your Gmail + App Password
- **Other providers**: Check their SMTP settings

---

## 🚨 **Important Security Notes:**

1. **NEVER commit .env file to git**
2. **Keep your secret key secure**
3. **Use different keys for development/production**
4. **Rotate keys regularly**
5. **Monitor Railway logs for any exposed secrets**

---

## 📋 **Railway Dashboard Setup:**

### **Environment Variables in Railway:**
1. Go to your Railway project
2. Click on your Django service
3. Go to "Variables" tab
4. Add each variable from your .env file
5. Railway will automatically inject:
   - `DATABASE_URL`
   - `PGDATABASE`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGHOST`
   - `PGPORT`
   - `RAILWAY_ENVIRONMENT`

### **Railway Service Configuration:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT`
- **Health Check Path**: `/health/`

---

## ✅ **Verification Steps:**

1. **Check Railway Logs**: Ensure no environment variable errors
2. **Test Database Connection**: Verify PostgreSQL connection
3. **Test Cloudinary**: Try uploading a test image
4. **Check Security Headers**: Verify HTTPS and security settings
5. **Test CORS**: Ensure frontend can communicate with backend

---

## 🔧 **Troubleshooting:**

### **Common Issues:**
- **Database Connection Failed**: Check Railway PostgreSQL service status
- **Cloudinary Upload Failed**: Verify API credentials
- **CORS Errors**: Check CORS_ALLOWED_ORIGINS
- **SSL Issues**: Ensure SECURE_SSL_REDIRECT is True

### **Debug Commands:**
```bash
# Check Railway environment variables
railway variables

# Test database connection
railway run python manage.py dbshell

# Check Django settings
railway run python manage.py check --deploy
```

---

**Remember**: Keep your .env file secure and never share it publicly! 🔒
