# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# VITE_API_URL يُمرَّر وقت البناء
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config لـ React Router (SPA)
# (2026-09-04) الإصدار السابق ما كان فيه أي Cache-Control إطلاقاً — لا
# لملفات JS/CSS المُصدَّرة بـhash بالاسم (Vite)، ولا للصور. Lighthouse
# رصدها تحديداً على /brand/logo-icon-only.avif (TTL=None). أضيف location
# منفصل لملفات ثابتة hashed بالاسم — آمن نخزّنها سنة كاملة immutable لأن
# أي تغيير بالمحتوى بيغيّر اسم الملف تلقائياً. index.html نفسه (الجذر)
# يبقى بدون تخزين مؤقت طويل عمداً — لازم يوصل حديث دايماً، وإلا متصفح
# يخزّن نسخة قديمة بتشاور لملفات JS/CSS محذوفة بعد أي نشر جديد.
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
        add_header Cache-Control "no-cache"; \
    } \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|webp|avif|woff|woff2|ttf|eot)$ { \
        try_files $uri =404; \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
    location /api { \
        proxy_pass http://backend:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
