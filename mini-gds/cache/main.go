// Command cache serves the availability cache over HTTP.
package main

import (
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

func main() {
	addr := env("ADDR", ":8081")
	ttl, err := strconv.Atoi(env("TTL_SECONDS", "60"))
	if err != nil {
		log.Fatalf("TTL_SECONDS: %v", err)
	}
	host := newHTTPHost(env("HOST_URL", "http://127.0.0.1:18000"))
	srv := newServer(host, time.Duration(ttl)*time.Second, time.Now)

	log.Printf("cache listening on %s (ttl %ds)", addr, ttl)
	log.Fatal(http.ListenAndServe(addr, srv.routes()))
}

func env(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
