module ceron-go

go 1.27

require (
	github.com/lib/pq v1.10.9 // 仅 -tags postgres 时需要
	github.com/nats-io/nats.go v1.37.0 // 仅 -tags nats 时需要
)
