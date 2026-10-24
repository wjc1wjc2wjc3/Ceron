FROM golang:1.27
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
# 启用 postgres + nats 持久化能力（需联网拉取 lib/pq / nats.go）
RUN go build -tags postgres,nats -o /out/server ./cmd/server
EXPOSE 8080
CMD ["/out/server"]
