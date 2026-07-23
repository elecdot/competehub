FROM public.ecr.aws/docker/library/node:22-alpine AS build

WORKDIR /app

# Keep the frontend build inside the memory envelope of the small demo host.
ENV NODE_OPTIONS=--max-old-space-size=768

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web/index.html apps/web/env.d.ts ./
COPY apps/web/tsconfig.json apps/web/tsconfig.node.json apps/web/vite.config.ts ./
COPY apps/web/src ./src
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM public.ecr.aws/docker/library/nginx:1.28-alpine

COPY infra/course-demo/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
