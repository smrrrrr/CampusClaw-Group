# ---- 依赖层 ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# ---- 构建层 ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ARG BACKEND_INTERNAL_URL=http://backend:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL
RUN npm run build

# ---- 运行层：standalone 产物，不含 node_modules/源码 ----
FROM node:22-alpine AS runner
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="campusclaw-frontend" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source="campusclaw"
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# 第10课 6.1：运行层只保留 node server.js；删除基础镜像自带的 npm/node-gyp
# 与 lldb 调试脚本（含 59 个 .py 与测试文件），并断言整镜像 .py 计数为 0。
RUN rm -rf /usr/local/lib/node_modules /usr/local/share/doc/node/lldb_commands.py \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
    && test "$(find / -name '*.py' -not -path '/proc/*' 2>/dev/null | wc -l)" -eq 0

EXPOSE 3000
CMD ["node", "server.js"]
