FROM golang:1.27
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN go build -o /out/server ./cmd/server
EXPOSE 8080
CMD ["/out/server"]
