# 构建阶段：只在这里需要 Node
FROM node:20-alpine AS build

WORKDIR /app

# 依赖先于源码单独一层，改页面不会重装 node_modules
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# 运行阶段：静态文件交给 nginx，镜像里不带 Node
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
