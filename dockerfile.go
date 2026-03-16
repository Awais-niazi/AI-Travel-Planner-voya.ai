FROM golang:1.22-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o service ./cmd/main.go

FROM alpine:3.19
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

COPY --from=builder /app/service .

EXPOSE 8001

CMD ["./service"]